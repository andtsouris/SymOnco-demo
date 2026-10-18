import asyncio

import httpx

from fetch_trials.config import BASE_URL, RATE_LIMIT_SECONDS
from fetch_trials.models import (
    ClinicalTrial,
    ClinicalTrialFetchResult,
    ClinicalTrialRequest,
)

_cache: dict[str, ClinicalTrialFetchResult] = {}


def _parse_trial(data: dict, nct_id: str) -> ClinicalTrial:
    if not isinstance(data, dict):
        raise ValueError("ClinicalTrials.gov returned a non-object response")
    protocol = data.get("protocolSection", {})
    if not isinstance(protocol, dict):
        raise ValueError("ClinicalTrials.gov response has an invalid protocol section")
    identification = protocol.get("identificationModule", {})
    description = protocol.get("descriptionModule", {})
    status = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    conditions_module = protocol.get("conditionsModule", {})
    arms = protocol.get("armsInterventionsModule", {})
    sponsor = protocol.get("sponsorCollaboratorsModule", {})
    modules = (identification, description, status, design, conditions_module, arms, sponsor)
    if any(not isinstance(module, dict) for module in modules):
        raise ValueError("ClinicalTrials.gov response contains an invalid module")

    interventions_raw = arms.get("interventions") or []
    if not isinstance(interventions_raw, list):
        raise ValueError("ClinicalTrials.gov interventions must be a list")
    interventions = [
        item["name"]
        for item in interventions_raw
        if isinstance(item, dict) and item.get("name")
    ] or None
    enrollment = design.get("enrollmentInfo") or {}
    lead_sponsor = sponsor.get("leadSponsor") or {}

    return ClinicalTrial(
        nct_id=identification.get("nctId", nct_id),
        official_title=identification.get("officialTitle"),
        brief_summary=description.get("briefSummary"),
        overall_status=status.get("overallStatus"),
        phase=design.get("phases"),
        conditions=conditions_module.get("conditions"),
        interventions=interventions,
        primary_sponsor=lead_sponsor.get("name"),
        start_date=(status.get("startDateStruct") or {}).get("date"),
        primary_completion_date=(
            status.get("primaryCompletionDateStruct") or {}
        ).get("date"),
        enrollment_count=enrollment.get("count"),
    )


async def fetch_clinical_trial(nct_id: str) -> ClinicalTrialFetchResult:
    """Fetch a canonical NCT identifier from ClinicalTrials.gov v2."""
    if nct_id in _cache:
        return _cache[nct_id]

    await asyncio.sleep(RATE_LIMIT_SECONDS)
    query = ClinicalTrialRequest(nct_text=nct_id)
    url = f"{BASE_URL}/{nct_id}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params={"format": "json"})
            if response.status_code == 429:
                await asyncio.sleep(1.0)
                response = await client.get(url, params={"format": "json"})

            if response.status_code == 404:
                result = ClinicalTrialFetchResult(
                    status="not_found",
                    query=query,
                    error_message=f"Trial {nct_id} not found",
                )
                _cache[nct_id] = result
                return result

            if response.status_code != 200:
                return ClinicalTrialFetchResult(
                    status="error",
                    query=query,
                    error_message=f"HTTP {response.status_code} fetching {nct_id}",
                )

            trial = _parse_trial(response.json(), nct_id)
        except httpx.TimeoutException:
            return ClinicalTrialFetchResult(
                status="error",
                query=query,
                error_message=f"Timeout fetching {nct_id}",
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            return ClinicalTrialFetchResult(
                status="error",
                query=query,
                error_message=str(exc),
            )

    result = ClinicalTrialFetchResult(
        status="success",
        query=query,
        clinical_trial=trial,
    )
    _cache[nct_id] = result
    return result
