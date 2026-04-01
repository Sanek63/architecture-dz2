const express = require("express");
const { intEnv, requireEnv } = require("./lib/env");
const { createPgPool, queryOne } = require("./lib/postgres");
const { createRedisClient } = require("./lib/redis");
const { startServer } = require("./lib/server");

const app = express();
app.use(express.json());

const port = intEnv("PORT", 3006);
const redis = createRedisClient(requireEnv("REDIS_URL", "redis://redis:6379"));
const readPool = createPgPool(requireEnv("POSTINFO_REPLICA_DB_URL", "postgres://app:app@postgres-replica:5432/posts"));
const masterPool = createPgPool(requireEnv("POSTINFO_MASTER_DB_URL", "postgres://app:app@postgres-master:5432/posts"));

async function readPost(postId) {
  const cacheKey = `post:${postId}`;
  const cached = await redis.get(cacheKey);
  if (cached) return JSON.parse(cached);

  let post = await queryOne(
    readPool,
    `SELECT id, author_id AS "authorId", content, media_key AS "mediaKey", created_at AS "createdAt" FROM posts WHERE id = $1`,
    [postId]
  );

  if (!post) {
    post = await queryOne(
      masterPool,
      `SELECT id, author_id AS "authorId", content, media_key AS "mediaKey", created_at AS "createdAt" FROM posts WHERE id = $1`,
      [postId]
    );
  }

  if (post) await redis.set(cacheKey, JSON.stringify(post), "EX", 600);
  return post;
}

app.get("/health", (_, res) => res.json({ ok: true }));

app.get("/internal/posts/:id", async (req, res) => {
  const post = await readPost(req.params.id);
  if (!post) return res.status(404).json({ error: "Post not found" });
  return res.json(post);
});

app.post("/internal/posts/bulk", async (req, res) => {
  const ids = Array.isArray(req.body.ids) ? req.body.ids : [];
  const posts = (await Promise.all(ids.map((id) => readPost(id)))).filter(Boolean);
  return res.json({ posts });
});

app.post("/internal/posts", async (req, res) => {
  const { id, authorId, content, mediaKey, createdAt } = req.body;
  if (!id || !authorId || !content) {
    return res.status(400).json({ error: "id, authorId, content are required" });
  }

  await masterPool.query(
    `INSERT INTO posts(id, author_id, content, media_key, created_at)
     VALUES ($1, $2, $3, $4, $5)
     ON CONFLICT (id) DO UPDATE SET author_id = EXCLUDED.author_id, content = EXCLUDED.content, media_key = EXCLUDED.media_key, created_at = EXCLUDED.created_at`,
    [id, authorId, content, mediaKey || null, createdAt || new Date().toISOString()]
  );

  await readPool.query(
    `INSERT INTO posts(id, author_id, content, media_key, created_at)
     VALUES ($1, $2, $3, $4, $5)
     ON CONFLICT (id) DO UPDATE SET author_id = EXCLUDED.author_id, content = EXCLUDED.content, media_key = EXCLUDED.media_key, created_at = EXCLUDED.created_at`,
    [id, authorId, content, mediaKey || null, createdAt || new Date().toISOString()]
  );

  const post = await readPost(id);
  return res.status(201).json(post);
});

startServer(app, port, "postinfo-service");
