# main.py

from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from handlers import (
    start_handler,
    button_handler,
    add_event_handler,
    add_event_title,
    add_event_description,
    add_event_category,
    add_event_slots,
    cancel,
    list_events_handler
)
from database import init_db
from config import TELEGRAM_TOKEN
from scheduler import init_scheduler

# Состояния для ConversationHandler
TITLE, DESCRIPTION, CATEGORY, SLOTS = range(4)


def main():
    # Инициализация базы данных
    init_db()

    # Создание экземпляра Updater и передача ему токена
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Регистрация обработчиков команд
    dispatcher.add_handler(CommandHandler('start', start_handler))
    dispatcher.add_handler(CommandHandler('list_events', list_events_handler))

    # Обработчик для команды /add_event с использованием ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add_event', add_event_handler)],
        states={
            TITLE: [MessageHandler(filters.text & ~filters.command, add_event_title)],
            DESCRIPTION: [MessageHandler(filters.text & ~filters.command, add_event_description)],
            CATEGORY: [MessageHandler(filters.text & ~filters.command, add_event_category)],
            SLOTS: [MessageHandler(filters.text & ~filters.command, add_event_slots)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(conv_handler)

    # Регистрация обработчика кнопок
    dispatcher.add_handler(CallbackQueryHandler(button_handler))

    # Инициализация планировщика задач
    init_scheduler(dispatcher)

    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
