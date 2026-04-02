from fastapi import FastAPI
from pydantic import BaseModel

from common.config import get_env, get_int_env
from common.http import create_http_client
from common.server import run_app

app = FastAPI(title="write-api")

port = get_int_env("PORT", 3002)
publication_client = create_http_client(get_env("PUBLICATION_SERVICE_URL", "http://publication-service:3004"))


class PostRequest(BaseModel):
    authorId: int
    content: str
    mediaContent: str | None = None


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/posts", status_code=201)
def create_post(payload: PostRequest):
    resp = publication_client.post("/internal/publications", json=payload.model_dump())
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    run_app(app, port)
