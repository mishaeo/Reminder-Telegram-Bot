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

from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def create_utc_times_keyboard():
    now_utc = datetime.utcnow()
    offsets = list(range(-12, 12 + 1))  # от -12 до +11

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    row = []

    for i, offset in enumerate(offsets):
        local_time = now_utc + timedelta(hours=offset)
        time_str = local_time.strftime("%H:%M")

        if offset >= 0:
            tz_text = f"UTC+{offset}({time_str})"
        else:
            tz_text = f"UTC{offset}({time_str})"

        button = InlineKeyboardButton(text=tz_text, callback_data=f"UTC{offset}")
        row.append(button)

        # Каждые 3 кнопки — новая строка
        if len(row) == 3:
            keyboard.inline_keyboard.append(row)
            row = []

    # Добавим последнюю строку, если остались кнопки
    if row:
        keyboard.inline_keyboard.append(row)

    return keyboard


utc_times_keyboard = create_utc_times_keyboard()
