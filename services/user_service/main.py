import json

from fastapi import FastAPI, HTTPException

from common.config import get_env, get_int_env
from common.postgres import query_all, query_one, wait_for_connection
from common.redis_client import create_redis_client
from common.server import run_app

app = FastAPI(title="user-service")

port = get_int_env("PORT", 3005)
redis_client = create_redis_client(get_env("REDIS_URL", "redis://redis:6379/0"))
pg_conn = wait_for_connection(get_env("USER_DB_URL", "postgresql://app:app@postgres-user:5432/users"))


def get_user(user_id: int):
    key = f"user:{user_id}"
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)

    user = query_one(
        pg_conn,
        "SELECT id, name, email, device_token AS \"deviceToken\" FROM users WHERE id = %s",
        (user_id,),
    )
    if not user:
        return None

    redis_client.setex(key, 600, json.dumps(user))
    return user


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/internal/users/{user_id}")
def user_by_id(user_id: int):
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/internal/users/{user_id}/followers")
def user_followers(user_id: int):
    rows = query_all(
        pg_conn,
        "SELECT follower_id FROM follows WHERE followee_id = %s ORDER BY follower_id",
        (user_id,),
    )
    return {"userId": user_id, "followerIds": [row["follower_id"] for row in rows]}


if __name__ == "__main__":
    run_app(app, port)
