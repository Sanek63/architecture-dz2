from fastapi import FastAPI, HTTPException, Query

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
def feed(user_id: int = Query(alias="userId"), limit: int = 20):
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="userId must be a positive integer")
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be a positive integer")

    resp = timeline_client.get(f"/internal/timeline/{user_id}", params={"limit": limit})
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    run_app(app, port)
