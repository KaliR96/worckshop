# scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal, Slot
from telegram.ext import CallbackContext
import datetime

# Функция для удаления прошедших слотов
def remove_past_slots():
    session = SessionLocal()
    now = datetime.datetime.now()
    past_slots = session.query(Slot).filter(
        datetime.datetime.combine(Slot.date, Slot.time) < now
    ).all()
    for slot in past_slots:
        session.delete(slot)
    session.commit()
    session.close()

# Функция для отправки напоминаний
def send_reminders(context: CallbackContext):
    session = SessionLocal()
    now = datetime.datetime.now()
    reminder_times = [
        now + datetime.timedelta(days=1),
        now + datetime.timedelta(hours=2)
    ]
    for reminder_time in reminder_times:
        slots = session.query(Slot).filter(
            datetime.datetime.combine(Slot.date, Slot.time) == reminder_time
        ).all()
        for slot in slots:
            for registration in slot.registrations:
                context.bot.send_message(
                    chat_id=registration.user_id,
                    text=(
                        f"Напоминаем о мероприятии {slot.event.title} "
                        f"{slot.date.strftime('%d.%m.%Y')} в {slot.time.strftime('%H:%M')}"
                    )
                )
    session.close()

# Инициализация планировщика задач
def init_scheduler(dispatcher):
    scheduler = BackgroundScheduler()
    scheduler.add_job(remove_past_slots, 'interval', hours=1)
    scheduler.add_job(send_reminders, 'interval', minutes=30, args=[dispatcher])
    scheduler.start()
