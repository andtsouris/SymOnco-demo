import json
from types import SimpleNamespace

import pytest

from mipro_v2.data import load_recommendations, task_examples
from mipro_v2.inference import _parse_model_paths, extract_records
from mipro_v2.metrics import jaccard_score, normalize_entity, parse_entity_list
from mipro_v2.report import write_error_report
from mipro_v2.service_client import enrich_extractions, infer_publication_id_type
from mipro_v2.tasks import get_task


def test_load_legacy_wrapped_recommendation_export(tmp_path):
    path = tmp_path / "recommendations.json"
    path.write_text(
        json.dumps(
            [
                {
                    "record": {
                        "id": 4,
                        "data": {"text": "Mentions BRCA1."},
                        "annotations": [
                            {
                                "result": [
                                    {
                                        "type": "labels",
                                        "value": {"text": "BRCA1", "labels": ["Gene"]},
                                    }
                                ]
                            }
                        ],
                    }
                },
                {
                    "record": {
                        "id": 5,
                        "data": {"text": "Unannotated record."},
                        "annotations": [],
                    }
                },
            ]
        ),
        encoding="utf-8",
    )

    records = load_recommendations(path)
    examples, skipped = task_examples(records, "genes")
    assert examples == [{"text": "Mentions BRCA1.", "genes": ["BRCA1"]}]
    assert skipped == 1


@pytest.mark.parametrize(
    ("task", "value", "expected"),
    [
        ("publications", "https://doi.org/10.1234/ABC", "10.1234/abc"),
        ("clinical_trials", "NCT-Nr: 01234567", "01234567"),
        ("genes", "brca1", "BRCA1"),
        ("evidence_levels", "ELm2B", "2b"),
    ],
)
def test_normalize_entity(task, value, expected):
    assert normalize_entity(value, task) == expected


def test_jaccard_uses_task_normalization():
    assert jaccard_score(["brca1", "TP53"], ["BRCA1"], "genes") == 0.5
    assert jaccard_score([], [], "genes") == 1.0


def test_parse_entity_list_handles_python_list_and_semicolon_text():
    assert parse_entity_list("['A', 'B']") == ["A", "B"]
    assert parse_entity_list("A; B") == ["A", "B"]


def test_report_escapes_untrusted_text(tmp_path):
    output = tmp_path / "model.json"
    _, html_path = write_error_report(
        get_task("genes"),
        [{"text": "<script>not markup</script>", "genes": ["TP53"]}],
        [["TP53"]],
        output,
    )
    assert "&lt;script&gt;" in html_path.read_text(encoding="utf-8")


def test_model_paths_require_task_equals_path():
    assert _parse_model_paths(["genes=genes.json"]) == {"genes": "genes.json"}
    with pytest.raises(ValueError, match="TASK=PATH"):
        _parse_model_paths(["genes"])


def test_extract_records_uses_prediction_field():
    class FakeProgram:
        def __call__(self, *, text):
            assert text == "Mentions BRCA1."
            return SimpleNamespace(genes=["BRCA1"])

    from mipro_v2.data import RecommendationRecord

    result = extract_records(
        [RecommendationRecord("4", "Mentions BRCA1.", [], 1)],
        {"genes": FakeProgram()},
    )
    assert result == [{"rec_id": "4", "extractions": {"genes": ["BRCA1"]}}]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("194742", "PMID"),
        ("10.1234/example", "DOI"),
        ("PMC12345", "PMC"),
        ("https://pubmed.ncbi.nlm.nih.gov/194742/", "URL"),
        ("Some citation text", "MISC"),
    ],
)
def test_infer_publication_id_type(value, expected):
    assert infer_publication_id_type(value) == expected


def test_enrichment_calls_each_fetch_service_over_http(monkeypatch):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status": "success"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, url, *, json):
            calls.append((url, json))
            return FakeResponse()

    monkeypatch.setattr(
        "mipro_v2.service_client.httpx.AsyncClient",
        lambda **_: FakeClient(),
    )

    import asyncio

    records = [
        {
            "rec_id": "42",
            "extractions": {
                "pubs": ["194742"],
                "ctrial": ["NCT01234567"],
                "drugs": ["imatinib"],
            },
        }
    ]
    enriched = asyncio.run(
        enrich_extractions(
            records,
            publications_url="http://pubs/",
            trials_url="http://trials/",
            drugs_url="http://drugs/",
        )
    )

    assert [call[0] for call in calls] == [
        "http://pubs/fetch/pub/bulk",
        "http://trials/fetch/trial/bulk",
        "http://drugs/fetch/drug/bulk",
    ]
    assert calls[0][1]["extracted_publications"][0]["pub_id_type"] == "PMID"
    assert len(enriched[0]["fetch_results"]) == 3
