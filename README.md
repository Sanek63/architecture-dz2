# architecture-dz2

Мини-проект социальной ленты по заданной архитектуре с API Gateway (nginx), синхронными сервисами, асинхронными Kafka-консьюмерами, Redis, PostgreSQL и S3-совместимым Object Storage (MinIO).

## Что реализовано

- **API Gateway (nginx)**
  - `GET /api/v1/feed` → Read API
  - `POST /api/v1/posts` → Write API
  - `/media/*` → Object Storage (MinIO)
- **Read API** → **Timeline Service**
- **Write API** → **Publication Service**
- **Timeline Service**
  - читает `feed:{userId}` из Redis
  - гидратирует посты через PostInfo Service
  - гидратирует авторов через User Service
- **User Service**
  - Redis cache + PostgreSQL users
  - выдаёт профиль и подписчиков
- **PostInfo Service**
  - Redis cache + PostgreSQL read replica
  - fallback в PostgreSQL master
  - запись постов в master (и синхронно в replica для демо)
- **Publication Service**
  - создаёт пост
  - сохраняет медиа в MinIO
  - публикует события в Kafka в **разные топики**:
    - `timeline.post-created`
    - `notifications.post-created`
- **Асинхронные консьюмеры**
  - `post-update-consumer`: читает `timeline.post-created`, обновляет Redis-ленты подписчиков
  - `send-notification-consumer`: читает `notifications.post-created`, пишет лог успешной отправки в PostgreSQL notifications

## Сервисы в docker-compose

- `gateway`
- `read-api`
- `write-api`
- `timeline-service`
- `publication-service`
- `user-service`
- `postinfo-service`
- `post-update-consumer`
- `send-notification-consumer`
- `redis`
- `zookeeper`, `kafka`
- `minio`, `minio-init`
- `postgres-user`
- `postgres-master`
- `postgres-replica`
- `postgres-notifications`

## Запуск

```bash
docker compose up --build
```

Gateway доступен на `http://localhost:8080`.

## Примеры запросов

### Создать пост

```bash
curl -X POST http://localhost:8080/api/v1/posts \
  -H 'Content-Type: application/json' \
  -d '{
    "authorId": 1,
    "content": "Привет, это новый пост",
    "mediaContent": "demo-media-content"
  }'
```

### Прочитать ленту

```bash
curl "http://localhost:8080/api/v1/feed?userId=2&limit=20"
```

Пользователь `2` подписан на пользователя `1`, поэтому после обработки Kafka-события новый пост попадёт в его Redis-ленту.

## Топики Kafka

- `timeline.post-created` — событие для обновления лент
- `notifications.post-created` — событие для отправки уведомлений

## Локальные npm-команды

```bash
npm install
npm run lint
npm run build
npm test
```
