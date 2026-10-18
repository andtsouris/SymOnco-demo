from fastapi.testclient import TestClient

from fetch_publications import app as app_module
from fetch_publications import pubmed_client
from fetch_publications.models import Author, Publication


def test_pubmed_identifier_is_validated_without_network():
    assert app_module.resolve_to_pmids(" 12345 ", "PMID") == ["12345"]


def test_publication_response_from_endpoint(monkeypatch):
    monkeypatch.setattr(app_module, "resolve_to_pmids", lambda *_: ["12345"])
    monkeypatch.setattr(
        app_module,
        "fetch_publication",
        lambda _: Publication(
            title="Example",
            pmid="12345",
            authors=[Author(name="Doe Jane")],
        ),
    )
    monkeypatch.setattr(app_module, "fetch_full_text", _no_full_text)

    response = TestClient(app_module.app).post(
        "/fetch/publication",
        json={"pub_text": "12345", "pub_id_type": "PMID"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["publication"]["pmid"] == "12345"


async def _no_full_text(_):
    return None


def test_pubmed_metadata_is_parsed_and_handle_is_closed(monkeypatch):
    class Handle:
        closed = False

        def close(self):
            self.closed = True

    class ArticleId:
        def __init__(self, id_type, value):
            self.attributes = {"IdType": id_type}
            self.value = value

        def __str__(self):
            return self.value

    handle = Handle()
    record = {
        "PubmedArticle": [
            {
                "MedlineCitation": {
                    "Article": {
                        "ArticleTitle": "A publication title",
                        "AuthorList": [
                            {
                                "LastName": "Doe",
                                "ForeName": "Jane",
                                "AffiliationInfo": [
                                    {"Affiliation": "Example Institute"}
                                ],
                            }
                        ],
                        "Journal": {
                            "Title": "Example Journal",
                            "JournalIssue": {
                                "PubDate": {"Year": "2026", "Month": "Oct"}
                            },
                        },
                        "Abstract": {"AbstractText": ["Part one.", "Part two."]},
                        "Language": ["eng"],
                        "PublicationTypeList": ["Journal Article"],
                    },
                    "KeywordList": [["oncology"]],
                    "MeshHeadingList": [{"DescriptorName": "Neoplasms"}],
                },
                "PubmedData": {
                    "ArticleIdList": [
                        ArticleId("doi", "10.1234/example"),
                        ArticleId("pmc", "PMC123456"),
                    ],
                    "ReferenceList": [],
                },
            }
        ]
    }
    monkeypatch.setattr(pubmed_client.Entrez, "efetch", lambda **_: handle)
    monkeypatch.setattr(pubmed_client.Entrez, "read", lambda _: record)
    pubmed_client._cache.pop("987654", None)

    publication = pubmed_client.fetch_publication("987654")

    assert publication.title == "A publication title"
    assert publication.publication_date == "2026-Oct"
    assert publication.authors[0].affiliation == "Example Institute"
    assert publication.doi == "10.1234/example"
    assert publication.pmc_id == "PMC123456"
    assert publication.abstract == "Part one. Part two."
    assert publication.full_text_available is False
    assert handle.closed
