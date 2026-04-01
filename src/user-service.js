const express = require("express");
const { intEnv, requireEnv } = require("./lib/env");
const { createPgPool, queryOne } = require("./lib/postgres");
const { createRedisClient } = require("./lib/redis");
const { startServer } = require("./lib/server");

const app = express();
app.use(express.json());

const port = intEnv("PORT", 3005);
const redis = createRedisClient(requireEnv("REDIS_URL", "redis://redis:6379"));
const pg = createPgPool(requireEnv("USER_DB_URL", "postgres://app:app@postgres-user:5432/users"));

async function getUserById(userId) {
  const cacheKey = `user:${userId}`;
  const cached = await redis.get(cacheKey);
  if (cached) {
    return JSON.parse(cached);
  }

  const user = await queryOne(
    pg,
    `SELECT id, name, email, device_token AS "deviceToken" FROM users WHERE id = $1`,
    [userId]
  );

  if (!user) return null;
  await redis.set(cacheKey, JSON.stringify(user), "EX", 600);
  return user;
}

app.get("/health", (_, res) => res.json({ ok: true }));

app.get("/internal/users/:id", async (req, res) => {
  const userId = Number.parseInt(req.params.id, 10);
  const user = await getUserById(userId);
  if (!user) return res.status(404).json({ error: "User not found" });
  return res.json(user);
});

app.get("/internal/users/:id/followers", async (req, res) => {
  const userId = Number.parseInt(req.params.id, 10);
  const result = await pg.query("SELECT follower_id FROM follows WHERE followee_id = $1 ORDER BY follower_id", [userId]);
  return res.json({ userId, followerIds: result.rows.map((row) => row.follower_id) });
});

startServer(app, port, "user-service");
