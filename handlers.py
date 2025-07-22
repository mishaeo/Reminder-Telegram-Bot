from aiogram import Router, F, BaseMiddleware, Bot
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from typing import Callable, Dict, Any
import re

from database import create_user_remind, get_user_reminders, delete_reminder_by_id, create_or_update_user, is_registered, async_session, User
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

    # Fetch user's timezone from DB
    async with async_session() as session:
        result = await session.execute(
            select(User.timezone).where(User.telegram_id == telegram_id)
        )
        timezone_offset_str = result.scalar()
        if timezone_offset_str is None:
            await message.answer("❌ Timezone not set. Please register your timezone with /register.")
            return
        try:
            timezone_offset = int(timezone_offset_str)
        except ValueError:
            await message.answer("❌ Invalid timezone value in your profile. Please re-register your timezone.")
            return
    tz = pytz.FixedOffset(timezone_offset * 60)

    if reminders:
        await state.update_data(reminder_ids=[r['id'] for r in reminders])

        response = "📋 Your reminders:\n\n"
        for i, r in enumerate(reminders, start=1):
            local_dt = r['reminder_time'].astimezone(tz)
            local_time_str = local_dt.strftime("%Y-%m-%d %H:%M")
            response += f"{i}. 📌 {r['title']} — {local_time_str}\n"
    else:
        response = "📋 Your reminders:\n\n"\
                   "🗒 You don't have any reminders yet."

    await message.answer(response, reply_markup=kb.remind_keyboard)


# Command show
@router.callback_query(F.data == "show")
async def command_show(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    reminders = await get_user_reminders(telegram_id)

    # Fetch user's timezone from DB
    async with async_session() as session:
        result = await session.execute(
            select(User.timezone).where(User.telegram_id == telegram_id)
        )
        timezone_offset_str = result.scalar()
        if timezone_offset_str is None:
            await callback.message.answer("❌ Timezone not set. Please register your timezone with /register.")
            return
        try:
            timezone_offset = int(timezone_offset_str)
        except ValueError:
            await callback.message.answer("❌ Invalid timezone value in your profile. Please re-register your timezone.")
            return
    tz = pytz.FixedOffset(timezone_offset * 60)

    if not reminders:
        await callback.message.answer("🗒 You don't have any reminders yet.")
        return

    await state.update_data(reminder_ids=[r['id'] for r in reminders])
    await state.update_data(full_reminders=reminders)

    response = "<b>📋 Your reminders:</b>\n\n"
    for i, r in enumerate(reminders, start=1):
        local_dt = r['reminder_time'].astimezone(tz)
        local_time_str = local_dt.strftime("%Y-%m-%d %H:%M")
        response += f"{i}. 📌 {r['title']} — {local_time_str}\n"

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
        telegram_id = message.from_user.id

        # Fetch user's timezone from DB
        async with async_session() as session:
            result = await session.execute(
                select(User.timezone).where(User.telegram_id == telegram_id)
            )
            timezone_offset_str = result.scalar()
            if timezone_offset_str is None:
                await message.answer("❌ Timezone not set. Please register your timezone with /register.")
                await state.clear()
                return
            try:
                timezone_offset = int(timezone_offset_str)
            except ValueError:
                await message.answer("❌ Invalid timezone value in your profile. Please re-register your timezone.")
                await state.clear()
                return

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

    # Fetch user's timezone from DB
    async with async_session() as session:
        result = await session.execute(
            select(User.timezone).where(User.telegram_id == telegram_id)
        )
        timezone_offset_str = result.scalar()
        if timezone_offset_str is None:
            await callback.message.answer("❌ Timezone not set. Please register your timezone with /register.")
            return
        try:
            timezone_offset = int(timezone_offset_str)
        except ValueError:
            await callback.message.answer("❌ Invalid timezone value in your profile. Please re-register your timezone.")
            return
    tz = pytz.FixedOffset(timezone_offset * 60)

    if not reminders:
        await callback.message.answer("🗒 You don't have any reminders yet.")
        return

    await state.update_data(reminder_ids=[r['id'] for r in reminders])

    response = "<b>📋 Your reminders:</b>\n\n"
    for i, r in enumerate(reminders, start=1):
        local_dt = r['reminder_time'].astimezone(tz)
        local_time_str = local_dt.strftime("%Y-%m-%d %H:%M")
        response += f"{i}. 📌 {r['title']} — {local_time_str}\n"

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

# Handler for command create, handler for a date of reminder
@router.message(user_remind.time_remind)
async def handler_create_date(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    reminder_message_id = data.get("reminder_message_id")
    name_remind = data.get('name_remind')
    telegram_id = message.from_user.id

    time_remind = message.text.strip()

    # Проверка формата
    try:
        dt_naive = datetime.strptime(time_remind, '%Y-%m-%d %H:%M')
    except ValueError:
        await message.answer("❌ Invalid time format. Please enter in format: <b>YYYY-MM-DD HH:MM</b>",
                             parse_mode="HTML")
        return

    # Получаем смещение пользователя
    async with async_session() as session:
        result = await session.execute(
            select(User.timezone).where(User.telegram_id == telegram_id)
        )
        timezone_offset_str = result.scalar()
        if timezone_offset_str is None:
            await message.answer("❌ Timezone not set. Please register your timezone with /register.")
            return
        try:
            timezone_offset = int(timezone_offset_str)
        except ValueError:
            await message.answer("❌ Invalid timezone value in your profile. Please re-register your timezone.")
            return

    # Локализуем время пользователя
    tz = pytz.FixedOffset(timezone_offset * 60)
    dt_local = tz.localize(dt_naive)

    # Проверка, что время не в прошлом (локальное время пользователя)
    now_local = datetime.now(tz)
    if dt_local < now_local:
        await message.answer("❌ The specified time has already passed. Please enter a future time.")
        return

    # Переводим в UTC
    dt_utc = dt_local.astimezone(pytz.UTC)

    await state.update_data(time_remind=dt_utc)

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

# Handler for command create, handler for a message of reminder
@router.message(user_remind.message_remind)
async def handler_create_message(message: Message, state: FSMContext, bot: Bot):
    telegram_id = message.from_user.id

    data = await state.get_data()
    reminder_message_id = data.get("reminder_message_id")

    data = await state.get_data()
    name_remind = data.get('name_remind')
    time_remind = data.get('time_remind')  # теперь это уже datetime в UTC

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
        reminder_time=time_remind,  # уже datetime в UTC
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


### new ###
@router.callback_query(F.data == "edit")
async def command_edit(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    telegram_id = callback.from_user.id
    reminders = await get_user_reminders(telegram_id)
    # Получаем таймзону пользователя
    async with async_session() as session:
        result = await session.execute(
            select(User.timezone).where(User.telegram_id == telegram_id)
        )
        timezone_offset_str = result.scalar()
        if timezone_offset_str is None:
            await callback.message.answer("❌ Timezone not set. Please register your timezone with /register.")
            return
        try:
            timezone_offset = int(timezone_offset_str)
        except ValueError:
            await callback.message.answer("❌ Invalid timezone value in your profile. Please re-register your timezone.")
            return
    tz = pytz.FixedOffset(timezone_offset * 60)
    if not reminders:
        await callback.message.answer("🗒 You don't have any reminders yet.")
        return
    await state.update_data(reminder_ids=[r['id'] for r in reminders])
    await state.update_data(full_reminders=reminders)
    response = "<b>📋 Your reminders:</b>\n\n"
    for i, r in enumerate(reminders, start=1):
        local_dt = r['reminder_time'].astimezone(tz)
        local_time_str = local_dt.strftime("%Y-%m-%d %H:%M")
        response += f"{i}. 📌 {r['title']} — {local_time_str}\n"
    await callback.message.answer(response, parse_mode="HTML")
    await callback.message.answer("Enter the number of the reminder you want to edit:")
    await state.set_state(user_remind.edit_index)

@router.message(user_remind.edit_index)
async def handler_edit_select(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    reminders = data.get("full_reminders", [])
    try:
        index = int(message.text.strip()) - 1
        if index < 0 or index >= len(reminders):
            raise ValueError
        reminder = reminders[index]
        await state.update_data(editing_reminder_id=reminder['id'])
        await state.update_data(editing_reminder_title=reminder['title'])
        await state.update_data(editing_reminder_time=reminder['reminder_time'])
        await state.update_data(editing_reminder_message=reminder['message'])
        # Получаем таймзону пользователя
        telegram_id = message.from_user.id
        async with async_session() as session:
            result = await session.execute(
                select(User.timezone).where(User.telegram_id == telegram_id)
            )
            timezone_offset_str = result.scalar()
            if timezone_offset_str is None:
                await message.answer("❌ Timezone not set. Please register your timezone with /register.")
                await state.clear()
                return
            try:
                timezone_offset = int(timezone_offset_str)
            except ValueError:
                await message.answer("❌ Invalid timezone value in your profile. Please re-register your timezone.")
                await state.clear()
                return
        tz = pytz.FixedOffset(timezone_offset * 60)
        local_dt = reminder['reminder_time'].astimezone(tz)
        local_time_str = local_dt.strftime("%Y-%m-%d %H:%M")
        # Отправляем шаблон с предзаполненными полями
        sent_msg = await message.answer(
            '<b>✏️ Edit reminder</b>\n\n'
            f'<b>✅ | 📝 Reminder name:</b>\n <b>{reminder["title"]}</b>\n'
            f'<b>✅ | ⏰ Time to receive reminder: </b>\n<b>{local_time_str}</b>\n'
            f'<b>✅ | 💬 Reminder message: </b>\n<b>{reminder["message"]}</b>\n\n'
            '<b># Enter a new name for the reminder (or send the same to keep it). #</b>',
            parse_mode=ParseMode.HTML
        )
        await state.update_data(reminder_message_id=sent_msg.message_id)
        await state.set_state(user_remind.edit_name)
    except (ValueError, IndexError):
        await message.answer("❌ Invalid number. Try again.")
        await state.clear()

@router.message(user_remind.edit_name)
async def handler_edit_name(message: Message, state: FSMContext, bot: Bot):
    name_remind = message.text
    if len(name_remind) > 20:
        await message.answer("❌ The reminder name must not exceed 20 characters. Please enter a shorter name.")
        return
    data = await state.get_data()
    reminder_message_id = data.get("reminder_message_id")
    await state.update_data(editing_reminder_title=name_remind)
    # Получаем текущее время и сообщение
    telegram_id = message.from_user.id
    # Получаем локальное время из state
    editing_reminder_time = data.get('editing_reminder_time')
    # Получаем таймзону пользователя
    async with async_session() as session:
        result = await session.execute(
            select(User.timezone).where(User.telegram_id == telegram_id)
        )
        timezone_offset_str = result.scalar()
        timezone_offset = int(timezone_offset_str)
    tz = pytz.FixedOffset(timezone_offset * 60)
    local_dt = editing_reminder_time.astimezone(tz)
    local_time_str = local_dt.strftime("%Y-%m-%d %H:%M")
    editing_reminder_message = data.get('editing_reminder_message')
    new_text = (
        '<b>✏️ Edit reminder</b>\n\n'
        f'<b>✅ | 📝 Reminder name:</b>\n <b>{name_remind}</b>\n'
        f'<b>✅ | ⏰ Time to receive reminder: </b>\n<b>{local_time_str}</b>\n'
        f'<b>✅ | 💬 Reminder message: </b>\n<b>{editing_reminder_message}</b>\n\n'
        '<b># Enter a new time for the reminder. Example: YYYY-MM-DD HH:MM #</b>'
    )
    try:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=reminder_message_id,
            text=new_text,
            parse_mode=ParseMode.HTML
        )
    except Exception:
        await message.answer("❗ Failed to update message.")
    await state.set_state(user_remind.edit_time)

@router.message(user_remind.edit_time)
async def handler_edit_time(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    reminder_message_id = data.get("reminder_message_id")
    name_remind = data.get('editing_reminder_title')
    telegram_id = message.from_user.id
    time_remind = message.text.strip()
    # Проверка формата
    try:
        dt_naive = datetime.strptime(time_remind, '%Y-%m-%d %H:%M')
    except ValueError:
        await message.answer("❌ Invalid time format. Please enter in format: <b>YYYY-MM-DD HH:MM</b>",
                             parse_mode="HTML")
        return
    # Получаем смещение пользователя
    async with async_session() as session:
        result = await session.execute(
            select(User.timezone).where(User.telegram_id == telegram_id)
        )
        timezone_offset_str = result.scalar()
        timezone_offset = int(timezone_offset_str)
    tz = pytz.FixedOffset(timezone_offset * 60)
    dt_local = tz.localize(dt_naive)
    now_local = datetime.now(tz)
    if dt_local < now_local:
        await message.answer("❌ The specified time has already passed. Please enter a future time.")
        return
    dt_utc = dt_local.astimezone(pytz.UTC)
    await state.update_data(editing_reminder_time=dt_utc)
    editing_reminder_message = data.get('editing_reminder_message')
    new_text = (
        '<b>✏️ Edit reminder</b>\n\n'
        f'<b>✅ | 📝 Reminder name:</b>\n <b>{name_remind}</b>\n'
        f'<b>✅ | ⏰ Time to receive reminder: </b>\n<b>{time_remind}</b>\n'
        f'<b>✅ | 💬 Reminder message: </b>\n<b>{editing_reminder_message}</b>\n\n'
        '<b># Enter a new message for the reminder. #</b>'
    )
    try:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=reminder_message_id,
            text=new_text,
            parse_mode=ParseMode.HTML
        )
    except Exception:
        await message.answer("❗ Failed to update message.")
    await state.set_state(user_remind.edit_message)

@router.message(user_remind.edit_message)
async def handler_edit_message(message: Message, state: FSMContext, bot: Bot):
    telegram_id = message.from_user.id
    data = await state.get_data()
    reminder_message_id = data.get("reminder_message_id")
    name_remind = data.get('editing_reminder_title')
    time_remind = data.get('editing_reminder_time')
    message_remind = message.text
    await state.update_data(editing_reminder_message=message_remind)
    new_text = (
        '<b>✏️ Edit reminder</b>\n\n'
        f'<b>✅ | 📝 Reminder name:</b>\n <b>{name_remind}</b>\n'
        f'<b>✅ | ⏰ Time to receive reminder: </b>\n<b>{time_remind}</b>\n'
        f'<b>✅ | 💬 Reminder message: </b>\n<b>{message_remind}</b>\n\n'
        '<b># Excellent, the reminder is updated. #</b>'
    )
    try:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=reminder_message_id,
            text=new_text,
            parse_mode=ParseMode.HTML
        )
    except Exception:
        await message.answer("❗ Failed to update message.")
    editing_reminder_id = data.get('editing_reminder_id')
    from database import update_reminder_by_id
    await update_reminder_by_id(
        reminder_id=editing_reminder_id,
        title=name_remind,
        reminder_time=time_remind,
        message=message_remind
    )
    await message.answer("✅ The reminder has been successfully updated.")
    await state.clear()




