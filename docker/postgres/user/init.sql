CREATE TABLE IF NOT EXISTS users (
  id BIGINT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  device_token TEXT
);

CREATE TABLE IF NOT EXISTS follows (
  follower_id BIGINT NOT NULL,
  followee_id BIGINT NOT NULL,
  PRIMARY KEY (follower_id, followee_id)
);

INSERT INTO users(id, name, email, device_token) VALUES
  (1, 'Alice', 'alice@example.com', 'token-1'),
  (2, 'Bob', 'bob@example.com', 'token-2'),
  (3, 'Charlie', 'charlie@example.com', 'token-3')
ON CONFLICT (id) DO NOTHING;

INSERT INTO follows(follower_id, followee_id) VALUES
  (2, 1),
  (3, 1)
ON CONFLICT DO NOTHING;
