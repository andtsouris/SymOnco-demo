import os

from dotenv import load_dotenv

load_dotenv()

RATE_LIMIT_SECONDS = float(os.getenv("CTRIAL_RATE_LIMIT", "0.2"))
BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
