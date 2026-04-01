# architecture-dz2

Мини-проект по заданной архитектуре на **Python** с API Gateway (nginx), набором сервисов, Kafka-консьюмерами, Redis, PostgreSQL и MinIO.

## Структура проекта

- `common/` — общие модули (config/http/redis/postgres/kafka/server)
- `services/`
  - `read_api`
  - `write_api`
  - `timeline_service`
  - `user_service`
  - `postinfo_service`
  - `publication_service`
- `consumers/`
  - `post_update_consumer`
  - `send_notification_consumer`
- `docker/` — nginx и SQL-инициализация БД
- `docker-compose.yml` — полный запуск системы

## Что реализовано по схеме

- Вход через `API Gateway (nginx)`.
- `GET /api/v1/feed` → `read-api` → `timeline-service`.
- `timeline-service` читает ленту пользователя из Redis (`feed:{userId}`) и гидратирует:
  - автора через `user-service` (Redis + PostgreSQL users)
  - посты через `postinfo-service` (Redis + PostgreSQL replica, fallback в master)
- `POST /api/v1/posts` → `write-api` → `publication-service`.
- `publication-service` создаёт пост, кладёт медиа в MinIO и публикует события в Kafka в **разные топики**:
  - `timeline.post-created`
  - `notifications.post-created`
- `post-update-consumer` читает `timeline.post-created` и обновляет Redis-ленты подписчиков.
- `send-notification-consumer` читает `notifications.post-created`, подтягивает данные из `user-service`/`postinfo-service`, пишет результат отправки в PostgreSQL notifications.

## Запуск через docker-compose

```bash
docker compose up --build
```

Gateway: `http://localhost:8080`

## Примеры запросов

### Создание поста

```bash
curl -X POST http://localhost:8080/api/v1/posts \
  -H 'Content-Type: application/json' \
  -d '{
    "authorId": 1,
    "content": "Привет, это пост",
    "mediaContent": "demo-media"
  }'
```

### Чтение ленты

```bash
curl "http://localhost:8080/api/v1/feed?userId=2&limit=20"
```

## Локальная проверка Python-кода

```bash
python -m compileall common services consumers
python tests/smoke_test.py
```
