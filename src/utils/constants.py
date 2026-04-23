import os
from dotenv import load_dotenv

load_dotenv(override=True)

ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "egisadmin")
INAVI_SECRET_KEY = os.getenv("INAVI_SECRET_KEY", "inaviadmin")
TOTAL_MONTHS_POOL = 34
