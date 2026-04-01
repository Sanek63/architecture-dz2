from fastapi import FastAPI

from common.config import get_env, get_int_env
from common.http import create_http_client
from common.redis_client import create_redis_client
from common.server import run_app

app = FastAPI(title="timeline-service")

port = get_int_env("PORT", 3003)
redis_client = create_redis_client(get_env("REDIS_URL", "redis://redis:6379/0"))
user_client = create_http_client(get_env("USER_SERVICE_URL", "http://user-service:3005"))
post_client = create_http_client(get_env("POSTINFO_SERVICE_URL", "http://postinfo-service:3006"))


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/internal/timeline/{user_id}")
def timeline(user_id: int, limit: int = 20):
    post_ids = redis_client.lrange(f"feed:{user_id}", 0, max(0, limit - 1))
    if not post_ids:
        return {"userId": user_id, "posts": []}

    posts_resp = post_client.post("/internal/posts/bulk", json={"ids": post_ids})
    posts_resp.raise_for_status()
    posts = posts_resp.json().get("posts", [])

    author_ids = sorted({post["authorId"] for post in posts})
    authors = {}
    for author_id in author_ids:
        resp = user_client.get(f"/internal/users/{author_id}")
        if resp.status_code == 200:
            authors[author_id] = resp.json()

    hydrated = [{**post, "author": authors.get(post["authorId"])} for post in posts]
    return {"userId": user_id, "posts": hydrated}


if __name__ == "__main__":
    run_app(app, port)
