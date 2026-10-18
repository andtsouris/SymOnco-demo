# Publication fetcher

This is an independently installable FastAPI service for resolving publication
identifiers with NCBI E-utilities and fetching PubMed metadata. It optionally
adds PMC full text when a publication has an available PMC identifier.

## Install and run

```bash
cd fetch_publications
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
cp .env.example .env
# Set NCBI_EMAIL in .env before making NCBI requests.
uvicorn fetch_publications.app:app --app-dir src --host 127.0.0.1 --port 5170
```

`NCBI_API_KEY` is optional. Without it, the service uses NCBI's unauthenticated
rate limit. The health endpoint reports NCBI E-utilities reachability.

## API

- `GET /health`
- `POST /fetch/publication` accepts `pub_text` and `pub_id_type` (`PMID`, `DOI`,
  `PMC`, `URL`, or `MISC`).
- `POST /fetch/pub/bulk` accepts a `source_document` and
  `extracted_publications` list.

The response models retain the publication metadata fields and ranked candidate
shape used by the legacy pipeline. Network operations are isolated from the
FastAPI event loop, and optional PMC full-text failures do not discard metadata.

Run tests with `pytest`.

## References

- [NCBI E-utilities documentation](https://www.ncbi.nlm.nih.gov/books/NBK25501/)
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/)
- [PMC Open Access and BioC resources](https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/)
