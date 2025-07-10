import asyncio
from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from aiogram import Bot


class user_remind(StatesGroup):
    name_remind = State()
    time_remind = State()
    message_remind = State()

router = Router()

async def schedule_message(name_remind, message_remind, time_remind, message: Message):
    target_time = datetime.strptime(time_remind, '%Y-%m-%d %H:%M')

    while True:
        now = datetime.now().replace(second=0, microsecond=0)
        if now >= target_time:
            await message.answer(
                f"Сообщение: {name_remind}\n "
                f"{message_remind}\n"
                f"(отправлено в {now.strftime('%Y-%m-%d %H:%M')})")
            break
        await asyncio.sleep(1)

@router.message(CommandStart())
async def handler_start(message: Message):
    await message.answer('👋 Welcome to the Reminder Bot! Press /help to find out what this bot can do!')

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
    sent_msg = await message.answer(
        '<b>📌 Create a new reminder</b>\n\n'
        '<b>❌ | 📝 Reminder name: </b>\n'
        '<b>❌ | ⏰ Time to receive reminder: </b>\n'
        '<b>❌ | 💬 Reminder message: </b>\n\n'
        '<b># Please select the name of the reminder #</b>',
        parse_mode=ParseMode.HTML
    )
    await state.update_data(reminder_message_id=sent_msg.message_id)
    await state.set_state(user_remind.name_remind)

@router.message(user_remind.name_remind)
async def handler_select_time_remind(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    reminder_message_id = data.get("reminder_message_id")

    name_remind = message.text
    await state.update_data(name_remind=name_remind)

    new_text = (
        '<b>📌 Create a new reminder</b>\n\n'
        '<b>✅ | 📝 Reminder name:</b>\n '
        f'<b>{name_remind}</b>\n'
        '<b>❌ | ⏰ Time to receive reminder: </b>\n'
        '<b>❌ | 💬 Reminder message: </b>\n\n'
        '<b># Please select the time of the reminder. Example: YYYY-MM-DD HH:MM #</b>'
    )
    try:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=reminder_message_id,
            text=new_text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.answer("❗ Failed to update message.")

    await state.set_state(user_remind.time_remind)

@router.message(user_remind.time_remind)
async def handler_select_message_remind(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    reminder_message_id = data.get("reminder_message_id")

    data = await state.get_data()
    name_remind = data.get('name_remind')

    time_remind = message.text
    await state.update_data(time_remind=time_remind)

    new_text = (
        '<b>📌 Create a new reminder</b>\n\n'
        '<b>✅ | 📝 Reminder name:</b>\n '
        f'<b>{name_remind}</b>\n'
        '<b>✅ | ⏰ Time to receive reminder: </b>\n'
        f'<b>{time_remind}</b>\n'
        '<b>❌ | 💬 Reminder message: </b>\n\n'
        '<b># Please Enter the message of the reminder. #</b>'
    )
    try:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=reminder_message_id,
            text=new_text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.answer("❗ Failed to update message.")

    await state.set_state(user_remind.message_remind)

@router.message(user_remind.message_remind)
async def handler_output(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    reminder_message_id = data.get("reminder_message_id")

    data = await state.get_data()
    name_remind = data.get('name_remind')
    time_remind = data.get('time_remind')

    message_remind = message.text
    await state.update_data(message_remind=message_remind)

    new_text = (
        '<b>📌 Create a new reminder</b>\n\n'
        '<b>✅ | 📝 Reminder name:</b>\n '
        f'<b>{name_remind}</b>\n'
        '<b>✅ | ⏰ Time to receive reminder: </b>\n'
        f'<b>{time_remind}</b>\n'
        '<b>✅ | 💬 Reminder message: </b>\n'
        f'<b>{message_remind}</b>\n\n'
        '<b># Excellent, the reminder is ready. #</b>'
    )
    try:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=reminder_message_id,
            text=new_text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.answer("❗ Failed to update message.")

    asyncio.create_task(schedule_message(name_remind, message_remind, time_remind, message))