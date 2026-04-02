CREATE TABLE IF NOT EXISTS posts (
  id UUID PRIMARY KEY,
  author_id BIGINT NOT NULL,
  content TEXT NOT NULL,
  media_blob BYTEA,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
