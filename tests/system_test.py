import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GATEWAY_BASE_URL = os.getenv("GATEWAY_BASE_URL", "http://localhost:8080")


def _request_json(method: str, path: str, data: bytes | None = None, headers: dict | None = None):
    request = Request(f"{GATEWAY_BASE_URL}{path}", data=data, method=method)
    for key, value in (headers or {}).items():
        request.add_header(key, value)

    with urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body) if body else {}


def _request_json_with_retry(
    method: str,
    path: str,
    data: bytes | None = None,
    headers: dict | None = None,
    attempts: int = 30,
    delay_seconds: float = 1.0,
):
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return _request_json(method, path, data=data, headers=headers)
        except (HTTPError, URLError, TimeoutError, ConnectionResetError, OSError) as exc:
            last_error = exc
            time.sleep(delay_seconds)
    assert last_error is not None
    raise last_error


def _wait_gateway_ready(max_attempts: int = 60, delay_seconds: float = 2.0):
    for _ in range(max_attempts):
        try:
            status, _ = _request_json("GET", "/api/v1/feed?userId=1&cursor=0&limit=1")
            if status == 200:
                return
        except (HTTPError, URLError, TimeoutError, ConnectionResetError, OSError):
            pass
        time.sleep(delay_seconds)
    raise RuntimeError("gateway did not become ready in time")


def _call_seed(users_count: int, max_followers_for_celeb: int, posts_per_user: int):
    query = urlencode(
        {
            "users_count": users_count,
            "max_followers_for_celeb": max_followers_for_celeb,
            "posts_per_users": posts_per_user,
        }
    )
    return _request_json_with_retry("GET", f"/api/v1/debug/seed?{query}")


def _post_with_media(author_id: int, content: str, media_payload: bytes):
    boundary = "----architecture-dz2-boundary"
    payload = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="authorId"\r\n\r\n'
        f"{author_id}\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="content"\r\n\r\n'
        f"{content}\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="media"; filename="media.bin"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + media_payload + f"\r\n--{boundary}--\r\n".encode("utf-8")

    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    return _request_json_with_retry("POST", "/api/v1/posts", data=payload, headers=headers)


def _get_feed(user_id: int, cursor: int, limit: int):
    query = urlencode({"userId": user_id, "cursor": cursor, "limit": limit})
    return _request_json_with_retry("GET", f"/api/v1/feed?{query}")


def test_system_flow_via_gateway():
    _wait_gateway_ready()

    seed_status, seed_payload = _call_seed(users_count=5, max_followers_for_celeb=4, posts_per_user=0)
    assert seed_status == 200
    assert seed_payload["status"] == "ok"

    post_status, post_payload = _post_with_media(
        author_id=1,
        content="system test post with media",
        media_payload=b"binary-media-payload",
    )
    assert post_status == 200
    assert post_payload["authorId"] == 1
    assert post_payload["content"] == "system test post with media"
    assert post_payload["mediaBase64"] is not None

    # users 2..5 follow user 1 after seed(max_followers_for_celeb=4), verify fanout in feed.
    feed_status, feed_payload = _get_feed(user_id=2, cursor=0, limit=20)
    assert feed_status == 200
    assert feed_payload["userId"] == 2
    assert feed_payload["cursor"] == 0
    assert isinstance(feed_payload["posts"], list)
    assert len(feed_payload["posts"]) >= 1

    top_post = feed_payload["posts"][0]
    assert top_post["id"] == post_payload["id"]
    assert top_post["authorId"] == 1
    assert top_post["content"] == "system test post with media"
    assert top_post["mediaBase64"] == post_payload["mediaBase64"]
    assert top_post["author"] is not None
    assert top_post["author"]["id"] == 1


if __name__ == "__main__":
    test_system_flow_via_gateway()
    print("System test passed")
