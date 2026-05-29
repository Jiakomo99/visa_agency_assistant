FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_JSON=true \
    LOG_LEVEL=INFO

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py logging_config.py rag.py telegram_bot.py system_prompt.txt ./
COPY documents/ documents/

CMD ["python", "telegram_bot.py"]
