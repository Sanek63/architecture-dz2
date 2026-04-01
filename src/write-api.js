const express = require("express");
const { intEnv, requireEnv } = require("./lib/env");
const { createHttpClient } = require("./lib/http");
const { startServer } = require("./lib/server");

const app = express();
app.use(express.json({ limit: "2mb" }));

const port = intEnv("PORT", 3002);
const publicationApi = createHttpClient(requireEnv("PUBLICATION_SERVICE_URL", "http://publication-service:3004"));

app.get("/health", (_, res) => res.json({ ok: true }));

app.post("/posts", async (req, res) => {
  const response = await publicationApi.post("/internal/publications", req.body);
  return res.status(201).json(response.data);
});

startServer(app, port, "write-api");
