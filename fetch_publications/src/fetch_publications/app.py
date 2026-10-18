import os
import httpx
from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from fetch_publications.config import NCBI_API_KEY
from fetch_publications.identifier_resolver import (
    get_total_misc_results,
    resolve_to_pmids,
)
from fetch_publications.models import (
    BulkFetchRequest,
    BulkFetchResponse,
    Candidate,
    FetchRequest,
    FetchResult,
    HealthResponse,
    MiscFetchResult,
    Publication,
    PubIdType,
)
from fetch_publications.pmc_client import fetch_full_text
from fetch_publications.pubmed_client import fetch_publication

app = FastAPI(
    title="fetch_publications",
    description="NCBI PubMed publication fetcher",
)


async def _enrich_with_full_text(publication: Publication) -> Publication:
    if publication.pmc_id:
        full_text = await fetch_full_text(publication.pmc_id)
        if full_text:
            return publication.model_copy(
                update={"full_text": full_text, "full_text_available": True}
            )
    return publication


async def _process_single(request: FetchRequest) -> FetchResult | MiscFetchResult:
    try:
        pmids = await run_in_threadpool(
            resolve_to_pmids, request.pub_text, request.pub_id_type.value
        )
        if not pmids:
            return FetchResult(
                status="error",
                query=request,
                error_message=(
                    f"No PubMed record found for {request.pub_id_type.value}: "
                    f"{request.pub_text}"
                ),
            )

        if request.pub_id_type == PubIdType.MISC:
            total = await run_in_threadpool(get_total_misc_results, request.pub_text)
            candidates = []
            candidate_errors = []
            for rank, pmid in enumerate(pmids, start=1):
                try:
                    publication = await run_in_threadpool(fetch_publication, pmid)
                except (OSError, RuntimeError, ValueError) as exc:
                    candidate_errors.append(f"PMID {pmid}: {exc}")
                    continue
                publication = await _enrich_with_full_text(publication)
                candidates.append(Candidate(rank=rank, publication=publication))
            return MiscFetchResult(
                status="partial_success" if candidate_errors else "success",
                query=request,
                total_results_found=total,
                candidates=candidates,
                candidate_errors=candidate_errors,
            )

        publication = await run_in_threadpool(fetch_publication, pmids[0])
        publication = await _enrich_with_full_text(publication)
        return FetchResult(status="success", query=request, publication=publication)
    except (OSError, RuntimeError, ValueError) as exc:
        return FetchResult(status="error", query=request, error_message=str(exc))


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    reachable = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi",
                params={"retmode": "json"},
            )
            reachable = response.status_code == 200
    except httpx.HTTPError:
        reachable = False
    return HealthResponse(
        status="ok",
        api_key_configured=NCBI_API_KEY is not None,
        ncbi_reachable=reachable,
    )


@app.post("/fetch/publication", response_model=FetchResult | MiscFetchResult)
async def fetch_single(request: FetchRequest) -> FetchResult | MiscFetchResult:
    return await _process_single(request)


@app.post("/fetch/pub/bulk", response_model=BulkFetchResponse)
async def fetch_bulk(request: BulkFetchRequest) -> BulkFetchResponse:
    results = []
    for item in request.extracted_publications:
        fetch_request = FetchRequest(
            pub_text=item.pub_text,
            pub_id_type=item.pub_id_type,
        )
        results.append(await _process_single(fetch_request))
    return BulkFetchResponse(source_document=request.source_document, results=results)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "fetch_publications.app:app",
        host=os.getenv("FETCH_PUBLICATIONS_HOST", "0.0.0.0"),
        port=int(os.getenv("FETCH_PUBLICATIONS_PORT", "5170")),
    )
