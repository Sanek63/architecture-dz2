from kafka import KafkaConsumer

from common.config import get_env
from common.http import create_http_client
from common.kafka_utils import ensure_topics, parse_event, wait_kafka
from common.redis_client import create_redis_client

redis_client = create_redis_client(get_env("REDIS_URL", "redis://redis:6379/0"))
user_client = create_http_client(get_env("USER_SERVICE_URL", "http://user-service:3005"))

kafka_brokers = get_env("KAFKA_BROKERS", "kafka:9092")
timeline_topic = get_env("KAFKA_TIMELINE_TOPIC", "timeline.post-created")

wait_kafka(kafka_brokers)
ensure_topics(kafka_brokers, [timeline_topic])

consumer = KafkaConsumer(
    timeline_topic,
    bootstrap_servers=kafka_brokers,
    group_id="timeline-post-update-group",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
)

for message in consumer:
    event = parse_event(message.value)
    followers = event.get("followerIds")
    if followers is None:
        resp = user_client.get(f"/internal/users/{event['authorId']}/followers")
        resp.raise_for_status()
        followers = resp.json().get("followerIds", [])

    target_users = sorted(set([event["authorId"], *followers]))
    for user_id in target_users:
        key = f"feed:{user_id}"
        redis_client.lpush(key, event["postId"])
        redis_client.ltrim(key, 0, 99)

    print(f"[post-update-consumer] processed post {event['postId']}")
