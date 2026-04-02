import http from 'k6/http';
import { check, fail } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const SCALE = parseFloat(__ENV.SCALE || '0.01');

const READ_RPS = parseInt(__ENV.READ_RPS || '10000', 10);
const WRITE_RPS = parseInt(__ENV.WRITE_RPS || '500', 10);
const MEDIA_SIZE_MB = parseFloat(__ENV.MEDIA_SIZE_MB || '5.0');
const MAX_FOLLOWERS = parseInt(__ENV.MAX_FOLLOWERS || '1000000', 10);

const TARGET_READ_RPS = Math.max(1, Math.ceil(READ_RPS * SCALE));
const TARGET_WRITE_RPS = Math.max(1, Math.ceil(WRITE_RPS * SCALE));
const MEDIA_BYTES = Math.max(1, Math.floor(MEDIA_SIZE_MB * 1024 * 1024));
const dummyMediaContent = new Uint8Array(MEDIA_BYTES).buffer;

export const options = {
  scenarios: {
    read_feed: {
      executor: 'constant-arrival-rate',
      exec: 'readFeed',
      rate: TARGET_READ_RPS,
      timeUnit: '1s',
      duration: '2m',
      preAllocatedVUs: TARGET_READ_RPS,
      maxVUs: Math.max(TARGET_READ_RPS * 2, 50),
    },
    create_post: {
      executor: 'constant-arrival-rate',
      exec: 'createPost',
      rate: TARGET_WRITE_RPS,
      timeUnit: '1s',
      duration: '2m',
      preAllocatedVUs: TARGET_WRITE_RPS,
      maxVUs: Math.max(TARGET_WRITE_RPS * 2, 20),
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    'http_req_duration{scenario:read_feed}': ['p(95)<200'],
    'http_req_duration{scenario:create_post}': ['p(95)<500'],
  },
};

export function setup() {
  console.log(`[run] Read RPS=${READ_RPS}, Write RPS=${WRITE_RPS}, File=${MEDIA_SIZE_MB}MB, Scale=${SCALE}`);
  console.log(`[target] ${TARGET_READ_RPS} read/s, ${TARGET_WRITE_RPS} write/s`);

  const seedUrl =
    `${BASE_URL}/api/v1/debug/seed?users_count=50` +
    `&max_followers_for_celeb=${MAX_FOLLOWERS}` +
    '&posts_per_users=20';

  const res = http.get(seedUrl, { timeout: '120s' });
  if (res.status !== 200 && res.status !== 201) {
    fail(`[seed] failed, status=${res.status}`);
  }

  const users = [];
  for (let i = 1; i <= 50; i += 1) users.push(i);
  return { test_users: users };
}

export function readFeed(data) {
  const randomUser = data.test_users[Math.floor(Math.random() * data.test_users.length)];
  const cursor = Math.floor(Date.now() / 1000);
  const res = http.get(`${BASE_URL}/api/v1/feed?userId=${randomUser}&cursor=${cursor}&limit=20`);
  check(res, { 'read 200 OK': (r) => r.status === 200 });
}

export function createPost(data) {
  const randomUser = data.test_users[Math.floor(Math.random() * data.test_users.length)];
  const payload = {
    authorId: `${randomUser}`,
    content: 'Автоматический пост для теста нагрузки',
    media: http.file(dummyMediaContent, 'test_media.blob', 'application/octet-stream'),
  };

  const res = http.post(`${BASE_URL}/api/v1/posts`, payload);
  check(res, { 'post 200 OK': (r) => r.status === 200 });
}
