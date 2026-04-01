const { Pool } = require("pg");

function createPgPool(connectionString) {
  const pool = new Pool({ connectionString });
  pool.on("error", (error) => {
    console.error("[postgres]", error.message);
  });
  return pool;
}

async function queryOne(pool, text, params = []) {
  const result = await pool.query(text, params);
  return result.rows[0] || null;
}

module.exports = { createPgPool, queryOne };
