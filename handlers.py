from aiogram import Router, F, BaseMiddleware, Bot
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from typing import Callable, Dict, Any, Coroutine
import re

from database import create_user_remind, get_user_reminders, delete_reminder_by_id, create_or_update_user, is_registered, async_session, User, update_reminder_by_id
import keyboards as kb
from sqlalchemy import select
import pytz

class user_remind(StatesGroup):
    name_remind = State()
    time_remind = State()
    message_remind = State()
    delete_index = State()
    show_index = State()
    ### new ###
    edit_index = State()  # новое состояние для выбора напоминания для редактирования
    edit_name = State()   # новое состояние для редактирования имени
    edit_time = State()   # новое состояние для редактирования времени
    edit_message = State()# новое состояние для редактирования сообщения

router = Router()

# Helper function to generate the list of reminders text
async def get_reminders_list_text(telegram_id: int) -> str:
    """
    Generates the text for the list of reminders.
    """
    reminders = await get_user_reminders(telegram_id)
    if not reminders:
        return "📋 Your reminders:\n\n🗒 You don't have any reminders yet."

    # Fetch user's timezone from DB
    async with async_session() as session:
        result = await session.execute(
            select(User.timezone).where(User.telegram_id == telegram_id)
        )
        timezone_offset_str = result.scalar()
    timezone_offset = int(timezone_offset_str)
    tz = pytz.FixedOffset(timezone_offset * 60)

    response = "📋 Your reminders:\n\n"
    for i, r in enumerate(reminders, start=1):
        local_dt = r['reminder_time'].astimezone(tz)
        local_time_str = local_dt.strftime("%Y-%m-%d %H:%M")
        response += f"{i}. 📌 {r['title']} — {local_time_str}\n"
    return response

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
    response = await get_reminders_list_text(telegram_id)
    sent_message = await message.answer(response, reply_markup=kb.remind_keyboard)
    await state.update_data(list_message_id=sent_message.message_id)


# Handler for "Back" button
@router.callback_query(F.data == "back_to_list")
async def back_to_list_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    telegram_id = callback.from_user.id
    response = await get_reminders_list_text(telegram_id)
    await callback.message.edit_text(response, reply_markup=kb.remind_keyboard)
    await state.clear()


# Command show
@router.callback_query(F.data == "show")
async def command_show(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    telegram_id = callback.from_user.id
    reminders = await get_user_reminders(telegram_id)

    if not reminders:
        await callback.message.edit_text("🗒 You don't have any reminders yet.", reply_markup=kb.back_keyboard)
        return

    await state.update_data(full_reminders=reminders)
    list_text = await get_reminders_list_text(telegram_id)
    prompt_text = "\n\nEnter the number of the reminder you want to view:"
    
    await callback.message.edit_text(list_text + prompt_text, reply_markup=kb.back_keyboard)
    await state.set_state(user_remind.show_index)

# Handler for command show
@router.message(user_remind.show_index)
async def handler_show(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    data = await state.get_data()
    reminders = data.get("full_reminders", [])
    list_message_id = data.get("list_message_id")
    telegram_id = message.from_user.id

    try:
        index = int(message.text.strip()) - 1
        if index < 0 or index >= len(reminders):
            raise ValueError

        reminder = reminders[index]

        # Fetch user's timezone from DB
        async with async_session() as session:
            result = await session.execute(
                select(User.timezone).where(User.telegram_id == telegram_id)
            )
            timezone_offset_str = result.scalar()
        timezone_offset = int(timezone_offset_str)

        # Convert UTC time to user's local time
        utc_dt = reminder['reminder_time']
        tz = pytz.FixedOffset(timezone_offset * 60)
        local_dt = utc_dt.astimezone(tz)
        local_time_str = local_dt.strftime("%Y-%m-%d %H:%M")

        response = (
            f"📌 <b>{reminder['title']}</b>\n"
            f"⏰ <b>Time:</b> {local_time_str}\n"
            f"💬 <b>Message:</b> {reminder['message']}"
        )
        await bot.edit_message_text(chat_id=message.chat.id, message_id=list_message_id, text=response, parse_mode="HTML", reply_markup=kb.back_keyboard)

    except (ValueError, IndexError):
        list_text = await get_reminders_list_text(telegram_id)
        error_text = "❌ Invalid number. Try again."
        await bot.edit_message_text(chat_id=message.chat.id, message_id=list_message_id, text=list_text + "\n\n" + error_text, reply_markup=kb.back_keyboard)
        return # Keep state for another try

    await state.clear()

# Command delete
@router.callback_query(F.data == "delete")
async def command_delete(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    telegram_id = callback.from_user.id
    reminders = await get_user_reminders(telegram_id)

    if not reminders:
        await callback.message.edit_text("🗒 You don't have any reminders yet.", reply_markup=kb.back_keyboard)
        return

    await state.update_data(reminder_ids=[r['id'] for r in reminders])
    list_text = await get_reminders_list_text(telegram_id)
    prompt_text = "\n\nEnter the number of the reminder you want to delete:"

    await callback.message.edit_text(list_text + prompt_text, reply_markup=kb.back_keyboard)
    await state.set_state(user_remind.delete_index)


# Handler for command delete
@router.message(user_remind.delete_index)
async def handler_delete(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    data = await state.get_data()
    reminder_ids = data.get("reminder_ids")
    list_message_id = data.get("list_message_id")
    telegram_id = message.from_user.id

    try:
        index = int(message.text.strip()) - 1
        if index < 0 or index >= len(reminder_ids):
            raise ValueError

        reminder_id = reminder_ids[index]
        await delete_reminder_by_id(reminder_id)
        
        new_list_text = await get_reminders_list_text(telegram_id)
        success_text = "✅ The reminder has been successfully removed."
        
        await bot.edit_message_text(chat_id=message.chat.id, message_id=list_message_id, text=new_list_text + "\n\n" + success_text, reply_markup=kb.remind_keyboard)

    except (ValueError, IndexError):
        list_text = await get_reminders_list_text(telegram_id)
        error_text = "❌ Invalid number. Try again."
        await bot.edit_message_text(chat_id=message.chat.id, message_id=list_message_id, text=list_text + "\n\n" + error_text, reply_markup=kb.back_keyboard)
        return # Keep state

    await state.clear()

# Command create
@router.callback_query(F.data == "create")
async def command_create(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    await callback.message.edit_text(
        '<b>📌 Create a new reminder</b>\n\n'
        '<b>❌ | 📝 Reminder name: </b>\n'
        '<b>❌ | ⏰ Time to receive reminder: </b>\n'
        '<b>❌ | 💬 Reminder message: </b>\n\n'
        '<b># Please select the name of the reminder, no more than 20 characters #</b>',
        parse_mode=ParseMode.HTML,
        reply_markup=kb.back_keyboard
    )
    await state.update_data(reminder_message_id=callback.message.message_id)
    await state.set_state(user_remind.name_remind)

# Handler for command create, handler for a name of reminder
@router.message(user_remind.name_remind)
async def handler_create_name(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    name_remind = message.text
    data = await state.get_data()
    reminder_message_id = data.get("reminder_message_id")
    
    if len(name_remind) > 20:
        error_text = "❌ The reminder name must not exceed 20 characters. Please enter a shorter name."
        current_text = (
            '<b>📌 Create a new reminder</b>\n\n'
            '<b>❌ | 📝 Reminder name: </b>\n'
            '<b>❌ | ⏰ Time to receive reminder: </b>\n'
            '<b>❌ | 💬 Reminder message: </b>\n\n'
            '<b># Please select the name of the reminder, no more than 20 characters #</b>'
        )
        await bot.edit_message_text(
            chat_id=message.chat.id, message_id=reminder_message_id,
            text=f"{error_text}\n\n{current_text}",
            parse_mode=ParseMode.HTML, reply_markup=kb.back_keyboard
        )
        return

    await state.update_data(name_remind=name_remind)

    new_text = (
        '<b>📌 Create a new reminder</b>\n\n'
        '<b>✅ | 📝 Reminder name:</b> '
        f'<b>{name_remind}</b>\n'
        '<b>❌ | ⏰ Time to receive reminder: </b>\n'
        '<b>❌ | 💬 Reminder message: </b>\n\n'
        '<b># Please select the time of the reminder. Example: YYYY-MM-DD HH:MM #</b>'
    )
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=reminder_message_id,
        text=new_text,
        parse_mode=ParseMode.HTML,
        reply_markup=kb.back_keyboard
    )
    await state.set_state(user_remind.time_remind)

# Handler for command create, handler for a date of reminder
@router.message(user_remind.time_remind)
async def handler_create_date(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    data = await state.get_data()
    reminder_message_id = data.get("reminder_message_id")
    name_remind = data.get('name_remind')
    telegram_id = message.from_user.id
    time_remind_str = message.text.strip()
    
    base_text = (
        '<b>📌 Create a new reminder</b>\n\n'
        f'<b>✅ | 📝 Reminder name:</b> <b>{name_remind}</b>\n'
        '<b>❌ | ⏰ Time to receive reminder: </b>\n'
        '<b>❌ | 💬 Reminder message: </b>\n\n'
        '<b># Please select the time of the reminder. Example: YYYY-MM-DD HH:MM #</b>'
    )

    try:
        dt_naive = datetime.strptime(time_remind_str, '%Y-%m-%d %H:%M')
    except ValueError:
        error_text = "❌ Invalid time format. Please enter in format: <b>YYYY-MM-DD HH:MM</b>"
        await bot.edit_message_text(
            chat_id=message.chat.id, message_id=reminder_message_id,
            text=f"{error_text}\n\n{base_text}", parse_mode="HTML", reply_markup=kb.back_keyboard
        )
        return

    # Получаем смещение пользователя
    async with async_session() as session:
        result = await session.execute(
            select(User.timezone).where(User.telegram_id == telegram_id)
        )
        timezone_offset_str = result.scalar()
    timezone_offset = int(timezone_offset_str)

    # Локализуем время пользователя
    tz = pytz.FixedOffset(timezone_offset * 60)
    dt_local = tz.localize(dt_naive)

    # Проверка, что время не в прошлом (локальное время пользователя)
    now_local = datetime.now(tz)
    if dt_local < now_local:
        error_text = "❌ The specified time has already passed. Please enter a future time."
        await bot.edit_message_text(
            chat_id=message.chat.id, message_id=reminder_message_id,
            text=f"{error_text}\n\n{base_text}", parse_mode="HTML", reply_markup=kb.back_keyboard
        )
        return

    # Переводим в UTC
    dt_utc = dt_local.astimezone(pytz.UTC)
    await state.update_data(time_remind=dt_utc, time_remind_str=time_remind_str)

    new_text = (
        '<b>📌 Create a new reminder</b>\n\n'
        f'<b>✅ | 📝 Reminder name:</b> <b>{name_remind}</b>\n'
        f'<b>✅ | ⏰ Time to receive reminder: </b> <b>{time_remind_str}</b>\n'
        '<b>❌ | 💬 Reminder message: </b>\n\n'
        '<b># Please Enter the message of the reminder. #</b>'
    )
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=reminder_message_id,
        text=new_text,
        parse_mode=ParseMode.HTML,
        reply_markup=kb.back_keyboard
    )
    await state.set_state(user_remind.message_remind)

# Handler for command create, handler for a message of reminder
@router.message(user_remind.message_remind)
async def handler_create_message(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    telegram_id = message.from_user.id
    data = await state.get_data()
    reminder_message_id = data.get("reminder_message_id")
    name_remind = data.get('name_remind')
    time_remind = data.get('time_remind')
    time_remind_str = data.get('time_remind_str')
    message_remind = message.text

    await create_user_remind(
        telegram_id=telegram_id,
        title=name_remind,
        reminder_time=time_remind,
        message=message_remind
    )
    
    new_text = (
        '<b>📌 Create a new reminder</b>\n\n'
        f'<b>✅ | 📝 Reminder name:</b> <b>{name_remind}</b>\n'
        f'<b>✅ | ⏰ Time to receive reminder: </b> <b>{time_remind_str}</b>\n'
        f'<b>✅ | 💬 Reminder message: </b> <b>{message_remind}</b>\n\n'
        '<b># Excellent, the reminder is ready. #</b>'
    )
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=reminder_message_id,
        text=new_text,
        parse_mode=ParseMode.HTML,
        reply_markup=kb.back_keyboard # Allows to go back to list
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

@router.callback_query(F.data == "edit")
async def command_edit(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    telegram_id = callback.from_user.id
    reminders = await get_user_reminders(telegram_id)

    if not reminders:
        await callback.message.edit_text("🗒 You don't have any reminders yet.", reply_markup=kb.back_keyboard)
        return

    # Save data for later use
    await state.update_data(
        full_reminders=reminders,
        list_message_id=callback.message.message_id
    )

    list_text = await get_reminders_list_text(telegram_id)
    prompt_text = "\n\nEnter the number of the reminder you want to edit:"
    
    await callback.message.edit_text(list_text + prompt_text, reply_markup=kb.back_keyboard)
    await state.set_state(user_remind.edit_index)


@router.message(user_remind.edit_index)
async def handler_edit_select(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    data = await state.get_data()
    reminders = data.get("full_reminders", [])
    list_message_id = data.get("list_message_id")
    telegram_id = message.from_user.id

    try:
        index = int(message.text.strip()) - 1
        if index < 0 or index >= len(reminders):
            raise ValueError
        reminder = reminders[index]

        # Fetch user's timezone from DB
        async with async_session() as session:
            result = await session.execute(select(User.timezone).where(User.telegram_id == telegram_id))
            timezone_offset_str = result.scalar()
        timezone_offset = int(timezone_offset_str)
        tz = pytz.FixedOffset(timezone_offset * 60)
        local_dt = reminder['reminder_time'].astimezone(tz)
        local_time_str = local_dt.strftime("%Y-%m-%d %H:%M")

        await state.update_data(
            editing_reminder_id=reminder['id'],
            editing_reminder_title=reminder['title'],
            editing_reminder_time=reminder['reminder_time'],
            editing_reminder_message=reminder['message'],
            timezone_offset=timezone_offset
        )

        # Send the edit form
        edit_form_text = (
            '<b>✏️ Edit reminder</b>\n\n'
            f'<b>✅ | 📝 Reminder name:</b>\n <b>{reminder["title"]}</b>\n'
            f'<b>✅ | ⏰ Time to receive reminder: </b>\n<b>{local_time_str}</b>\n'
            f'<b>✅ | 💬 Reminder message: </b>\n<b>{reminder["message"]}</b>\n\n'
            '<b># Enter a new name for the reminder (or send the same to keep it). #</b>'
        )
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=list_message_id,
            text=edit_form_text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb.back_keyboard
        )
        await state.set_state(user_remind.edit_name)

    except (ValueError, IndexError):
        list_text = await get_reminders_list_text(telegram_id)
        error_text = "❌ Invalid number. Try again."
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=list_message_id,
            text=f"{list_text}\n\n{error_text}",
            reply_markup=kb.back_keyboard
        )
        # Don't clear state, let user try again


@router.message(user_remind.edit_name)
async def handler_edit_name(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    new_name = message.text
    data = await state.get_data()
    list_message_id = data.get("list_message_id")

    # Get original reminder data for the template
    timezone_offset = data.get('timezone_offset')
    tz = pytz.FixedOffset(timezone_offset * 60)
    original_time_utc = data.get('editing_reminder_time')
    original_time_local_str = original_time_utc.astimezone(tz).strftime("%Y-%m-%d %H:%M")
    original_message = data.get('editing_reminder_message')

    base_text = (
        '<b>✏️ Edit reminder</b>\n\n'
        f'<b>✅ | 📝 Reminder name:</b>\n <b>{new_name}</b>\n'
        f'<b>✅ | ⏰ Time to receive reminder: </b>\n<b>{original_time_local_str}</b>\n'
        f'<b>✅ | 💬 Reminder message: </b>\n<b>{original_message}</b>\n\n'
    )

    if len(new_name) > 20:
        error_text = "❌ The reminder name must not exceed 20 characters. Please enter a shorter name."
        await bot.edit_message_text(
            chat_id=message.chat.id, message_id=list_message_id,
            text=f"{error_text}\n\n{base_text}", parse_mode=ParseMode.HTML, reply_markup=kb.back_keyboard
        )
        return

    await state.update_data(editing_reminder_title=new_name)
    
    prompt_text = '<b># Enter a new time for the reminder. Example: YYYY-MM-DD HH:MM #</b>'

    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=list_message_id,
        text=base_text + prompt_text,
        parse_mode=ParseMode.HTML,
        reply_markup=kb.back_keyboard
    )
    await state.set_state(user_remind.edit_time)

@router.message(user_remind.edit_time)
async def handler_edit_time(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    data = await state.get_data()
    list_message_id = data.get("list_message_id")
    name_remind = data.get('editing_reminder_title')
    original_message = data.get('editing_reminder_message')
    time_remind_str = message.text.strip()
    
    base_text_template = (
        '<b>✏️ Edit reminder</b>\n\n'
        f'<b>✅ | 📝 Reminder name:</b>\n <b>{name_remind}</b>\n'
        '<b>✅ | ⏰ Time to receive reminder: </b>\n<b>{time_str}</b>\n'
        f'<b>✅ | 💬 Reminder message: </b>\n<b>{original_message}</b>\n\n'
    )

    try:
        dt_naive = datetime.strptime(time_remind_str, '%Y-%m-%d %H:%M')
    except ValueError:
        error_text = "❌ Invalid time format. Please enter in format: <b>YYYY-MM-DD HH:MM</b>"
        # We need the old time to display in the error message
        timezone_offset = data.get('timezone_offset')
        tz = pytz.FixedOffset(timezone_offset * 60)
        old_time_utc = data.get('editing_reminder_time')
        old_time_local_str = old_time_utc.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        base_text = base_text_template.format(time_str=old_time_local_str)
        await bot.edit_message_text(
            chat_id=message.chat.id, message_id=list_message_id,
            text=f"{error_text}\n\n{base_text}", parse_mode="HTML", reply_markup=kb.back_keyboard
        )
        return

    timezone_offset = data.get('timezone_offset')
    tz = pytz.FixedOffset(timezone_offset * 60)
    dt_local = tz.localize(dt_naive)
    now_local = datetime.now(tz)
    if dt_local < now_local:
        error_text = "❌ The specified time has already passed. Please enter a future time."
        old_time_utc = data.get('editing_reminder_time')
        old_time_local_str = old_time_utc.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        base_text = base_text_template.format(time_str=old_time_local_str)
        await bot.edit_message_text(
            chat_id=message.chat.id, message_id=list_message_id,
            text=f"{error_text}\n\n{base_text}", parse_mode="HTML", reply_markup=kb.back_keyboard
        )
        return

    dt_utc = dt_local.astimezone(pytz.UTC)
    await state.update_data(editing_reminder_time=dt_utc)
    
    prompt_text = '<b># Enter a new message for the reminder. #</b>'
    new_base_text = base_text_template.format(time_str=time_remind_str)
    
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=list_message_id,
        text=new_base_text + prompt_text,
        parse_mode=ParseMode.HTML,
        reply_markup=kb.back_keyboard
    )
    await state.set_state(user_remind.edit_message)


@router.message(user_remind.edit_message)
async def handler_edit_message(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    telegram_id = message.from_user.id
    data = await state.get_data()
    list_message_id = data.get("list_message_id")
    
    # Get all the final data
    name_remind = data.get('editing_reminder_title')
    time_remind_utc = data.get('editing_reminder_time')
    message_remind = message.text
    editing_reminder_id = data.get('editing_reminder_id')

    # Update reminder in DB
    await update_reminder_by_id(
        reminder_id=editing_reminder_id,
        title=name_remind,
        reminder_time=time_remind_utc,
        message=message_remind
    )
    
    # Get local time for final display
    timezone_offset = data.get('timezone_offset')
    tz = pytz.FixedOffset(timezone_offset * 60)
    local_dt = time_remind_utc.astimezone(tz)
    local_time_str = local_dt.strftime("%Y-%m-%d %H:%M")

    final_text = (
        '<b>✏️ Edit reminder</b>\n\n'
        f'<b>✅ | 📝 Reminder name:</b>\n <b>{name_remind}</b>\n'
        f'<b>✅ | ⏰ Time to receive reminder: </b>\n<b>{local_time_str}</b>\n'
        f'<b>✅ | 💬 Reminder message: </b>\n<b>{message_remind}</b>\n\n'
        '<b># Excellent, the reminder is updated. #</b>'
    )
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=list_message_id,
        text=final_text,
        parse_mode=ParseMode.HTML,
        reply_markup=kb.back_keyboard
    )
    
    # Send a confirmation message and then show the main list
    await message.answer("✅ The reminder has been successfully updated.")
    
    # Go back to the main list
    final_list = await get_reminders_list_text(telegram_id)
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=list_message_id,
        text=final_list,
        parse_mode=ParseMode.HTML,
        reply_markup=kb.remind_keyboard
    )
    await state.clear()