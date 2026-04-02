# architecture-dz2

Лаконичная реализация микросервисной ленты на Python с API Gateway (nginx), Redis и PostgreSQL.

## Архитектура

- Gateway: `GET /api/v1/feed`, `POST /api/v1/posts`, `GET /api/v1/debug/seed`
- Read-path: `read-api -> timeline-service -> (user-service + postinfo-service)`
- Write-path: `write-api -> publication-service -> postinfo-service`
- Push-path: `publication-service -> push-service`

## Важно про Postgres replica

В этой версии `replica` трактуется как **реплицированное хранилище/кластерный контур**, а не как отдельные логические инстансы `master/replica` внутри compose. Поэтому `postinfo-service` работает с единым `POSTINFO_DB_URL`.

## Структура

- `common/` — конфиг, HTTP, Redis, Postgres утилиты
- `services/` — `read_api`, `write_api`, `timeline_service`, `user_service`, `postinfo_service`, `publication_service`, `push_service`
- `consumers/` — фоновые консьюмеры (legacy)
- `docker/` — nginx + SQL init
- `deploy/env/` — env-профили
- `Makefile` — запуск/остановка/масштабирование

## Краткая документация сервисов

- **read-api**
  - `GET /feed?userId=&cursor=&limit=`
  - Прокси к timeline-service
- **write-api**
  - `POST /posts` (multipart/form-data: `authorId`, `content`, `media`)
  - `GET /debug/seed?users_count=&max_followers_for_celeb=&posts_per_users=`
  - Передача публикации в publication-service
- **timeline-service**
  - `GET /internal/timeline/{userId}`
  - `POST /internal/timeline/publish`
  - Читает `feed:{userId}` из Redis c cursor/limit и гидратирует пост+автора
- **user-service**
  - `GET /internal/users/{id}`
  - `GET /internal/users/{id}/followers`
  - Redis cache + PostgreSQL users
- **postinfo-service**
  - `GET /internal/posts/{id}`
  - `POST /internal/posts/bulk`
  - `POST /internal/posts`
  - Redis cache + PostgreSQL posts (`BYTEA` для media)
- **publication-service**
  - `POST /internal/publications`
  - Создает пост, синхронно обновляет feed и отправляет push по подписчикам
- **push-service**
  - `POST /internal/push`
  - Логирует отправку push в PostgreSQL notifications

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
  -F 'authorId=1' \
  -F 'content=hello' \
  -F 'media=@/path/to/file.bin'

curl "http://localhost:8080/api/v1/feed?userId=2&cursor=0&limit=20"

curl "http://localhost:8080/api/v1/debug/seed?users_count=100&max_followers_for_celeb=1000&posts_per_users=5"
```
