function requireEnv(name, fallback) {
  const value = process.env[name] ?? fallback;
  if (value === undefined || value === null || value === "") {
    throw new Error(`Missing env var: ${name}`);
  }
  return value;
}

function intEnv(name, fallback) {
  return Number.parseInt(requireEnv(name, fallback), 10);
}

module.exports = { requireEnv, intEnv };
