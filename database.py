from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, DateTime, select, delete, ForeignKey
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import pytz
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=False)

async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False
)


Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, nullable=False, unique=True)
    country = Column(String, nullable=True)
    timezone = Column(Integer, nullable=True)

    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # внешний ключ
    title = Column(String, nullable=False)
    reminder_time = Column(DateTime, nullable=False)
    message = Column(String)

    user = relationship("User", back_populates="reminders")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def create_user_remind(telegram_id: int, title: str, reminder_time, message: str):
    if isinstance(reminder_time, str):
        dt_naive = datetime.strptime(reminder_time, "%Y-%m-%d %H:%M")
        local_tz = pytz.timezone("Europe/Moscow")
        dt_local = local_tz.localize(dt_naive)
        reminder_time = dt_local.astimezone(pytz.UTC)

    reminder = Reminder(
        telegram_id=str(telegram_id),
        title=title,
        reminder_time=reminder_time.replace(second=0, microsecond=0),
        message=message
    )

    async with async_session() as session:
        session.add(reminder)
        await session.commit()

async def create_or_update_user(telegram_id: int, country: str, timezone: int):
    async with async_session() as session:
        try:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalars().first()

            if user:
                user.country = country
                user.timezone = timezone
                print(f"Пользователь {telegram_id} найден — обновлены данные.")
            else:
                user = User(
                    telegram_id=telegram_id,
                    country=country,
                    timezone=timezone
                )
                session.add(user)
                print(f"Создан новый пользователь {telegram_id}.")

            await session.commit()
            await session.refresh(user)
            return user

        except IntegrityError as e:
            await session.rollback()
            print(f"Ошибка при сохранении пользователя: {e}")
            return None






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
    async with async_session() as session:
        result = await session.execute(
            select(Reminder)
        )
        reminders = result.scalars().all()
        return reminders

async def delete_expired_reminders():
    async with async_session() as session:
        stmt = delete(Reminder).where(Reminder.reminder_time <= datetime.now())
        result = await session.execute(stmt)
        await session.commit()
        print(f"[Cleaner] Deleted {result.rowcount} expired reminders")

async def delete_reminder_by_id(reminder_id: int):
    async with async_session() as session:
        stmt = delete(Reminder).where(Reminder.id == reminder_id)
        await session.execute(stmt)
        await session.commit()

async def get_all_reminders_all():
    async with async_session() as session:
        result = await session.execute(select(Reminder))
        return result.scalars().all()







