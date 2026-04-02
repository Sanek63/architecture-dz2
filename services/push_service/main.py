from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from common.config import get_env, get_int_env
from common.postgres import execute, wait_for_connection
from common.server import run_app

app = FastAPI(title="push-service")

port = get_int_env("PORT", 3007)
pg_conn = wait_for_connection(get_env("NOTIFICATION_DB_URL", "postgresql://app:app@postgres-notifications:5432/notifications"))


class PushRequest(BaseModel):
    postId: str
    userId: int
    deviceToken: str | None = None
    message: str


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/internal/push")
def push(payload: PushRequest):
    if payload.userId <= 0:
        raise HTTPException(status_code=400, detail="userId must be a positive integer")
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    status = "sent" if payload.deviceToken else "skipped"
    execute(
        pg_conn,
        "INSERT INTO notification_logs(post_id, user_id, status, message) VALUES (%s::uuid, %s, %s, %s)",
        (payload.postId, payload.userId, status, payload.message),
    )
    return {"status": status}


if __name__ == "__main__":
    run_app(app, port)
