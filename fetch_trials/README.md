# Clinical-trial fetcher

This independently installable FastAPI service normalizes NCT identifiers and
fetches trial metadata from the ClinicalTrials.gov v2 API.

## Install and run

```bash
cd fetch_trials
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
uvicorn fetch_trials.app:app --app-dir src --host 127.0.0.1 --port 5172
```

The request pacing interval can be configured with `CTRIAL_RATE_LIMIT`
(seconds). See `.env.example`.

## API

- `GET /health`
- `POST /fetch/trial` with an NCT identifier or supported NCT text.
- `POST /fetch/trial/bulk` with a source document and trial list.

Trial results retain the title, summary, status, phase, conditions,
interventions, sponsor, dates, and enrollment fields used by the legacy
pipeline. Run tests with `pytest`.

## References

- [ClinicalTrials.gov API v2 documentation](https://clinicaltrials.gov/data-api/api)
