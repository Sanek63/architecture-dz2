const { Kafka } = require("kafkajs");

function createKafkaClient(clientId, brokers) {
  return new Kafka({
    clientId,
    brokers: brokers.split(",")
  });
}

async function ensureTopics(kafka, topics) {
  const admin = kafka.admin();
  await admin.connect();
  await admin.createTopics({
    waitForLeaders: true,
    topics: topics.map((topic) => ({ topic, numPartitions: 1, replicationFactor: 1 }))
  });
  await admin.disconnect();
}

module.exports = { createKafkaClient, ensureTopics };
