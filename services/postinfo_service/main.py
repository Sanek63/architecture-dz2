from datetime import datetime, timezone
import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from common.config import get_env, get_int_env
from common.postgres import execute, query_one, wait_for_connection
from common.redis_client import create_redis_client
from common.server import run_app

app = FastAPI(title="postinfo-service")

port = get_int_env("PORT", 3006)
redis_client = create_redis_client(get_env("REDIS_URL", "redis://redis:6379/0"))
db_conn = wait_for_connection(get_env("POSTINFO_DB_URL", "postgresql://app:app@postgres-posts:5432/posts"))


class BulkRequest(BaseModel):
    ids: list[str]


class CreatePostRequest(BaseModel):
    id: str
    authorId: int
    content: str
    mediaBase64: str | None = None
    createdAt: str | None = None


def read_post(post_id: str):
    key = f"post:{post_id}"
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)

    query = (
        "SELECT id::text AS id, author_id AS \"authorId\", content, "
        "encode(media_blob, 'base64') AS \"mediaBase64\", created_at AS \"createdAt\" "
        "FROM posts WHERE id = %s"
    )

    post = query_one(db_conn, query, (post_id,))
    if not post:
        return None

    if hasattr(post["createdAt"], "isoformat"):
        post["createdAt"] = post["createdAt"].isoformat()

    redis_client.setex(key, 600, json.dumps(post))
    return post


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/internal/posts/{post_id}")
def post_by_id(post_id: str):
    post = read_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@app.post("/internal/posts/bulk")
def post_bulk(payload: BulkRequest):
    posts: list[dict] = []
    for post_id in payload.ids:
        post = read_post(post_id)
        if post:
            posts.append(post)
    return {"posts": posts}


@app.post("/internal/posts", status_code=201)
def post_create(payload: CreatePostRequest):
    created_at = payload.createdAt or datetime.now(timezone.utc).isoformat()
    sql = (
        "INSERT INTO posts(id, author_id, content, media_blob, created_at) VALUES (%s::uuid, %s, %s, decode(%s, 'base64'), %s) "
        "ON CONFLICT (id) DO UPDATE SET author_id = EXCLUDED.author_id, content = EXCLUDED.content, "
        "media_blob = EXCLUDED.media_blob, created_at = EXCLUDED.created_at"
    )
    params = (payload.id, payload.authorId, payload.content, payload.mediaBase64, created_at)
    execute(db_conn, sql, params)
    return read_post(payload.id)


if __name__ == "__main__":
    run_app(app, port)
