import re


def normalize_nct_id(nct_text: str) -> str:
    """Normalize supported NCT text to the canonical NCT######## form."""
    text = str(nct_text).strip().strip(".,")
    text = re.sub(r"^NCT-Nr:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^NCT\s*", "", text, flags=re.IGNORECASE)
    match = re.search(r"(?<!\d)\d{8}(?!\d)", text)
    if match:
        return f"NCT{match.group()}"
    raise ValueError(f"No valid 8-digit NCT number found in {nct_text!r}")
