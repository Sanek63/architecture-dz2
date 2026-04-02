from datetime import datetime, timezone
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from common.config import get_env, get_int_env
from common.http import create_http_client
from common.server import run_app

app = FastAPI(title="publication-service")

port = get_int_env("PORT", 3004)
post_client = create_http_client(get_env("POSTINFO_SERVICE_URL", "http://postinfo-service:3006"))
user_client = create_http_client(get_env("USER_SERVICE_URL", "http://user-service:3005"))
timeline_client = create_http_client(get_env("TIMELINE_SERVICE_URL", "http://timeline-service:3003"))
push_client = create_http_client(get_env("PUSH_SERVICE_URL", "http://push-service:3007"))


class PublicationRequest(BaseModel):
    authorId: int
    content: str
    mediaBase64: str | None = None


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/internal/publications", status_code=201)
def create_publication(payload: PublicationRequest):
    if payload.authorId <= 0:
        raise HTTPException(status_code=400, detail="authorId must be a positive integer")
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="content is required")

    post_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    post_resp = post_client.post(
        "/internal/posts",
        json={
            "id": post_id,
            "authorId": payload.authorId,
            "content": payload.content,
            "mediaBase64": payload.mediaBase64,
            "createdAt": created_at,
        },
    )
    post_resp.raise_for_status()
    post = post_resp.json()

    followers_resp = user_client.get(f"/internal/users/{payload.authorId}/followers")
    followers_resp.raise_for_status()
    follower_ids = followers_resp.json().get("followerIds", [])

    timeline_resp = timeline_client.post(
        "/internal/timeline/publish",
        json={"postId": post_id, "followerIds": follower_ids},
    )
    timeline_resp.raise_for_status()

    for follower_id in follower_ids:
        user_resp = user_client.get(f"/internal/users/{follower_id}")
        if user_resp.status_code != 200:
            continue
        user = user_resp.json()
        push_resp = push_client.post(
            "/internal/push",
            json={
                "postId": post_id,
                "userId": follower_id,
                "deviceToken": user.get("deviceToken"),
                "message": f"New post from user {payload.authorId}",
            },
        )
        push_resp.raise_for_status()

    return post


if __name__ == "__main__":
    run_app(app, port)
