const Redis = require("ioredis");

function createRedisClient(redisUrl) {
  const client = new Redis(redisUrl, {
    maxRetriesPerRequest: null,
    enableReadyCheck: true
  });

  client.on("error", (error) => {
    console.error("[redis]", error.message);
  });

  return client;
}

module.exports = { createRedisClient };
