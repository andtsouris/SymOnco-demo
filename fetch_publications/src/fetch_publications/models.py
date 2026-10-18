from enum import Enum

from pydantic import BaseModel, Field, field_validator


class PubIdType(str, Enum):
    PMID = "PMID"
    DOI = "DOI"
    PMC = "PMC"
    URL = "URL"
    MISC = "MISC"


class FetchRequest(BaseModel):
    pub_text: str
    pub_id_type: PubIdType

    @field_validator("pub_text")
    @classmethod
    def require_publication_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("pub_text must not be empty")
        return value


class ExtractedPublication(BaseModel):
    id: int
    pub_text: str
    pub_id_type: PubIdType

    @field_validator("pub_text")
    @classmethod
    def require_publication_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("pub_text must not be empty")
        return value


class BulkFetchRequest(BaseModel):
    source_document: str
    extracted_publications: list[ExtractedPublication]


class Author(BaseModel):
    name: str
    affiliation: str | None = None


class Publication(BaseModel):
    title: str
    authors: list[Author] = Field(default_factory=list)
    journal: str | None = None
    publication_date: str | None = None
    doi: str | None = None
    pmid: str
    pmc_id: str | None = None
    abstract: str | None = None
    full_text: str | None = None
    full_text_available: bool = False
    keywords: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    publication_type: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    language: str | None = None


class Candidate(BaseModel):
    rank: int
    publication: Publication


class FetchResult(BaseModel):
    status: str
    query: FetchRequest
    publication: Publication | None = None
    error_message: str | None = None


class MiscFetchResult(BaseModel):
    status: str
    query: FetchRequest
    resolution_type: str = "free_text_search"
    total_results_found: int = 0
    candidates: list[Candidate] = Field(default_factory=list)
    candidate_errors: list[str] = Field(default_factory=list)
    error_message: str | None = None


class BulkFetchResponse(BaseModel):
    source_document: str
    results: list[FetchResult | MiscFetchResult]


class HealthResponse(BaseModel):
    status: str
    api_key_configured: bool
    ncbi_reachable: bool | None = None
