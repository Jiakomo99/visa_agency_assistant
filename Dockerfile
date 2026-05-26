FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_JSON=true \
    LOG_LEVEL=INFO

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py logging_config.py db.py rag.py telegram_bot.py ./
COPY documents/ documents/

RUN mkdir -p data

VOLUME ["/app/data"]

CMD ["python", "telegram_bot.py"]
