import logging

import telebot

from config import validate_settings
from logging_config import setup_logging
from rag import ask
from sessions import (
    add_assistant_message,
    add_user_message,
    clear_session,
    rollback_last_user_message,
)

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
        "Напишите вопрос — отвечу по нашей базе знаний.\n\n"
        "Команда /reset — начать диалог заново.",
    )


@bot.message_handler(commands=["reset"])
def reset(message):
    chat_id = message.chat.id
    clear_session(chat_id)
    bot.send_message(chat_id, "Диалог сброшен. Можете задать новый вопрос.")


@bot.message_handler(content_types=["text"])
def handle_text(message):
    chat_id = message.chat.id
    history = add_user_message(chat_id, message.text)

    logger.info(
        "user message",
        extra={
            "event": "user_message",
            "chat_id": chat_id,
            "text_length": len(message.text),
            "history_messages": len(history),
        },
    )

    bot.send_chat_action(chat_id, "typing")
    try:
        answer = ask(message.text, history=history, chat_id=chat_id)
        add_assistant_message(chat_id, answer)
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
        rollback_last_user_message(chat_id)
        bot.send_message(
            chat_id,
            "Прошу прощения, произошла техническая ошибка! "
            "Наши специалисты уже выясняют в чём дело.",
        )


if __name__ == "__main__":
    bot.polling(none_stop=True, interval=0)
