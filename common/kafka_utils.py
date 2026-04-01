import json
import time

from confluent_kafka.admin import AdminClient, NewTopic


def ensure_topics(bootstrap_servers: str, topics: list[str]) -> None:
    admin = AdminClient({"bootstrap.servers": bootstrap_servers})
    metadata = admin.list_topics(timeout=10)
    existing = set(metadata.topics.keys())
    to_create = [NewTopic(topic, num_partitions=1, replication_factor=1) for topic in topics if topic not in existing]
    if not to_create:
        return
    futures = admin.create_topics(to_create)
    for _, future in futures.items():
        try:
            future.result()
        except Exception:
            pass


def serialize_event(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def parse_event(raw: bytes) -> dict:
    return json.loads(raw.decode("utf-8"))


def wait_kafka(bootstrap_servers: str, retries: int = 30, delay: float = 2.0) -> None:
    for _ in range(retries):
        try:
            admin = AdminClient({"bootstrap.servers": bootstrap_servers})
            admin.list_topics(timeout=5)
            return
        except Exception:
            time.sleep(delay)
    raise RuntimeError("Kafka is unavailable")
