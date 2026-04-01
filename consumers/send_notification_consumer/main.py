from kafka import KafkaConsumer

from common.config import get_env
from common.http import create_http_client
from common.kafka_utils import ensure_topics, parse_event, wait_kafka
from common.postgres import create_connection, execute

user_client = create_http_client(get_env("USER_SERVICE_URL", "http://user-service:3005"))
post_client = create_http_client(get_env("POSTINFO_SERVICE_URL", "http://postinfo-service:3006"))
pg_conn = create_connection(get_env("NOTIFICATION_DB_URL", "postgresql://app:app@postgres-notifications:5432/notifications"))

kafka_brokers = get_env("KAFKA_BROKERS", "kafka:9092")
notification_topic = get_env("KAFKA_NOTIFICATION_TOPIC", "notifications.post-created")

wait_kafka(kafka_brokers)
ensure_topics(kafka_brokers, [notification_topic])

consumer = KafkaConsumer(
    notification_topic,
    bootstrap_servers=kafka_brokers,
    group_id="send-notification-group",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
)

for message in consumer:
    event = parse_event(message.value)
    post_resp = post_client.get(f"/internal/posts/{event['postId']}")
    post_resp.raise_for_status()
    post = post_resp.json()

    followers = event.get("followerIds", [])
    for follower_id in followers:
        user_resp = user_client.get(f"/internal/users/{follower_id}")
        if user_resp.status_code != 200:
            continue
        user = user_resp.json()
        text = f"Sent push to {user['email']} about post {post['id']}"
        print(f"[send-notification-consumer] {text}")
        execute(
            pg_conn,
            "INSERT INTO notification_logs(post_id, user_id, status, message) VALUES (%s::uuid, %s, %s, %s)",
            (post["id"], follower_id, "sent", text),
        )
