import os

PROXY_BASE_URL = os.environ.get(
    "SUBTITLE_PROXY_URL",
    "https://subtitle-creator-production.up.railway.app",
)

PROXY_SECRET = os.environ.get("PROXY_SECRET", "")
