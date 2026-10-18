from fastapi.testclient import TestClient

from fetch_drugs.app import app
from fetch_drugs.models import Drug, DrugFetchResult, DrugFetchRequest
from fetch_drugs.nci_client import _parse_drug


def test_parse_drug_response_shape():
    drug = _parse_drug(
        {
            "termId": 7,
            "nciConceptId": "C106432",
            "name": "pembrolizumab",
            "nciConceptName": "Pembrolizumab",
            "definition": {"text": "An example definition."},
            "aliases": [{"type": "USBrandName", "name": "Keytruda"}],
            "drugInfoSummaryLink": {
                "uri": "https://example.test/drug",
                "text": "Drug information",
            },
        }
    )
    assert drug.term_id == 7
    assert drug.nci_concept_name == "Pembrolizumab"
    assert drug.aliases[0].name == "Keytruda"
    assert drug.drug_info_summary_link.uri.endswith("/drug")


def test_drug_endpoint_returns_service_result(monkeypatch):
    async def fake_fetch(_):
        return DrugFetchResult(
            status="success",
            query=DrugFetchRequest(drug_text="imatinib"),
            drug=Drug(
                term_id=7,
                nci_concept_id="C123",
                name="imatinib",
                nci_concept_name="Imatinib",
            ),
        )

    monkeypatch.setattr("fetch_drugs.app.fetch_drug_by_name", fake_fetch)
    response = TestClient(app).post(
        "/fetch/drug",
        json={"drug_text": "imatinib"},
    )
    assert response.status_code == 200
    assert response.json()["drug"]["nci_concept_name"] == "Imatinib"
