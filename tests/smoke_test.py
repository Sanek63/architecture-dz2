from common.config import get_env
from common.kafka_utils import parse_event, serialize_event


def test_env_default():
    assert get_env("SMOKE_TEST_ENV", "ok") == "ok"


def test_kafka_serde_roundtrip():
    payload = {"hello": "world", "n": 1}
    assert parse_event(serialize_event(payload)) == payload


if __name__ == "__main__":
    test_env_default()
    test_kafka_serde_roundtrip()
    print("Smoke test passed")
