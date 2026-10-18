from fastapi.testclient import TestClient

from fetch_trials.app import app
from fetch_trials.clinicaltrials_client import _parse_trial
from fetch_trials.nct_resolver import normalize_nct_id


def test_normalize_nct_variants():
    assert normalize_nct_id(" NCT-Nr: 01234567, ") == "NCT01234567"
    assert normalize_nct_id("NCT 01234567") == "NCT01234567"


def test_invalid_nct_is_reported_by_endpoint():
    response = TestClient(app).post(
        "/fetch/trial",
        json={"nct_text": "not an NCT"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "8-digit NCT" in response.json()["error_message"]


def test_parse_trial_selected_fields():
    trial = _parse_trial(
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT01234567",
                    "officialTitle": "Trial title",
                },
                "descriptionModule": {"briefSummary": "Trial summary"},
                "statusModule": {
                    "overallStatus": "RECRUITING",
                    "startDateStruct": {"date": "2025-01"},
                },
                "designModule": {
                    "phases": ["PHASE2"],
                    "enrollmentInfo": {"count": 42},
                },
                "conditionsModule": {"conditions": ["Cancer"]},
                "armsInterventionsModule": {
                    "interventions": [{"name": "Drug A"}],
                },
                "sponsorCollaboratorsModule": {
                    "leadSponsor": {"name": "Sponsor"},
                },
            }
        },
        "NCT01234567",
    )
    assert trial.official_title == "Trial title"
    assert trial.interventions == ["Drug A"]
    assert trial.enrollment_count == 42
