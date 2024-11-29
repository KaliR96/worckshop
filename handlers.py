# handlers.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from database import SessionLocal, Event, Slot, Registration
from sqlalchemy.orm import sessionmaker
from config import ADMIN_ID, BOT_USERNAME
import datetime

# Переменные состояния для ConversationHandler
TITLE, DESCRIPTION, CATEGORY, SLOTS = range(4)

# Приветственное сообщение и главное меню
def start_handler(update: Update, context: CallbackContext):
    user = update.effective_user
    message = (
        f"Здравствуйте, {user.first_name}! "
        "Этот бот поможет вам записаться на мастер-классы."
    )

    # Клавиатура с основными опциями
    keyboard = [
        [InlineKeyboardButton("Посмотреть афишу", callback_data='view_events')],
        [InlineKeyboardButton("Фильтровать мероприятия", callback_data='filter_events')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Проверка на наличие реферального кода
    args = context.args
    if args and args[0].startswith('invite_code_'):
        slot_id = int(args[0].split('_')[-1])
        # Автоматическая запись пользователя на мероприятие
        register_user(update, context, slot_id)
    else:
        update.message.reply_text(message, reply_markup=reply_markup)

# Обработчик кнопок меню
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data

    if data == 'view_events':
        show_events(update, context)
    elif data == 'filter_events':
        start_filtering(update, context)
    elif data.startswith('event_'):
        event_id = int(data.split('_')[1])
        show_event_details(update, context, event_id)
    elif data.startswith('slot_'):
        slot_id = int(data.split('_')[1])
        register_user(update, context, slot_id)
    elif data.startswith('admin_delete_'):
        event_id = int(data.split('_')[2])
        delete_event(update, context, event_id)
    elif data.startswith('admin_edit_'):
        event_id = int(data.split('_')[2])
        edit_event(update, context, event_id)
    else:
        query.answer("Неизвестная команда.")

# Отображение списка мероприятий
def show_events(update: Update, context: CallbackContext):
    session = SessionLocal()
    events = session.query(Event).all()

    if not events:
        update.callback_query.message.reply_text("Сейчас нет доступных мероприятий.")
        session.close()
        return

    for event in events:
        keyboard = [[InlineKeyboardButton("Подробнее", callback_data=f'event_{event.id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.message.reply_text(
            f"*{event.title}*\nКатегория: {event.category}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    session.close()

# Показ деталей мероприятия и слотов
def show_event_details(update: Update, context: CallbackContext, event_id):
    session = SessionLocal()
    event = session.query(Event).filter(Event.id == event_id).first()

    if not event:
        update.callback_query.message.reply_text("Мероприятие не найдено.")
        session.close()
        return

    # Кнопки слотов
    keyboard = []
    for slot in event.slots:
        slot_datetime = datetime.datetime.combine(slot.date, slot.time)
        if slot_datetime >= datetime.datetime.now():
            button_text = f"{slot.date.strftime('%d.%m.%Y')} {slot.time.strftime('%H:%M')} ({slot.reserved_seats}/{slot.max_seats})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f'slot_{slot.id}')])

    if not keyboard:
        update.callback_query.message.reply_text("Нет доступных слотов для этого мероприятия.")
        session.close()
        return

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text(
        f"*{event.title}*\n\n{event.description}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    session.close()

# Регистрация пользователя на слот
def register_user(update: Update, context: CallbackContext, slot_id):
    session = SessionLocal()
    slot = session.query(Slot).filter(Slot.id == slot_id).first()
    user = update.effective_user

    if not slot:
        update.callback_query.message.reply_text("Слот не найден.")
        session.close()
        return

    # Проверка наличия мест
    if slot.reserved_seats >= slot.max_seats:
        update.callback_query.message.reply_text("К сожалению, места закончились.")
        session.close()
        return

    # Проверка, не записан ли уже пользователь
    existing_registration = session.query(Registration).filter(
        Registration.slot_id == slot_id,
        Registration.user_id == user.id
    ).first()

    if existing_registration:
        update.callback_query.message.reply_text("Вы уже записаны на этот слот.")
        session.close()
        return

    # Регистрация пользователя
    registration = Registration(
        slot_id=slot_id,
        user_id=user.id,
        user_name=user.username or user.full_name
    )
    slot.reserved_seats += 1
    session.add(registration)
    session.commit()

    # Генерация ссылки для приглашения друзей
    invite_link = f"https://t.me/{BOT_USERNAME}?start=invite_code_{slot_id}"
    message = (
        "Вы успешно записались на мероприятие!\n"
        f"Пригласите друзей по ссылке: {invite_link}"
    )
    update.callback_query.message.reply_text(message)

    # Уведомление администратора
    context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Пользователь @{user.username} записался на слот {slot_id}."
    )
    session.close()

# Начало процесса фильтрации мероприятий
def start_filtering(update: Update, context: CallbackContext):
    # Здесь будет реализация фильтрации по категориям, дате и времени
    update.callback_query.message.reply_text("Функция фильтрации пока не реализована.")

# Команда /add_event для администратора
def add_event_handler(update: Update, context: CallbackContext):
    # Проверка прав администратора
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return ConversationHandler.END

    update.message.reply_text("Введите название мероприятия:")
    return TITLE

def add_event_title(update: Update, context: CallbackContext):
    context.user_data['title'] = update.message.text
    update.message.reply_text("Введите описание мероприятия:")
    return DESCRIPTION

def add_event_description(update: Update, context: CallbackContext):
    context.user_data['description'] = update.message.text
    update.message.reply_text("Введите категорию мероприятия:")
    return CATEGORY

def add_event_category(update: Update, context: CallbackContext):
    context.user_data['category'] = update.message.text
    update.message.reply_text("Введите слоты в формате 'дд.мм.гггг чч:мм количество_мест', каждый с новой строки:")
    return SLOTS

def add_event_slots(update: Update, context: CallbackContext):
    slots_text = update.message.text.strip().split('\n')
    slots = []
    for slot_text in slots_text:
        try:
            date_str, time_str, seats_str = slot_text.strip().split()
            date = datetime.datetime.strptime(date_str, '%d.%m.%Y').date()
            time = datetime.datetime.strptime(time_str, '%H:%M').time()
            max_seats = int(seats_str)
            slots.append({'date': date, 'time': time, 'max_seats': max_seats})
        except ValueError:
            update.message.reply_text("Неверный формат слота. Пожалуйста, повторите ввод.")
            return SLOTS

    # Сохранение мероприятия и слотов в базу данных
    session = SessionLocal()
    event = Event(
        title=context.user_data['title'],
        description=context.user_data['description'],
        category=context.user_data['category']
    )
    session.add(event)
    session.commit()

    for slot_info in slots:
        slot = Slot(
            event_id=event.id,
            date=slot_info['date'],
            time=slot_info['time'],
            max_seats=slot_info['max_seats']
        )
        session.add(slot)
    session.commit()
    session.close()

    update.message.reply_text("Мероприятие успешно добавлено!")
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Добавление мероприятия отменено.")
    return ConversationHandler.END

# Команда /list_events для администратора
def list_events_handler(update: Update, context: CallbackContext):
    # Проверка прав администратора
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return

    session = SessionLocal()
    events = session.query(Event).all()

    if not events:
        update.message.reply_text("Нет активных мероприятий.")
        session.close()
        return

    for event in events:
        keyboard = [
            [
                InlineKeyboardButton("Удалить", callback_data=f'admin_delete_{event.id}'),
                InlineKeyboardButton("Редактировать", callback_data=f'admin_edit_{event.id}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            f"{event.title}",
            reply_markup=reply_markup
        )
    session.close()

# Удаление мероприятия
def delete_event(update: Update, context: CallbackContext, event_id):
    session = SessionLocal()
    event = session.query(Event).filter(Event.id == event_id).first()

    if not event:
        update.callback_query.message.reply_text("Мероприятие не найдено.")
        session.close()
        return

    session.delete(event)
    session.commit()
    session.close()

    update.callback_query.message.reply_text("Мероприятие удалено.")

# Редактирование мероприятия (заглушка)
def edit_event(update: Update, context: CallbackContext, event_id):
    update.callback_query.message.reply_text("Функция редактирования пока не реализована.")
