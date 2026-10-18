from pydantic import BaseModel, Field, field_validator


class DrugAlias(BaseModel):
    type: str
    name: str


class DrugInfoSummaryLink(BaseModel):
    uri: str
    text: str


class Drug(BaseModel):
    term_id: int
    nci_concept_id: str
    name: str
    nci_concept_name: str
    definition: str | None = None
    aliases: list[DrugAlias] = Field(default_factory=list)
    drug_info_summary_link: DrugInfoSummaryLink | None = None


class DrugCandidate(BaseModel):
    rank: int
    drug: Drug


class DrugFetchRequest(BaseModel):
    drug_text: str = Field(min_length=1)

    @field_validator("drug_text")
    @classmethod
    def require_drug_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("drug_text must not be empty")
        return value


class DrugFetchResult(BaseModel):
    status: str
    query: DrugFetchRequest
    drug: Drug | None = None
    error_message: str | None = None


class MultipleDrugFetchResult(BaseModel):
    status: str
    query: DrugFetchRequest
    multiple_results: bool = True
    total_results_found: int = 0
    candidates: list[DrugCandidate] = Field(default_factory=list)
    error_message: str | None = None


class ExtractedDrug(BaseModel):
    id: int
    drug_text: str = Field(min_length=1)

    @field_validator("drug_text")
    @classmethod
    def require_drug_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("drug_text must not be empty")
        return value


class BulkDrugFetchRequest(BaseModel):
    source_document: str
    drugs: list[ExtractedDrug]


class BulkDrugFetchResponse(BaseModel):
    source_document: str
    results: list[DrugFetchResult | MultipleDrugFetchResult]


class HealthResponse(BaseModel):
    status: str
    nci_api_reachable: bool | None = None
