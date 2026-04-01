import httpx


def create_http_client(base_url: str) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=5.0)
