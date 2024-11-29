# database.py

from sqlalchemy import create_engine, Column, Integer, String, Date, Time, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config import DATABASE_URI

# Создаем подключение к базе данных
engine = create_engine(DATABASE_URI, connect_args={'check_same_thread': False})
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Модель таблицы мероприятий
class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)
    slots = relationship('Slot', back_populates='event', cascade="all, delete-orphan")

# Модель таблицы слотов
class Slot(Base):
    __tablename__ = 'slots'
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'))
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    max_seats = Column(Integer, nullable=False)
    reserved_seats = Column(Integer, default=0)
    event = relationship('Event', back_populates='slots')
    registrations = relationship('Registration', back_populates='slot', cascade="all, delete-orphan")

# Модель таблицы регистраций пользователей
class Registration(Base):
    __tablename__ = 'registrations'
    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(Integer, ForeignKey('slots.id', ondelete='CASCADE'))
    user_id = Column(Integer, nullable=False)
    user_name = Column(String, nullable=False)
    referred_by = Column(Integer, nullable=True)
    slot = relationship('Slot', back_populates='registrations')

# Инициализация базы данных
def init_db():
    Base.metadata.create_all(bind=engine)
