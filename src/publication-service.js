const express = require("express");
const { Client } = require("minio");
const crypto = require("crypto");
const { intEnv, requireEnv } = require("./lib/env");
const { createHttpClient } = require("./lib/http");
const { createKafkaClient, ensureTopics } = require("./lib/kafka");
const { startServer } = require("./lib/server");

const app = express();
app.use(express.json({ limit: "2mb" }));

const port = intEnv("PORT", 3004);
const postInfoApi = createHttpClient(requireEnv("POSTINFO_SERVICE_URL", "http://postinfo-service:3006"));
const userApi = createHttpClient(requireEnv("USER_SERVICE_URL", "http://user-service:3005"));

const minioClient = new Client({
  endPoint: requireEnv("MINIO_HOST", "minio"),
  port: intEnv("MINIO_PORT", 9000),
  useSSL: false,
  accessKey: requireEnv("MINIO_ACCESS_KEY", "minioadmin"),
  secretKey: requireEnv("MINIO_SECRET_KEY", "minioadmin")
});

const mediaBucket = requireEnv("MINIO_BUCKET", "media");
const kafka = createKafkaClient("publication-service", requireEnv("KAFKA_BROKERS", "kafka:9092"));
const producer = kafka.producer();

async function uploadMedia(postId, mediaContent) {
  if (!mediaContent) return null;
  const mediaKey = `${postId}.txt`;
  await minioClient.putObject(mediaBucket, mediaKey, Buffer.from(mediaContent));
  return mediaKey;
}

app.get("/health", (_, res) => res.json({ ok: true }));

app.post("/internal/publications", async (req, res) => {
  const { authorId, content, mediaContent } = req.body;
  if (!authorId || !content) {
    return res.status(400).json({ error: "authorId and content are required" });
  }

  const postId = crypto.randomUUID();
  const createdAt = new Date().toISOString();
  const mediaKey = await uploadMedia(postId, mediaContent);

  await postInfoApi.post("/internal/posts", {
    id: postId,
    authorId,
    content,
    mediaKey,
    createdAt
  });

  const followersResponse = await userApi.get(`/internal/users/${authorId}/followers`);
  const followerIds = followersResponse.data.followerIds;

  const event = {
    eventId: crypto.randomUUID(),
    postId,
    authorId,
    content,
    createdAt,
    mediaKey,
    followerIds
  };

  await producer.send({
    topic: requireEnv("KAFKA_TIMELINE_TOPIC", "timeline.post-created"),
    messages: [{ key: String(authorId), value: JSON.stringify(event) }]
  });

  await producer.send({
    topic: requireEnv("KAFKA_NOTIFICATION_TOPIC", "notifications.post-created"),
    messages: [{ key: String(authorId), value: JSON.stringify(event) }]
  });

  return res.status(201).json({ postId, authorId, content, mediaKey, createdAt });
});

async function run() {
  await ensureTopics(kafka, [
    requireEnv("KAFKA_TIMELINE_TOPIC", "timeline.post-created"),
    requireEnv("KAFKA_NOTIFICATION_TOPIC", "notifications.post-created")
  ]);
  await producer.connect();
  startServer(app, port, "publication-service");
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
