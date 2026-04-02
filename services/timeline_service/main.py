from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI

from common.config import get_env, get_int_env
from common.http import create_http_client
from common.redis_client import create_redis_client
from common.server import run_app

app = FastAPI(title="timeline-service")

port = get_int_env("PORT", 3003)
max_workers = get_int_env("AUTHOR_FETCH_MAX_WORKERS", 16)
redis_client = create_redis_client(get_env("REDIS_URL", "redis://redis:6379/0"))
user_client = create_http_client(get_env("USER_SERVICE_URL", "http://user-service:3005"))
post_client = create_http_client(get_env("POSTINFO_SERVICE_URL", "http://postinfo-service:3006"))


def fetch_author(author_id: int):
    response = user_client.get(f"/internal/users/{author_id}")
    if response.status_code != 200:
        return author_id, None
    return author_id, response.json()


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/internal/timeline/{user_id}")
def timeline(user_id: int, limit: int = 20):
    if limit <= 0:
        return {"userId": user_id, "posts": []}

    post_ids = redis_client.lrange(f"feed:{user_id}", 0, limit - 1)
    if not post_ids:
        return {"userId": user_id, "posts": []}

    posts_resp = post_client.post("/internal/posts/bulk", json={"ids": post_ids})
    posts_resp.raise_for_status()
    posts = posts_resp.json().get("posts", [])

    author_ids = sorted({post["authorId"] for post in posts})
    worker_count = min(max_workers, len(author_ids)) or 1
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        authors = dict(pool.map(fetch_author, author_ids))

    hydrated_posts = [{**post, "author": authors.get(post["authorId"])} for post in posts]
    return {"userId": user_id, "posts": hydrated_posts}


if __name__ == "__main__":
    run_app(app, port)
