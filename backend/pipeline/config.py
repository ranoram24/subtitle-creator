import os

# After deploying proxy/ to Railway, paste your URL here (no trailing slash).
# e.g. "https://subtitle-proxy-production.up.railway.app"
PROXY_BASE_URL = os.environ.get(
    "SUBTITLE_PROXY_URL",
    "https://REPLACE_WITH_YOUR_PROXY_URL",
)
