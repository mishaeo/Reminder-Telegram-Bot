from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

class user_remind(StatesGroup):
    name_remind = State()
    time_remind = State()
    message_remind = State()

router = Router()

@router.message(CommandStart())
async def handler_start(message: Message):
    await message.answer('👋 Welcome to the Reminder Bot! Press /help to find out what this bot can do')

@router.message(Command("help"))
async def handler_help(message: Message):
    await message.answer(
        "ℹ️ <b>Help Menu</b>\n\n"
        "🧾 <b>/start</b> — Start interacting with the bot\n"
        "🧾 <b>/remind</b> - Set a reminder\n"
        "❓ <b>/help</b> — Show this help menu",
        parse_mode="HTML"
    )

@router.message(Command("remind"))
async def handler_select_name_remind(message: Message, state: FSMContext):
    await message.answer('Select the name of the reminder.')
    await state.set_state(user_remind.name_remind)

@router.message(user_remind.name_remind)
async def handler_select_time_remind(message: Message, state: FSMContext):
    name_remind = message.text
    await state.update_data(name_remind=name_remind)

    await message.answer('Select the time of the reminder. Here is an example: YYYY-MM-DD HH:MM')
    await state.set_state(user_remind.time_remind)

@router.message(user_remind.time_remind)
async def handler_select_message_remind(message: Message, state: FSMContext):
    time_remind = message.text
    await state.update_data(time_remind=time_remind)

    await message.answer('Enter the message of the reminder.')
    await state.set_state(user_remind.message_remind)

@router.message(user_remind.message_remind)
async def handler_output(message: Message, state: FSMContext):
    message_remind = message.text
    await state.update_data(message_remind=message_remind)

    data = await state.get_data()

    time_remind = data.get('time_remind')
    name_remind = data.get('name_remind')

    await message.answer(f"Your name of remind: {name_remind}\n Your time of remind: {time_remind}\n Your message of remind: {message_remind}")
