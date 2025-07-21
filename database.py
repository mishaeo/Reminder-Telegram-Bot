from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, selectinload
from sqlalchemy import Column, Integer, String, DateTime, select, delete, ForeignKey, BigInteger
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import TIMESTAMP

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
    telegram_id = Column(BigInteger, nullable=False, unique=True)
    timezone = Column(String, nullable=True)

    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # внешний ключ
    title = Column(String, nullable=False)
    reminder_time = Column(TIMESTAMP(timezone=True), nullable=False)
    message = Column(String)

    user = relationship("User", back_populates="reminders")

async def init_db():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def create_user_remind(telegram_id: int, title: str, reminder_time, message: str):
    async with async_session() as session:
        # Получаем user_id по telegram_id
        result = await session.execute(
            select(User.id).where(User.telegram_id == telegram_id)
        )
        user_id = result.scalar()

        if not user_id:
            raise ValueError(f"Пользователь с telegram_id {telegram_id} не найден")

        # Убираем секунды и микросекунды
        reminder_time = reminder_time.replace(second=0, microsecond=0)

        # Создаём напоминание
        reminder = Reminder(
            user_id=user_id,
            title=title,
            reminder_time=reminder_time,
            message=message
        )

        session.add(reminder)
        await session.commit()

async def create_or_update_user(telegram_id: int, timezone: str):
    async with async_session() as session:
        try:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalars().first()

            if user:
                user.timezone = timezone
                print(f"Пользователь {telegram_id} найден — обновлены данные.")
            else:
                user = User(
                    telegram_id=telegram_id,
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
        # Получаем user_id по telegram_id
        result = await session.execute(select(User.id).where(User.telegram_id == telegram_id))
        user_id = result.scalar()

        if not user_id:
            return []

        stmt = select(Reminder).where(Reminder.user_id == user_id).order_by(Reminder.reminder_time)
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
        stmt = delete(Reminder).where(Reminder.reminder_time <= datetime.now(timezone.utc))
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
        result = await session.execute(
            select(Reminder).options(selectinload(Reminder.user))
        )
        return result.scalars().all()

async def is_registered(telegram_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        return user is not None


