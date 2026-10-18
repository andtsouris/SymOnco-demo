import os

from dotenv import load_dotenv

load_dotenv()

NCBI_API_KEY = os.getenv("NCBI_API_KEY")
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "")
RATE_LIMIT = 10 if NCBI_API_KEY else 3
MAX_MISC_RESULTS = 10
