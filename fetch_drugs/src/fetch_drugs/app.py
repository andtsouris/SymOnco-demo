import os

import httpx
from fastapi import FastAPI

from fetch_drugs.config import HEALTH_URL
from fetch_drugs.models import (
    BulkDrugFetchRequest,
    BulkDrugFetchResponse,
    DrugFetchRequest,
    DrugFetchResult,
    HealthResponse,
    MultipleDrugFetchResult,
)
from fetch_drugs.nci_client import fetch_drug_by_name

app = FastAPI(
    title="fetch_drugs",
    description="NCI Drug Dictionary resolver",
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(HEALTH_URL)
            reachable = response.status_code == 200
    except httpx.HTTPError:
        reachable = False
    return HealthResponse(status="ok", nci_api_reachable=reachable)


@app.post("/fetch/drug", response_model=DrugFetchResult | MultipleDrugFetchResult)
async def fetch_drug_single(
    request: DrugFetchRequest,
) -> DrugFetchResult | MultipleDrugFetchResult:
    return await fetch_drug_by_name(request.drug_text)


@app.post("/fetch/drug/bulk", response_model=BulkDrugFetchResponse)
async def fetch_drug_bulk(
    request: BulkDrugFetchRequest,
) -> BulkDrugFetchResponse:
    results = []
    for item in request.drugs:
        results.append(
            await fetch_drug_by_name(item.drug_text)
        )
    return BulkDrugFetchResponse(
        source_document=request.source_document,
        results=results,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "fetch_drugs.app:app",
        host=os.getenv("FETCH_DRUGS_HOST", "0.0.0.0"),
        port=int(os.getenv("FETCH_DRUGS_PORT", "5171")),
    )
