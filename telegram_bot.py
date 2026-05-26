import logging

import telebot

from config import validate_settings
from db import (
    append_message,
    clear_history,
    format_history_for_display,
    init_db,
    load_history,
    remove_last_message,
)
from logging_config import setup_logging
from rag import ask

settings = validate_settings()
setup_logging(level=settings.log_level, json_format=settings.log_json)

logger = logging.getLogger(__name__)

init_db()
bot = telebot.TeleBot(settings.telegram_api_key)

logger.info("telegram bot starting", extra={"event": "bot_start"})


@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    history = load_history(chat_id)

    logger.info(
        "start command",
        extra={"event": "command_start", "chat_id": chat_id, "history_messages": len(history)},
    )

    greeting = (
        "Здравствуйте! Я помощник по испанским ВНЖ.\n"
        "Напишите вопрос — отвечу по нашей базе знаний.\n\n"
        "Команда /reset — начать диалог заново."
    )

    if history:
        recap = format_history_for_display(history)
        bot.send_message(chat_id, recap)
        bot.send_message(chat_id, greeting)
    else:
        bot.send_message(chat_id, greeting)


@bot.message_handler(commands=["reset"])
def reset(message):
    chat_id = message.chat.id
    clear_history(chat_id)
    bot.send_message(chat_id, "Диалог сброшен. Можете задать новый вопрос.")


@bot.message_handler(content_types=["text"])
def handle_text(message):
    chat_id = message.chat.id
    append_message(chat_id, "user", message.text)
    history = load_history(chat_id)

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
        answer, _ = ask(message.text, history=history, chat_id=chat_id)
        append_message(chat_id, "assistant", answer)
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
        remove_last_message(chat_id)
        bot.send_message(
            chat_id,
            "Прошу прощения, произошла техническая ошибка! "
            "Наши специалисты уже выясняют в чём дело.",
        )


if __name__ == "__main__":
    bot.polling(none_stop=True, interval=0)
