# MIPROv2 recommendation extraction

This folder contains an independently installable DSPy workflow for tuning
and running extractors over Label Studio recommendation annotations. It
supports publication references, clinical-trial identifiers, gene mentions,
drug names, and evidence levels. It reads either raw Label Studio task exports or the wrapped
recommendation JSON produced by the legacy pull script.

Records with zero or multiple annotations are excluded from training and
reported as skipped; their labels are ambiguous for this single-gold-label
workflow.

## Install

```bash
cd mipro_v2
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
cp .env.example .env
```

Configure `MIPRO_MODEL`; `MIPRO_API_BASE` and `MIPRO_API_KEY` are optional for
local or compatible model endpoints. No API key is embedded in the code.

## Run

```bash
mipro-optimize \
  --task genes \
  --data /path/to/all_recommendations.json \
  --output ./artifacts/genes_mipro.json
```

Valid tasks are `publications`, `clinical_trials`, `genes`, `drugs`, and
`evidence_levels`. The command evaluates a seeded train/test split, saves the
optimized DSPy program, and writes JSON and HTML test-set reports next to the
model file. It uses the corresponding legacy output field names (`pubs`,
`ctrial`, `genes`, `drugs`, `evLevs`).

To run the saved models over recommendation letters:

```bash
mipro-run \
  --data /path/to/all_recommendations.json \
  --model genes=./artifacts/genes_mipro.json \
  --model publications=./artifacts/publications_mipro.json \
  --output ./artifacts/extractions.json
```

Add `--enrich` to call the independent publication, trial, and drug services
over HTTP. Start each service separately first. Service base URLs can be
configured with `FETCH_PUBLICATIONS_URL`, `FETCH_TRIALS_URL`, and
`FETCH_DRUGS_URL`. The saved output contains extraction results and, when
requested, each service's raw response payload.

The JSON/HTML evaluation reports include recommendation text. Treat them as
sensitive research data and store them in an access-controlled location.

## References

- [DSPy MIPROv2 optimizer API](https://dspy.ai/api/optimizers/MIPROv2/)
- [DSPy project and documentation](https://github.com/stanfordnlp/dspy)
- Opsahl-Ong et al., [Optimizing Instructions and Demonstrations for
  Multi-Stage Language Model Programs](https://arxiv.org/abs/2406.11695)
