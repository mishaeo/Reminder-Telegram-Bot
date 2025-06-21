from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from apscheduler.triggers.date import DateTrigger
import asyncio

from database import create_or_update_user
from bot_instance import bot


router = Router()

scheduler = AsyncIOScheduler()

class Reminder(StatesGroup):
    date = State()
    time = State()
    person_message = State()
    user_id = State()

@router.message(CommandStart())
async def start(message: Message):
    await message.answer("👋 Welcome to the reminder bot! To find out what this bot can do, click /help")

@router.message(Command("help"))
async def handler_help(message: Message):
    await message.answer(
        "📖 <b>Меню помощи</b>\n\n"
        "🚀 <b>/start</b> — Начать работу с ботом\n"
        "⏰ <b>/remind</b> — Добавить или обновить напоминание\n"
        "❓ <b>/help</b> — Показать это меню",
        parse_mode="HTML"
    )

@router.message(Command('remind'))
async def create_remind(message: Message, state: FSMContext):
    user_id = message.from_user.id

    await state.update_data(user_id=user_id)

    await message.answer("Enter the message you want the bot to remind you of:")
    await state.set_state(Reminder.person_message)

@router.message(Reminder.person_message)
async def remember_message(message: Message, state: FSMContext):
    person_message = message.text

    await state.update_data(person_message=person_message)

    await message.answer("Enter the date when the bot should remind you: (year-month-day)")
    await state.set_state(Reminder.date)

@router.message(Reminder.date)
async def remember_date(message: Message, state: FSMContext):
    date = message.text

    await state.update_data(date=date)

    await message.answer("Enter the time when the bot should remind you: (hour:minutes)")
    await state.set_state(Reminder.time)

async def send_reminder(telegram_id: int, message: str):
    try:
        await bot.send_message(telegram_id, f"🔔 Напоминание: {message}")
    except Exception as e:
        print(f"Ошибка при отправке напоминания: {e}")

@router.message(Reminder.time)
async def remember_message(message: Message, state: FSMContext):
    time = message.text

    await state.update_data(time=time)

    data = await state.get_data()
    user_id = data.get('user_id')
    date = data.get('date')
    person_message = data.get('person_message')
    time = data.get('time')

    await message.answer(f"### ОТЛАДКА ###\n Your telegram_id: {user_id}\n Your message: {person_message}\n Your date: {date}\n Your time: {time}")

    await create_or_update_user(
        telegram_id=user_id,
        time=time,
        date=date,
        message=person_message
    )

    await state.clear()

    remind_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")

    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(run_date=remind_datetime),
        args=[user_id, person_message],
        id=f"{user_id}_{remind_datetime}",
        replace_existing=True
    )