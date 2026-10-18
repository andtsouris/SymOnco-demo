import httpx


async def fetch_full_text(pmc_id: str) -> str | None:
    """Fetch PMC full text through the NCBI BioC JSON API."""
    if not pmc_id:
        return None

    clean_id = pmc_id if pmc_id.upper().startswith("PMC") else f"PMC{pmc_id}"
    url = (
        "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/"
        f"BioC_json/{clean_id}/unicode"
    )
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            if response.status_code != 200:
                return None
            data = response.json()
        except (httpx.HTTPError, ValueError):
            return None

    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        return None
    documents = data.get("documents") or []
    if not isinstance(documents, list):
        return None
    passages = []
    for document in documents:
        if not isinstance(document, dict):
            continue
        document_passages = document.get("passages") or []
        if not isinstance(document_passages, list):
            continue
        for passage in document_passages:
            if isinstance(passage, dict) and passage.get("text"):
                passages.append(passage["text"])
    return "\n\n".join(passages) if passages else None
