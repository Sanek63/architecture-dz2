const express = require("express");
const { intEnv, requireEnv } = require("./lib/env");
const { createHttpClient } = require("./lib/http");
const { startServer } = require("./lib/server");

const app = express();
const port = intEnv("PORT", 3001);
const timelineApi = createHttpClient(requireEnv("TIMELINE_SERVICE_URL", "http://timeline-service:3003"));

app.get("/health", (_, res) => res.json({ ok: true }));

app.get("/feed", async (req, res) => {
  const userId = Number.parseInt(req.query.userId, 10);
  const limit = Number.parseInt(req.query.limit || "20", 10);

  if (!userId) return res.status(400).json({ error: "userId is required" });

  const response = await timelineApi.get(`/internal/timeline/${userId}`, { params: { limit } });
  return res.json(response.data);
});

startServer(app, port, "read-api");
