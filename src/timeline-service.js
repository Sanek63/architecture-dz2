const express = require("express");
const { intEnv, requireEnv } = require("./lib/env");
const { createRedisClient } = require("./lib/redis");
const { createHttpClient } = require("./lib/http");
const { startServer } = require("./lib/server");

const app = express();
app.use(express.json());

const port = intEnv("PORT", 3003);
const redis = createRedisClient(requireEnv("REDIS_URL", "redis://redis:6379"));
const userApi = createHttpClient(requireEnv("USER_SERVICE_URL", "http://user-service:3005"));
const postInfoApi = createHttpClient(requireEnv("POSTINFO_SERVICE_URL", "http://postinfo-service:3006"));

app.get("/health", (_, res) => res.json({ ok: true }));

app.get("/internal/timeline/:userId", async (req, res) => {
  const userId = Number.parseInt(req.params.userId, 10);
  const limit = Number.parseInt(req.query.limit || "20", 10);

  const postIds = await redis.lrange(`feed:${userId}`, 0, Math.max(0, limit - 1));
  if (postIds.length === 0) return res.json({ userId, posts: [] });

  const postsResponse = await postInfoApi.post("/internal/posts/bulk", { ids: postIds });
  const posts = postsResponse.data.posts || [];

  const authorIds = [...new Set(posts.map((post) => post.authorId))];
  const authorMap = new Map(
    (
      await Promise.all(
        authorIds.map(async (authorId) => {
          const response = await userApi.get(`/internal/users/${authorId}`);
          return [authorId, response.data];
        })
      )
    )
  );

  const hydrated = posts.map((post) => ({ ...post, author: authorMap.get(post.authorId) || null }));
  return res.json({ userId, posts: hydrated });
});

startServer(app, port, "timeline-service");
