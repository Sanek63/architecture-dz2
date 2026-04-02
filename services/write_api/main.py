import base64

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile

from common.config import get_env, get_int_env
from common.http import create_http_client
from common.server import run_app

app = FastAPI(title="write-api")

port = get_int_env("PORT", 3002)
publication_client = create_http_client(get_env("PUBLICATION_SERVICE_URL", "http://publication-service:3004"))
user_client = create_http_client(get_env("USER_SERVICE_URL", "http://user-service:3005"))
post_client = create_http_client(get_env("POSTINFO_SERVICE_URL", "http://postinfo-service:3006"))


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/posts", status_code=200)
def create_post(
    author_id: int = Form(alias="authorId"),
    content: str = Form(),
    media: UploadFile | None = File(default=None),
):
    if author_id <= 0:
        raise HTTPException(status_code=400, detail="authorId must be a positive integer")
    if not content.strip():
        raise HTTPException(status_code=400, detail="content is required")

    media_base64 = None
    if media:
        media_bytes = media.file.read()
        media_base64 = base64.b64encode(media_bytes).decode("ascii")

    resp = publication_client.post(
        "/internal/publications",
        json={
            "authorId": author_id,
            "content": content,
            "mediaBase64": media_base64,
        },
    )
    resp.raise_for_status()
    return resp.json()


@app.get("/debug/seed")
def debug_seed(
    users_count: int = Query(alias="users_count"),
    max_followers_for_celeb: int = Query(alias="max_followers_for_celeb"),
    posts_per_users: int = Query(alias="posts_per_users"),
):
    if users_count <= 0 or max_followers_for_celeb < 0 or posts_per_users < 0:
        raise HTTPException(status_code=400, detail="invalid seed parameters")

    user_seed_resp = user_client.post(
        "/internal/debug/seed",
        params={
            "usersCount": users_count,
            "maxFollowersForCeleb": max_followers_for_celeb,
            "postsPerUsers": posts_per_users,
        },
    )
    user_seed_resp.raise_for_status()

    for author_id in range(1, users_count + 1):
        for idx in range(posts_per_users):
            post_resp = post_client.post(
                "/internal/posts",
                json={
                    "id": f"00000000-0000-0000-0000-{author_id:04d}{idx:08d}",
                    "authorId": author_id,
                    "content": f"seed post {idx} by user {author_id}",
                    "mediaBase64": None,
                },
            )
            post_resp.raise_for_status()

    return {
        "users_count": users_count,
        "max_followers_for_celeb": max_followers_for_celeb,
        "posts_per_users": posts_per_users,
        "status": "ok",
    }


if __name__ == "__main__":
    run_app(app, port)
