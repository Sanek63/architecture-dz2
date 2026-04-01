const { requireEnv } = require("./lib/env");
const { createRedisClient } = require("./lib/redis");
const { createHttpClient } = require("./lib/http");
const { createKafkaClient, ensureTopics } = require("./lib/kafka");

const redis = createRedisClient(requireEnv("REDIS_URL", "redis://redis:6379"));
const userApi = createHttpClient(requireEnv("USER_SERVICE_URL", "http://user-service:3005"));
const kafka = createKafkaClient("timeline-post-update-consumer", requireEnv("KAFKA_BROKERS", "kafka:9092"));

async function run() {
  const timelineTopic = requireEnv("KAFKA_TIMELINE_TOPIC", "timeline.post-created");
  await ensureTopics(kafka, [timelineTopic]);

  const consumer = kafka.consumer({ groupId: "timeline-post-update-group" });
  await consumer.connect();
  await consumer.subscribe({ topic: timelineTopic, fromBeginning: true });

  await consumer.run({
    eachMessage: async ({ message }) => {
      const event = JSON.parse(message.value.toString());
      const postId = event.postId;

      let followerIds = event.followerIds;
      if (!Array.isArray(followerIds)) {
        const response = await userApi.get(`/internal/users/${event.authorId}/followers`);
        followerIds = response.data.followerIds;
      }

      const usersToUpdate = [...new Set([event.authorId, ...followerIds])];
      for (const userId of usersToUpdate) {
        await redis.lpush(`feed:${userId}`, postId);
        await redis.ltrim(`feed:${userId}`, 0, 99);
      }

      console.log(`[post-update-consumer] processed post ${postId}`);
    }
  });
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
