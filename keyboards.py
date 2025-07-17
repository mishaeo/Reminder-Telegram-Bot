from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

remind_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Create", callback_data="create"),
        InlineKeyboardButton(text="Delete", callback_data="delete"),
        InlineKeyboardButton(text="Show", callback_data="show"),
        InlineKeyboardButton(text="Edit", callback_data="edit")
    ]
])

def create_utc_times_keyboard():
    now_utc = datetime.utcnow()
    # Диапазон часовых поясов от -12 до +11 включительно
    offsets = list(range(-12, 12))

    buttons = []
    for offset in offsets:
        # Время для данного часового пояса
        local_time = now_utc + timedelta(hours=offset)
        # Форматируем время в ЧЧ:ММ
        time_str = local_time.strftime("%H:%M")
        # Формируем текст кнопки, например "UTC-12(08:34)"
        if offset >= 0:
            tz_text = f"UTC+{offset}({time_str})"
        else:
            tz_text = f"UTC{offset}({time_str})"
        callback_data = f"UTC{offset}"
        buttons.append(InlineKeyboardButton(text=tz_text, callback_data=callback_data))

    # Можно сделать по одной строке или разбить на несколько рядов — здесь все в одном ряду
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    return keyboard

utc_times_keyboard = create_utc_times_keyboard()
