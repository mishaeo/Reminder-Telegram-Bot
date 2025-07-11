import asyncio
from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from aiogram import Bot

from database import create_user_remind, get_user_reminders, delete_reminder_by_id
import keyboards as kb


class user_remind(StatesGroup):
    name_remind = State()
    time_remind = State()
    message_remind = State()
    delete_index = State()
    show_index = State()

router = Router()

async def schedule_message(name_remind, message_remind, time_remind, message: Message):
    target_time = datetime.strptime(time_remind, '%Y-%m-%d %H:%M')

    while True:
        now = datetime.now().replace(second=0, microsecond=0)
        if now >= target_time:
            await message.answer(
                f"Your reminder: {name_remind}\n "
                f"{message_remind}\n"
                f"(Sent at {now.strftime('%Y-%m-%d %H:%M')})")
            break
        await asyncio.sleep(1)

@router.message(CommandStart())
async def handler_start(message: Message):
    await message.answer('👋 Welcome to the Reminder Bot! Press /help to find out what this bot can do!')

@router.message(Command("help"))
async def handler_help(message: Message):
    await message.answer(
        "ℹ️ <b>Help Menu</b>\n\n"
        "🚀 <b>/start</b> — Start interacting with the bot\n"
        "📋 <b>/list</b> — Shows the current reminders\n"
        "❓ <b>/help</b> — Show this help menu",
        parse_mode="HTML"
    )

@router.message(Command('list'))
async def list_reminders(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    reminders = await get_user_reminders(telegram_id)

    if not reminders:
        await message.answer("🗒 You don't have any reminders yet.")
        return

    await state.update_data(reminder_ids=[r['id'] for r in reminders])

    response = "📋 Your reminders:\n\n"
    for i, r in enumerate(reminders, start=1):
        response += f"{i}. 📌 {r['title']} — {r['reminder_time']}\n"

    await message.answer(response, reply_markup=kb.remind_keyboard)

@router.callback_query(F.data == "show")
async def handle_show_start(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    reminders = await get_user_reminders(telegram_id)

    if not reminders:
        await callback.message.answer("🗒 У вас пока нет напоминаний.")
        return

    await state.update_data(reminder_ids=[r['id'] for r in reminders])
    await state.update_data(full_reminders=reminders)  # сохраняем сами объекты напоминаний

    response = "🔍 Ваши напоминания:\n\n"
    for i, r in enumerate(reminders, start=1):
        response += f"{i}. 📌 {r['title']} — {r['reminder_time']}\n"

    await callback.message.answer(response)
    await callback.message.answer("Введите номер напоминания, которое хотите просмотреть:")
    await state.set_state(user_remind.show_index)

@router.message(user_remind.show_index)
async def handle_show_by_index(message: Message, state: FSMContext):
    data = await state.get_data()
    reminders = data.get("full_reminders", [])

    try:
        index = int(message.text.strip()) - 1
        if index < 0 or index >= len(reminders):
            raise ValueError

        reminder = reminders[index]

        response = (
            f"📌 <b>{reminder['title']}</b>\n"
            f"⏰ <b>Время:</b> {reminder['reminder_time']}\n"
            f"💬 <b>Сообщение:</b> {reminder['message']}"
        )
        await message.answer(response, parse_mode="HTML")

    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер. Попробуйте снова.")

    await state.clear()

@router.callback_query(F.data == "delete")
async def handle_delete_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("🗑 Введите номер напоминания, которое хотите удалить:")
    await state.set_state(user_remind.delete_index)

@router.message(user_remind.delete_index)
async def handle_delete_by_index(message: Message, state: FSMContext):
    data = await state.get_data()
    reminder_ids = data.get("reminder_ids")

    try:
        index = int(message.text.strip()) - 1
        if index < 0 or index >= len(reminder_ids):
            raise ValueError

        reminder_id = reminder_ids[index]
        await delete_reminder_by_id(reminder_id)
        await message.answer("✅ Напоминание успешно удалено.")
    except (ValueError, IndexError):
        await message.answer("❌ Неверный номер. Попробуйте снова.")

    await state.clear()

@router.callback_query(F.data == "create")
async def handler_select_name_remind(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    sent_msg = await callback.message.answer(
        '<b>📌 Create a new reminder</b>\n\n'
        '<b>❌ | 📝 Reminder name: </b>\n'
        '<b>❌ | ⏰ Time to receive reminder: </b>\n'
        '<b>❌ | 💬 Reminder message: </b>\n\n'
        '<b># Please select the name of the reminder, no more than 20 characters #</b>',
        parse_mode=ParseMode.HTML
    )
    await state.update_data(reminder_message_id=sent_msg.message_id)
    await state.set_state(user_remind.name_remind)

@router.message(user_remind.name_remind)
async def handler_select_time_remind(message: Message, state: FSMContext, bot: Bot):
    name_remind = message.text

    if len(name_remind) > 20:
        await message.answer(
            "❌ The reminder name must not exceed 20 characters. Please enter a shorter name.")
        return

    data = await state.get_data()
    reminder_message_id = data.get("reminder_message_id")

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
    name_remind = data.get('name_remind')

    time_remind = message.text.strip()

    try:
        datetime.strptime(time_remind, '%Y-%m-%d %H:%M')
    except ValueError:
        await message.answer("❌ Invalid time format. Please enter in format: <b>YYYY-MM-DD HH:MM</b>",
                             parse_mode="HTML")
        return

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
    telegram_id = message.from_user.id

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

    await create_user_remind(
        telegram_id=telegram_id,
        title=name_remind,
        reminder_time=time_remind,
        message=message_remind
    )

    asyncio.create_task(schedule_message(name_remind, message_remind, time_remind, message))

    await state.clear()