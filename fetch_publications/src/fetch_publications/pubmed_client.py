from Bio import Entrez

from fetch_publications.config import NCBI_API_KEY, NCBI_EMAIL
from fetch_publications.identifier_resolver import _throttle
from fetch_publications.models import Author, Publication

Entrez.email = NCBI_EMAIL
if NCBI_API_KEY:
    Entrez.api_key = NCBI_API_KEY

_cache: dict[str, Publication] = {}


def fetch_publication(pmid: str) -> Publication:
    """Fetch and normalize PubMed metadata for a PMID."""
    if pmid in _cache:
        return _cache[pmid]

    _throttle()
    handle = Entrez.efetch(db="pubmed", id=pmid, rettype="xml", retmode="xml")
    try:
        records = Entrez.read(handle)
    finally:
        handle.close()

    articles = records.get("PubmedArticle", [])
    if not articles:
        raise ValueError(f"No PubMed record found for PMID: {pmid}")

    article = articles[0]
    citation = article.get("MedlineCitation", {})
    article_data = citation.get("Article", {})
    journal_info = article_data.get("Journal", {})
    title = str(article_data.get("ArticleTitle", ""))

    authors = []
    for author in article_data.get("AuthorList", []):
        name = f"{author.get('LastName', '')} {author.get('ForeName', '')}".strip()
        affiliations = author.get("AffiliationInfo", [])
        affiliation = str(affiliations[0].get("Affiliation", "")) if affiliations else None
        if name:
            authors.append(Author(name=name, affiliation=affiliation))

    pub_date = journal_info.get("JournalIssue", {}).get("PubDate", {})
    publication_date = "-".join(
        str(pub_date[key]) for key in ("Year", "Month", "Day") if pub_date.get(key)
    )

    doi = None
    pmc_id = None
    pubmed_data = article.get("PubmedData", {})
    for article_id in pubmed_data.get("ArticleIdList", []):
        id_type = str(article_id.attributes.get("IdType", ""))
        if id_type == "doi":
            doi = str(article_id)
        elif id_type == "pmc":
            pmc_id = str(article_id)

    abstract_parts = article_data.get("Abstract", {}).get("AbstractText", [])
    abstract = " ".join(str(part) for part in abstract_parts) or None
    keywords = [
        str(keyword)
        for keyword_list in citation.get("KeywordList", [])
        for keyword in keyword_list
    ]
    mesh_terms = [
        str(mesh["DescriptorName"])
        for mesh in citation.get("MeshHeadingList", [])
        if mesh.get("DescriptorName")
    ]
    publication_type = [
        str(item) for item in article_data.get("PublicationTypeList", [])
    ]
    references = []
    for group in pubmed_data.get("ReferenceList", []):
        for reference in group.get("Reference", []):
            for reference_id in reference.get("ArticleIdList", []):
                if str(reference_id.attributes.get("IdType", "")) == "pubmed":
                    references.append(f"PMID:{reference_id}")
    languages = article_data.get("Language", [])

    publication = Publication(
        title=title,
        authors=authors,
        journal=str(journal_info.get("Title", "")) or None,
        publication_date=publication_date or None,
        doi=doi,
        pmid=pmid,
        pmc_id=pmc_id,
        abstract=abstract,
        full_text_available=False,
        keywords=keywords,
        mesh_terms=mesh_terms,
        publication_type=publication_type,
        references=references,
        language=str(languages[0]) if languages else None,
    )
    _cache[pmid] = publication
    return publication
