from fastapi import FastAPI, HTTPException

from common.config import get_env, get_int_env
from common.http import create_http_client
from common.server import run_app

app = FastAPI(title="read-api")

port = get_int_env("PORT", 3001)
timeline_client = create_http_client(get_env("TIMELINE_SERVICE_URL", "http://timeline-service:3003"))


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/feed")
def feed(userId: int, limit: int = 20):
    if userId <= 0:
        raise HTTPException(status_code=400, detail="userId is required")

    resp = timeline_client.get(f"/internal/timeline/{userId}", params={"limit": limit})
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    run_app(app, port)
