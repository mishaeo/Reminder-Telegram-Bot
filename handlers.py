from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command

import keyboards as kb

router = Router()

class Reminder(StatesGroup):
    date = State()
    time = State()
    person_message = State()
    user_id = State()

months = {
    '01': 'января',
    '02': 'февраля',
    '03': 'марта',
    '04': 'апреля',
    '05': 'мая',
    '06': 'июня',
    '07': 'июля',
    '08': 'августа',
    '09': 'сентября',
    '10': 'октября',
    '11': 'ноября',
    '12': 'декабря'
}

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

    await message.answer("Enter the date when the bot should remind you:")
    await state.set_state(Reminder.date)

@router.message(Reminder.date)
async def remember_date(message: Message, state: FSMContext):
    date = message.text

    await state.update_data(date=date)

    await message.answer("Enter the time when the bot should remind you:")
    await state.set_state(Reminder.time)

@router.message(Reminder.time)
async def remember_message(message: Message, state: FSMContext):
    time = message.text

    await state.update_data(time=time)

    data = await state.get_data()
    user_id = data.get('user_id')
    date = data.get('date')
    person_message = data.get('person_message')
    time = data.get('time')

    await message.answer(f"Your telegram_id: {user_id}\n Your message: {person_message}\n Your date: {date}\n Your time: {time}")