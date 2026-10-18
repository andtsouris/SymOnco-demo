import os

from dotenv import load_dotenv

load_dotenv()

DRUG_RATE_LIMIT = float(os.getenv("DRUG_RATE_LIMIT", "0.2"))
BASE_URL = "https://webapis.cancer.gov/drugdictionary/v1/Drugs/Search"
HEALTH_URL = f"{BASE_URL}?query=aspirin&size=1&from=0"
MAX_CANDIDATES = 5
