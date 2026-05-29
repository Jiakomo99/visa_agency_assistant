import logging

from config import validate_settings
from logging_config import setup_logging
from rag import ask

settings = validate_settings()
setup_logging(level=settings.log_level, json_format=settings.log_json)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("cli started", extra={"event": "cli_start"})

    while True:
        user_input = input("Введите ваш вопрос (или 'exit' для выхода): ")
        if user_input.lower() == "exit":
            break

        answer = ask(user_input)
        print("Ответ ассистента:", answer)
