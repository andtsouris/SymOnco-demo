import re
from typing import Any

import httpx


def infer_publication_id_type(value: str) -> str:
    text = value.strip()
    if re.fullmatch(r"\d+", text):
        return "PMID"
    if re.search(r"pmc/articles/PMC\d+", text, re.IGNORECASE) or re.fullmatch(
        r"PMC\d+", text, re.IGNORECASE
    ):
        return "PMC"
    if re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/\d+", text, re.IGNORECASE):
        return "URL"
    if re.search(r"doi\.org/10\.", text, re.IGNORECASE):
        return "URL"
    if re.match(r"10\.\S+/\S+", text):
        return "DOI"
    if re.match(r"https?://", text, re.IGNORECASE):
        return "URL"
    return "MISC"


async def enrich_extractions(
    records: list[dict[str, Any]],
    *,
    publications_url: str,
    trials_url: str,
    drugs_url: str,
) -> list[dict[str, Any]]:
    """Call the standalone fetch services over HTTP for extracted entities."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        for record in records:
            extraction = record["extractions"]
            rec_id = str(record["rec_id"])
            fetch_results = {}

            publications = extraction.get("pubs", [])
            if publications:
                response = await client.post(
                    f"{publications_url.rstrip('/')}/fetch/pub/bulk",
                    json={
                        "source_document": rec_id,
                        "extracted_publications": [
                            {
                                "id": index,
                                "pub_text": value,
                                "pub_id_type": infer_publication_id_type(value),
                            }
                            for index, value in enumerate(publications, start=1)
                        ],
                    },
                )
                response.raise_for_status()
                fetch_results["publications"] = response.json()

            trials = extraction.get("ctrial", [])
            if trials:
                response = await client.post(
                    f"{trials_url.rstrip('/')}/fetch/trial/bulk",
                    json={
                        "source_document": rec_id,
                        "trials": [
                            {"id": index, "nct_text": value}
                            for index, value in enumerate(trials, start=1)
                        ],
                    },
                )
                response.raise_for_status()
                fetch_results["clinical_trials"] = response.json()

            drugs = extraction.get("drugs", [])
            if drugs:
                response = await client.post(
                    f"{drugs_url.rstrip('/')}/fetch/drug/bulk",
                    json={
                        "source_document": rec_id,
                        "drugs": [
                            {"id": index, "drug_text": value}
                            for index, value in enumerate(drugs, start=1)
                        ],
                    },
                )
                response.raise_for_status()
                fetch_results["drugs"] = response.json()

            record["fetch_results"] = fetch_results
    return records
