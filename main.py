import logging

from config import validate_settings
from logging_config import setup_logging
from rag import ask
from sessions import add_assistant_message, add_user_message, clear_session

CLI_CHAT_ID = 0

settings = validate_settings()
setup_logging(level=settings.log_level, json_format=settings.log_json)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("cli started", extra={"event": "cli_start"})
    print("Команда 'reset' — начать диалог заново. 'exit' — выход.")

    while True:
        user_input = input("Введите ваш вопрос: ").strip()
        if user_input.lower() == "exit":
            break
        if user_input.lower() == "reset":
            clear_session(CLI_CHAT_ID)
            print("Диалог сброшен.")
            continue
        if not user_input:
            continue

        history = add_user_message(CLI_CHAT_ID, user_input)
        answer = ask(user_input, history=history)
        add_assistant_message(CLI_CHAT_ID, answer)
        print("Ответ ассистента:", answer)
