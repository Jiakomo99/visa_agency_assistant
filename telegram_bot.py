import logging

import telebot

from config import validate_settings
from logging_config import setup_logging
from rag import ask

settings = validate_settings()
setup_logging(level=settings.log_level, json_format=settings.log_json)

logger = logging.getLogger(__name__)

bot = telebot.TeleBot(settings.telegram_api_key)

logger.info("telegram bot starting", extra={"event": "bot_start"})


@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    logger.info("start command", extra={"event": "command_start", "chat_id": chat_id})
    bot.send_message(
        chat_id,
        "Здравствуйте! Я помощник по испанским ВНЖ.\n"
        "Напишите вопрос — отвечу по нашей базе знаний.",
    )


@bot.message_handler(content_types=["text"])
def handle_text(message):
    chat_id = message.chat.id

    logger.info(
        "user message",
        extra={
            "event": "user_message",
            "chat_id": chat_id,
            "text_length": len(message.text),
        },
    )

    bot.send_chat_action(chat_id, "typing")
    try:
        answer = ask(message.text, chat_id=chat_id)
        bot.send_message(chat_id, answer)
        logger.info(
            "assistant reply sent",
            extra={
                "event": "assistant_reply",
                "chat_id": chat_id,
                "answer_length": len(answer),
            },
        )
    except Exception:
        bot.send_message(
            chat_id,
            "Прошу прощения, произошла техническая ошибка! "
            "Наши специалисты уже выясняют в чём дело.",
        )


if __name__ == "__main__":
    bot.polling(none_stop=True, interval=0)
