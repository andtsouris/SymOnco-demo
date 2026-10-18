import os

import httpx
from fastapi import FastAPI

from fetch_trials.clinicaltrials_client import fetch_clinical_trial
from fetch_trials.models import (
    BulkTrialFetchRequest,
    BulkTrialFetchResponse,
    ClinicalTrialFetchResult,
    ClinicalTrialRequest,
    HealthResponse,
)
from fetch_trials.nct_resolver import normalize_nct_id

app = FastAPI(
    title="fetch_trials",
    description="ClinicalTrials.gov NCT identifier resolver",
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://clinicaltrials.gov/api/v2/studies",
                params={"pageSize": 1, "format": "json"},
            )
            reachable = response.status_code == 200
    except httpx.HTTPError:
        reachable = False
    return HealthResponse(status="ok", clinicaltrials_reachable=reachable)


@app.post("/fetch/trial", response_model=ClinicalTrialFetchResult)
async def fetch_trial(
    request: ClinicalTrialRequest,
) -> ClinicalTrialFetchResult:
    try:
        nct_id = normalize_nct_id(request.nct_text)
    except ValueError as exc:
        return ClinicalTrialFetchResult(
            status="error",
            query=request,
            error_message=str(exc),
        )
    return await fetch_clinical_trial(nct_id)


@app.post("/fetch/trial/bulk", response_model=BulkTrialFetchResponse)
async def fetch_trial_bulk(
    request: BulkTrialFetchRequest,
) -> BulkTrialFetchResponse:
    results = []
    for item in request.trials:
        trial_request = ClinicalTrialRequest(nct_text=item.nct_text)
        try:
            nct_id = normalize_nct_id(item.nct_text)
        except ValueError as exc:
            results.append(
                ClinicalTrialFetchResult(
                    status="error",
                    query=trial_request,
                    error_message=str(exc),
                )
            )
            continue
        results.append(await fetch_clinical_trial(nct_id))
    return BulkTrialFetchResponse(
        source_document=request.source_document,
        results=results,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "fetch_trials.app:app",
        host=os.getenv("FETCH_TRIALS_HOST", "0.0.0.0"),
        port=int(os.getenv("FETCH_TRIALS_PORT", "5172")),
    )
