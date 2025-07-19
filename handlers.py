from aiogram import Router, F, BaseMiddleware, Bot
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from typing import Callable, Dict, Any
import re

from database import create_user_remind, get_user_reminders, delete_reminder_by_id, create_or_update_user, is_registered
import keyboards as kb
from aiogram_calendar import SimpleCalendar
from aiogram_timepicker import TimePicker, timepicker_callback

class user_remind(StatesGroup):
    name_remind = State()
    time_remind = State()
    message_remind = State()
    delete_index = State()
    show_index = State()

router = Router()

# Check if the user is registered
class RegistrationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable,
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            if event.text and event.text.startswith(('/register', '/start', '/help')):
                return await handler(event, data)

            telegram_id = event.from_user.id
            if not await is_registered(telegram_id):
                await event.answer("❌ You are not registered. Use /register.")
                return

        elif isinstance(event, CallbackQuery):
            # ✅ Разрешаем callback-запросы, соответствующие таймзоне (например: "+2", "-3", "0")
            if event.data and re.fullmatch(r"[+-]?\d{1,2}", event.data):
                return await handler(event, data)

            telegram_id = event.from_user.id
            if not await is_registered(telegram_id):
                await event.answer("❌ You are not registered. Use /register.", show_alert=True)
                return

        return await handler(event, data)

# Command start
@router.message(CommandStart())
async def command_start(message: Message):
    await message.answer('👋 Welcome to the Reminder Bot! Press /help to find out what this bot can do!')

# Command help
@router.message(Command("help"))
async def command_help(message: Message):
    await message.answer(
        "ℹ️ <b>Help Menu</b>\n\n"
        "🚀 <b>/start</b> — Start interacting with the bot\n"
        "📝 <b>/register</b> — Register yourself to use the bot\n"
        "📋 <b>/list</b> — Shows the current reminders\n"
        "❓ <b>/help</b> — Show this help menu",
        parse_mode="HTML"
    )

# Command list
@router.message(Command('list'))
async def command_list(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    reminders = await get_user_reminders(telegram_id)

    if reminders:
        await state.update_data(reminder_ids=[r['id'] for r in reminders])

        response = "📋 Your reminders:\n\n"
        for i, r in enumerate(reminders, start=1):
            response += f"{i}. 📌 {r['title']} — {r['reminder_time']}\n"
    else:
        response = "📋 Your reminders:\n\n"\
                   "🗒 You don't have any reminders yet."

    await message.answer(response, reply_markup=kb.remind_keyboard)


# Command show
@router.callback_query(F.data == "show")
async def command_show(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    reminders = await get_user_reminders(telegram_id)

    if not reminders:
        await callback.message.answer("🗒 You don't have any reminders yet.")
        return

    await state.update_data(reminder_ids=[r['id'] for r in reminders])
    await state.update_data(full_reminders=reminders)

    response = "<b>📋 Your reminders:</b>\n\n"
    for i, r in enumerate(reminders, start=1):
        response += f"{i}. 📌 {r['title']} — {r['reminder_time']}\n"

    await callback.message.answer(response)
    await callback.message.answer("Enter the number of the reminder you want to view:")
    await state.set_state(user_remind.show_index)

# Handler for command show
@router.message(user_remind.show_index)
async def handler_show(message: Message, state: FSMContext):
    data = await state.get_data()
    reminders = data.get("full_reminders", [])

    try:
        index = int(message.text.strip()) - 1
        if index < 0 or index >= len(reminders):
            raise ValueError

        reminder = reminders[index]

        response = (
            f"📌 <b>{reminder['title']}</b>\n"
            f"⏰ <b>Time:</b> {reminder['reminder_time']}\n"
            f"💬 <b>Message:</b> {reminder['message']}"
        )
        await message.answer(response, parse_mode="HTML")

    except (ValueError, IndexError):
        await message.answer("❌ Invalid number. Try again.")

    await state.clear()

# Command delete
@router.callback_query(F.data == "delete")
async def command_delete(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    telegram_id = callback.from_user.id

    reminders = await get_user_reminders(telegram_id)
    if not reminders:
        await callback.message.answer("🗒 You don't have any reminders yet.")
        return

    await state.update_data(reminder_ids=[r['id'] for r in reminders])

    response = "<b>📋 Your reminders:</b>\n\n"
    for i, r in enumerate(reminders, start=1):
        response += f"{i}. 📌 {r['title']} — {r['reminder_time']}\n"

    await callback.message.answer(response, parse_mode="HTML")
    await callback.message.answer("Enter the number of the reminder you want to delete:")
    await state.set_state(user_remind.delete_index)

# Handler for command delete
@router.message(user_remind.delete_index)
async def handler_delete(message: Message, state: FSMContext):
    data = await state.get_data()
    reminder_ids = data.get("reminder_ids")

    try:
        index = int(message.text.strip()) - 1
        if index < 0 or index >= len(reminder_ids):
            raise ValueError

        reminder_id = reminder_ids[index]
        await delete_reminder_by_id(reminder_id)
        await message.answer("✅ The reminder has been successfully removed.")
    except (ValueError, IndexError):
        await message.answer("❌ Invalid number. Try again.")

    await state.clear()

# Command create
@router.callback_query(F.data == "create")
async def command_create(callback: CallbackQuery, state: FSMContext):
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

# Handler for command create, handler for a name of reminder
@router.message(user_remind.name_remind)
async def handler_create_name(message: Message, state: FSMContext, bot: Bot):
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
        '<b># Please select the time of the reminder. #</b>'
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
    # Показываем календарь для выбора даты
    await message.answer("📅 Please select a date:", reply_markup=await SimpleCalendar().start_calendar())
    await state.set_state(user_remind.time_remind)

# Новый handler для выбора даты через календарь
@router.callback_query(F.data.startswith("simple_calendar"))
async def process_simple_calendar(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    if selected:
        await state.update_data(date_remind=date.strftime('%Y-%m-%d'))
        await callback_query.message.answer(f"🕒 Please select a time:", reply_markup=TimePicker().as_markup())
        await state.set_state(user_remind.time_remind)  # Остаёмся в этом состоянии для выбора времени
    await callback_query.answer()

# Новый handler для выбора времени через timepicker
@router.callback_query(timepicker_callback.filter())
async def process_timepicker(callback_query: CallbackQuery, callback_data: dict, state: FSMContext, bot: Bot):
    time = TimePicker().convert_callback_data(callback_data)
    if time:
        data = await state.get_data()
        date_remind = data.get('date_remind')
        time_remind = f"{date_remind} {time.strftime('%H:%M')}"
        await state.update_data(time_remind=time_remind)
        # Обновляем сообщение и переходим к следующему шагу (ввод текста напоминания)
        reminder_message_id = data.get("reminder_message_id")
        name_remind = data.get('name_remind')
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
                chat_id=callback_query.message.chat.id,
                message_id=reminder_message_id,
                text=new_text,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            await callback_query.message.answer("❗ Failed to update message.")
        await callback_query.message.answer("💬 Please enter the message for the reminder:")
        await state.set_state(user_remind.message_remind)
    await callback_query.answer()

# Handler for command create, handler for a message of reminder
@router.message(user_remind.message_remind)
async def handler_create_message(message: Message, state: FSMContext, bot: Bot):
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

    await state.clear()

# Command registration
@router.message(Command('register'))
async def command_register(message: Message, state: FSMContext):

    await message.answer('Please select your time zone from the list (you need to select the same time as you are currently on).', reply_markup=kb.utc_times_keyboard)

# Handler registration of timezone
@router.callback_query(F.data.regexp(r"^[+-]?\d{1,2}$"))
async def handle_timezone_callback(callback: CallbackQuery):
    user_timezone = callback.data
    telegram_id = callback.from_user.id

    await callback.message.answer(f"Great! Your timezone: UTC{user_timezone}")
    await callback.answer()

    await create_or_update_user(telegram_id, user_timezone)




