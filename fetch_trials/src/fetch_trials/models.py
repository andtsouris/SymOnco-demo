from pydantic import BaseModel


class ClinicalTrialRequest(BaseModel):
    nct_text: str


class ExtractedTrial(BaseModel):
    id: int
    nct_text: str


class BulkTrialFetchRequest(BaseModel):
    source_document: str
    trials: list[ExtractedTrial]


class ClinicalTrial(BaseModel):
    nct_id: str
    official_title: str | None = None
    brief_summary: str | None = None
    overall_status: str | None = None
    phase: list[str] | None = None
    conditions: list[str] | None = None
    interventions: list[str] | None = None
    primary_sponsor: str | None = None
    start_date: str | None = None
    primary_completion_date: str | None = None
    enrollment_count: int | None = None


class ClinicalTrialFetchResult(BaseModel):
    status: str
    query: ClinicalTrialRequest
    clinical_trial: ClinicalTrial | None = None
    error_message: str | None = None


class BulkTrialFetchResponse(BaseModel):
    source_document: str
    results: list[ClinicalTrialFetchResult]


class HealthResponse(BaseModel):
    status: str
    clinicaltrials_reachable: bool | None = None
