"""
Subtitle Creator – OpenAI proxy server.

Forwards /v1/* requests to the real OpenAI API, injecting the server-side key.
Deploy to Railway (or any host) and set OPENAI_API_KEY as an environment variable.
"""

import os
import httpx
from fastapi import FastAPI, Request, Response

app = FastAPI()

_API_KEY = os.environ.get("OPENAI_API_KEY", "")
_APP_SECRET = os.environ.get("PROXY_APP_SECRET", "")
_OPENAI_BASE = "https://api.openai.com"

_HOP_BY_HOP = {"transfer-encoding", "connection", "content-encoding", "keep-alive",
               "proxy-authenticate", "proxy-authorization", "te", "trailers", "upgrade"}


@app.get("/health")
async def health():
    return {"ok": True}


@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    if not _API_KEY:
        return Response(content='{"error":"proxy not configured"}', status_code=500,
                        media_type="application/json")

    if _APP_SECRET and request.headers.get("X-App-Secret") != _APP_SECRET:
        return Response(content='{"error":{"message":"Unauthorized","type":"authentication_error","code":"unauthorized","param":null}}',
                        status_code=401, media_type="application/json")

    url = f"{_OPENAI_BASE}/v1/{path}"

    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "authorization", "content-length")
    }
    headers["Authorization"] = f"Bearer {_API_KEY}"

    body = await request.body()

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=dict(request.query_params),
        )

    resp_headers = {k: v for k, v in resp.headers.items()
                    if k.lower() not in _HOP_BY_HOP}

    return Response(content=resp.content, status_code=resp.status_code,
                    headers=resp_headers)
