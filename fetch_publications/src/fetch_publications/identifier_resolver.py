import re
import threading
import time
from typing import Any

from Bio import Entrez

from fetch_publications.config import MAX_MISC_RESULTS, NCBI_API_KEY, NCBI_EMAIL, RATE_LIMIT

Entrez.email = NCBI_EMAIL
if NCBI_API_KEY:
    Entrez.api_key = NCBI_API_KEY

_MIN_INTERVAL = 1.0 / RATE_LIMIT
_last_request_time = 0.0
_throttle_lock = threading.Lock()


def _throttle() -> None:
    """Respect the configured NCBI request rate across worker threads."""
    global _last_request_time
    with _throttle_lock:
        now = time.monotonic()
        elapsed = now - _last_request_time
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        _last_request_time = time.monotonic()


def _read_entrez(handle: Any) -> Any:
    try:
        return Entrez.read(handle)
    finally:
        handle.close()


def _resolve_pmid(pub_text: str) -> list[str]:
    pmid = pub_text.strip()
    if not pmid.isdigit():
        raise ValueError(f"Invalid PMID: {pub_text}")
    return [pmid]


def _resolve_doi(pub_text: str) -> list[str]:
    _throttle()
    handle = Entrez.esearch(db="pubmed", term=f"{pub_text.strip()}[DOI]", retmax=1)
    record = _read_entrez(handle)
    return record.get("IdList", [])


def _resolve_pmc(pub_text: str) -> list[str]:
    pmc_id = pub_text.strip().upper().removeprefix("PMC")
    if not pmc_id.isdigit():
        raise ValueError(f"Invalid PMC identifier: {pub_text}")
    _throttle()
    handle = Entrez.elink(dbfrom="pmc", db="pubmed", id=pmc_id)
    record = _read_entrez(handle)
    pmids = []
    for linkset in record:
        for link_db in linkset.get("LinkSetDb", []):
            for link in link_db.get("Link", []):
                pmids.append(link["Id"])
    return pmids


def _resolve_url(pub_text: str) -> list[str]:
    url = pub_text.strip()
    match = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", url, re.IGNORECASE)
    if match:
        return [match.group(1)]

    match = re.search(r"doi\.org/(10\.\S+)", url, re.IGNORECASE)
    if match:
        return _resolve_doi(match.group(1).rstrip(".,"))

    match = re.search(r"pmc/articles/PMC(\d+)", url, re.IGNORECASE)
    if match:
        return _resolve_pmc(f"PMC{match.group(1)}")

    raise ValueError(f"Unrecognized URL format: {url}")


def _resolve_misc(pub_text: str) -> list[str]:
    _throttle()
    handle = Entrez.esearch(db="pubmed", term=pub_text, retmax=MAX_MISC_RESULTS)
    record = _read_entrez(handle)
    return record.get("IdList", [])


def get_total_misc_results(pub_text: str) -> int:
    _throttle()
    handle = Entrez.esearch(db="pubmed", term=pub_text, retmax=0)
    record = _read_entrez(handle)
    return int(record.get("Count", 0))


_RESOLVERS = {
    "PMID": _resolve_pmid,
    "DOI": _resolve_doi,
    "PMC": _resolve_pmc,
    "URL": _resolve_url,
    "MISC": _resolve_misc,
}


def resolve_to_pmids(pub_text: str, pub_id_type: str) -> list[str]:
    """Resolve an identifier or search phrase to PubMed identifiers."""
    try:
        resolver = _RESOLVERS[pub_id_type]
    except KeyError as exc:
        raise ValueError(f"Unknown pub_id_type: {pub_id_type}") from exc
    return resolver(pub_text)
