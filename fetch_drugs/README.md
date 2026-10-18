# Drug fetcher

This independently installable FastAPI service resolves drug names using the
NCI Drug Dictionary. It returns a single result, ranked candidates for
ambiguous searches, or an explicit error/not-found result.

## Install and run

```bash
cd fetch_drugs
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
uvicorn fetch_drugs.app:app --app-dir src --host 127.0.0.1 --port 5171
```

The request delay is configurable with `DRUG_RATE_LIMIT` (seconds). See
`.env.example`.

## API

- `GET /health`
- `POST /fetch/drug` with `{"drug_text": "imatinib"}`
- `POST /fetch/drug/bulk` with a source document and `drugs` list

Run tests with `pytest`.

## References

- [NCI Drug Dictionary](https://www.cancer.gov/publications/dictionaries/cancer-drug)
- [NCI API portal](https://api.cancer.gov/)
