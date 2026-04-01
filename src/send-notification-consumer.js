const { requireEnv } = require("./lib/env");
const { createKafkaClient, ensureTopics } = require("./lib/kafka");
const { createHttpClient } = require("./lib/http");
const { createPgPool } = require("./lib/postgres");

const kafka = createKafkaClient("send-notification-consumer", requireEnv("KAFKA_BROKERS", "kafka:9092"));
const userApi = createHttpClient(requireEnv("USER_SERVICE_URL", "http://user-service:3005"));
const postInfoApi = createHttpClient(requireEnv("POSTINFO_SERVICE_URL", "http://postinfo-service:3006"));
const pg = createPgPool(requireEnv("NOTIFICATION_DB_URL", "postgres://app:app@postgres-notifications:5432/notifications"));

async function run() {
  const notificationTopic = requireEnv("KAFKA_NOTIFICATION_TOPIC", "notifications.post-created");
  await ensureTopics(kafka, [notificationTopic]);

  const consumer = kafka.consumer({ groupId: "send-notification-group" });
  await consumer.connect();
  await consumer.subscribe({ topic: notificationTopic, fromBeginning: true });

  await consumer.run({
    eachMessage: async ({ message }) => {
      const event = JSON.parse(message.value.toString());
      const postResponse = await postInfoApi.get(`/internal/posts/${event.postId}`);
      const post = postResponse.data;

      const followerIds = Array.isArray(event.followerIds) ? event.followerIds : [];
      for (const followerId of followerIds) {
        const userResponse = await userApi.get(`/internal/users/${followerId}`);
        const user = userResponse.data;

        const messageText = `Sent push to ${user.email} about post ${post.id}`;
        console.log(`[send-notification-consumer] ${messageText}`);

        await pg.query(
          `INSERT INTO notification_logs(post_id, user_id, status, message) VALUES ($1, $2, $3, $4)`,
          [post.id, followerId, "sent", messageText]
        );
      }
    }
  });
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
