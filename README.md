# architecture-dz2

Лаконичная реализация микросервисной ленты на Python с API Gateway (nginx), Redis, Kafka, PostgreSQL и MinIO.

## Архитектура

- Gateway: `GET /api/v1/feed`, `POST /api/v1/posts`
- Read-path: `read-api -> timeline-service -> (user-service + postinfo-service)`
- Write-path: `write-api -> publication-service -> postinfo-service + MinIO`
- Async:
  - `post-update-consumer` читает `timeline.post-created` и обновляет Redis feed
  - `send-notification-consumer` читает `notifications.post-created` и пишет логи в PostgreSQL
- Kafka общая, топики разные:
  - `timeline.post-created`
  - `notifications.post-created`

## Важно про Postgres replica

В этой версии `replica` трактуется как **реплицированное хранилище/кластерный контур**, а не как отдельные логические инстансы `master/replica` внутри compose. Поэтому `postinfo-service` работает с единым `POSTINFO_DB_URL`.

## Структура

- `common/` — конфиг, HTTP, Redis, Postgres, Kafka утилиты
- `services/` — `read_api`, `write_api`, `timeline_service`, `user_service`, `postinfo_service`, `publication_service`
- `consumers/` — `post_update_consumer`, `send_notification_consumer`
- `docker/` — nginx + SQL init
- `deploy/env/` — env-профили
- `Makefile` — запуск/остановка/масштабирование

## Краткая документация сервисов

- **read-api**
  - `GET /feed?userId=&limit=`
  - Прокси к timeline-service
- **write-api**
  - `POST /posts`
  - Передача публикации в publication-service
- **timeline-service**
  - `GET /internal/timeline/{userId}`
  - Читает `feed:{userId}` из Redis и гидратирует пост+автора
- **user-service**
  - `GET /internal/users/{id}`
  - `GET /internal/users/{id}/followers`
  - Redis cache + PostgreSQL users
- **postinfo-service**
  - `GET /internal/posts/{id}`
  - `POST /internal/posts/bulk`
  - `POST /internal/posts`
  - Redis cache + PostgreSQL posts
- **publication-service**
  - `POST /internal/publications`
  - Создает пост, кладет media в MinIO, публикует в 2 Kafka topic
- **post-update-consumer**
  - Консьюмит `timeline.post-created`, обновляет Redis feeds
- **send-notification-consumer**
  - Консьюмит `notifications.post-created`, пишет логи доставки в PostgreSQL

## Makefile

### Установка/проверка

```bash
make install
make check
```

### Запуск (dev)

```bash
make up
make ps
make logs
```

### Остановка

```bash
make down
# или полностью с volume
make clean
```

### Запуск с масштабированием (perf-профиль)

```bash
make up-perf
```

Можно переопределять реплики:

```bash
make up-perf READ_API_REPLICAS=8 TIMELINE_SERVICE_REPLICAS=8 POSTINFO_SERVICE_REPLICAS=4
```

## Профили окружений

- `deploy/env/dev.env` — локальная разработка
- `deploy/env/perf.env` — примерный нагрузочный профиль

## Целевой тест (вариант 10)

Требования:
- Read: `60k RPS`
- Write: `200 RPS`
- Media avg: `2MB`
- Max followers per author: `3,000,000`
- Feed freshness: `<= 1 min`

Текущий compose-проект — демонстрационный стенд архитектуры и маршрутов. Для реального достижения 60k RPS нужно внешнее горизонтальное масштабирование, выделенный managed Kafka/Postgres/Redis кластер и прод-инфраструктура (оркестратор, autoscaling, observability, load balancer).

## Пример API

```bash
curl -X POST http://localhost:8080/api/v1/posts \
  -H 'Content-Type: application/json' \
  -d '{"authorId":1,"content":"hello","mediaContent":"demo"}'

curl "http://localhost:8080/api/v1/feed?userId=2&limit=20"
```
