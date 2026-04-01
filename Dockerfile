FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY common ./common
COPY services ./services
COPY consumers ./consumers
COPY tests ./tests

CMD ["python", "-m", "services.read_api.main"]
