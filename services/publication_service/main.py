from datetime import datetime, timezone
import io
import uuid

from confluent_kafka import Producer
from fastapi import FastAPI, HTTPException
from minio import Minio
from pydantic import BaseModel

from common.config import get_env, get_int_env
from common.http import create_http_client
from common.kafka_utils import ensure_topics, serialize_event, wait_kafka
from common.server import run_app

app = FastAPI(title="publication-service")

port = get_int_env("PORT", 3004)
post_client = create_http_client(get_env("POSTINFO_SERVICE_URL", "http://postinfo-service:3006"))
user_client = create_http_client(get_env("USER_SERVICE_URL", "http://user-service:3005"))

kafka_brokers = get_env("KAFKA_BROKERS", "kafka:29092")
timeline_topic = get_env("KAFKA_TIMELINE_TOPIC", "timeline.post-created")
notification_topic = get_env("KAFKA_NOTIFICATION_TOPIC", "notifications.post-created")

minio_client = Minio(
    endpoint=f"{get_env('MINIO_HOST', 'minio')}:{get_int_env('MINIO_PORT', 9000)}",
    access_key=get_env("MINIO_ACCESS_KEY", "minioadmin"),
    secret_key=get_env("MINIO_SECRET_KEY", "minioadmin"),
    secure=False,
)
media_bucket = get_env("MINIO_BUCKET", "media")

wait_kafka(kafka_brokers)
ensure_topics(kafka_brokers, [timeline_topic, notification_topic])
producer = Producer({"bootstrap.servers": kafka_brokers})


class PublicationRequest(BaseModel):
    authorId: int
    content: str
    mediaContent: str | None = None


def upload_media(post_id: str, media_content: str | None) -> str | None:
    if not media_content:
        return None
    media_key = f"{post_id}.txt"
    data = media_content.encode("utf-8")
    minio_client.put_object(
        media_bucket,
        media_key,
        data=io.BytesIO(data),
        length=len(data),
        content_type="text/plain",
    )
    return media_key


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/internal/publications", status_code=201)
def create_publication(payload: PublicationRequest):
    if not payload.authorId or not payload.content:
        raise HTTPException(status_code=400, detail="authorId and content are required")

    post_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    media_key = upload_media(post_id, payload.mediaContent)

    post_resp = post_client.post(
        "/internal/posts",
        json={
            "id": post_id,
            "authorId": payload.authorId,
            "content": payload.content,
            "mediaKey": media_key,
            "createdAt": created_at,
        },
    )
    post_resp.raise_for_status()

    followers_resp = user_client.get(f"/internal/users/{payload.authorId}/followers")
    followers_resp.raise_for_status()
    follower_ids = followers_resp.json().get("followerIds", [])

    event = {
        "eventId": str(uuid.uuid4()),
        "postId": post_id,
        "authorId": payload.authorId,
        "content": payload.content,
        "mediaKey": media_key,
        "createdAt": created_at,
        "followerIds": follower_ids,
    }

    data = serialize_event(event)
    producer.produce(timeline_topic, key=str(payload.authorId), value=data)
    producer.produce(notification_topic, key=str(payload.authorId), value=data)
    producer.flush(10)

    return {
        "postId": post_id,
        "authorId": payload.authorId,
        "content": payload.content,
        "mediaKey": media_key,
        "createdAt": created_at,
    }


if __name__ == "__main__":
    run_app(app, port)
