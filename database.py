from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, select, delete
from datetime import datetime
from typing import List, Dict, Any
import os
import asyncpg

# Получаем DATABASE_URL из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")

# Создаём движок
engine = create_async_engine(DATABASE_URL, echo=False)

# Создаём сессию
async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False
)

# Базовый класс
Base = declarative_base()


# Модель
class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    reminder_time = Column(DateTime, nullable=False)
    message = Column(String)


# Инициализация БД
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Создание напоминания
async def create_user_remind(telegram_id: int, title: str, reminder_time: datetime, message: str):
    if isinstance(reminder_time, str):
        reminder_time = datetime.strptime(reminder_time, "%Y-%m-%d %H:%M")

    reminder = Reminder(
        telegram_id=str(telegram_id),
        title=title,
        reminder_time=reminder_time.replace(second=0, microsecond=0),
        message=message
    )

    async with async_session() as session:
        session.add(reminder)
        await session.commit()


# Удаление просроченных напоминаний
async def delete_expired_reminders():
    async with async_session() as session:
        stmt = delete(Reminder).where(Reminder.reminder_time <= datetime.now())
        result = await session.execute(stmt)
        await session.commit()
        print(f"[Cleaner] Deleted {result.rowcount} expired reminders")


# Получение напоминаний пользователя
async def get_user_reminders(telegram_id: int) -> List[Dict[str, Any]]:
    async with async_session() as session:
        stmt = select(Reminder).where(Reminder.telegram_id == str(telegram_id)).order_by(Reminder.reminder_time)
        result = await session.execute(stmt)
        reminders = result.scalars().all()

        return [
            {
                "id": r.id,
                "title": r.title,
                "reminder_time": r.reminder_time.strftime("%Y-%m-%d %H:%M"),
                "message": r.message
            }
            for r in reminders
        ]

async def get_all_reminders():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch("SELECT id, telegram_id, title, reminder_time, message FROM reminders")
        return [
            {
                "id": row["id"],
                "telegram_id": row["telegram_id"],
                "title": row["title"],
                "reminder_time": row["reminder_time"].strftime('%Y-%m-%d %H:%M'),
                "message": row["message"]
            }
            for row in rows
        ]
    finally:
        await conn.close()

# Удаление напоминания по ID
async def delete_reminder_by_id(reminder_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("DELETE FROM reminders WHERE id = $1", reminder_id)
    finally:
        await conn.close()





