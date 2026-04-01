import json
import time

from kafka import KafkaAdminClient
from kafka.admin import NewTopic


def ensure_topics(bootstrap_servers: str, topics: list[str]) -> None:
    admin = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
    try:
        existing = set(admin.list_topics())
        for topic in topics:
            if topic in existing:
                continue
            try:
                admin.create_topics([NewTopic(name=topic, num_partitions=1, replication_factor=1)])
            except Exception:
                pass
    finally:
        admin.close()


def serialize_event(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def parse_event(raw: bytes) -> dict:
    return json.loads(raw.decode("utf-8"))


def wait_kafka(bootstrap_servers: str, retries: int = 20, delay: float = 2.0) -> None:
    for _ in range(retries):
        try:
            admin = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
            admin.close()
            return
        except Exception:
            time.sleep(delay)
    raise RuntimeError("Kafka is unavailable")
