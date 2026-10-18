import asyncio

import httpx

from fetch_drugs.config import BASE_URL, DRUG_RATE_LIMIT, MAX_CANDIDATES
from fetch_drugs.models import (
    Drug,
    DrugAlias,
    DrugCandidate,
    DrugFetchRequest,
    DrugFetchResult,
    DrugInfoSummaryLink,
    MultipleDrugFetchResult,
)

_cache: dict[str, DrugFetchResult | MultipleDrugFetchResult] = {}


def _parse_drug(item: dict) -> Drug:
    if "termId" not in item:
        raise ValueError("NCI response is missing termId")

    aliases = []
    for alias in item.get("aliases") or []:
        if not isinstance(alias, dict) or not alias.get("type") or not alias.get("name"):
            raise ValueError("NCI response contains an invalid drug alias")
        aliases.append(DrugAlias(type=alias["type"], name=alias["name"]))

    link = item.get("drugInfoSummaryLink")
    summary_link = None
    if link:
        if not isinstance(link, dict):
            raise ValueError("NCI response contains an invalid drug summary link")
        if not link.get("uri") or not link.get("text"):
            raise ValueError("NCI response contains an invalid drug summary link")
        summary_link = DrugInfoSummaryLink(uri=link["uri"], text=link["text"])

    definition = item.get("definition") or {}
    return Drug(
        term_id=int(item["termId"]),
        nci_concept_id=item.get("nciConceptId") or "",
        name=item.get("name") or "",
        nci_concept_name=item.get("nciConceptName") or item.get("name") or "",
        definition=(
            definition.get("text") if isinstance(definition, dict) else None
        ),
        aliases=aliases,
        drug_info_summary_link=summary_link,
    )


async def fetch_drug_by_name(
    drug_text: str,
) -> DrugFetchResult | MultipleDrugFetchResult:
    query_text = drug_text.strip()
    if not query_text:
        raise ValueError("Drug name must not be empty")

    cache_key = query_text.casefold()
    if cache_key in _cache:
        return _cache[cache_key]

    await asyncio.sleep(DRUG_RATE_LIMIT)
    query = DrugFetchRequest(drug_text=drug_text)
    params = {"query": query_text, "size": MAX_CANDIDATES, "from": 0}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(BASE_URL, params=params)
            if response.status_code == 429:
                await asyncio.sleep(1.0)
                response = await client.get(BASE_URL, params=params)

            if response.status_code != 200:
                return DrugFetchResult(
                    status="error",
                    query=query,
                    error_message=f"HTTP {response.status_code} fetching NCI drug",
                )

            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("NCI returned a non-object response")
            items = data.get("results") or []
            if not isinstance(items, list):
                raise ValueError("NCI response results must be a list")
            meta = data.get("meta") or {}
            if not isinstance(meta, dict):
                raise ValueError("NCI response meta must be an object")
            total = int(meta.get("totalResults", len(items)))

            if not items:
                result: DrugFetchResult | MultipleDrugFetchResult = DrugFetchResult(
                    status="not_found",
                    query=query,
                    error_message=f"No NCI drug record found for: {drug_text}",
                )
            elif len(items) == 1:
                result = DrugFetchResult(
                    status="success",
                    query=query,
                    drug=_parse_drug(items[0]),
                )
            else:
                candidates = [
                    DrugCandidate(rank=index + 1, drug=_parse_drug(item))
                    for index, item in enumerate(items[:MAX_CANDIDATES])
                ]
                result = MultipleDrugFetchResult(
                    status="multiple_results",
                    query=query,
                    total_results_found=total,
                    candidates=candidates,
                )
        except httpx.TimeoutException:
            return DrugFetchResult(
                status="error",
                query=query,
                error_message=f"Timeout fetching drug: {drug_text}",
            )
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            return DrugFetchResult(
                status="error",
                query=query,
                error_message=str(exc),
            )

    _cache[cache_key] = result
    return result
