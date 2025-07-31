from datetime import datetime, timedelta, timezone
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

remind_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Create➕", callback_data="create"),
        InlineKeyboardButton(text="Delete🗑️", callback_data="delete")
    ],
    [
        InlineKeyboardButton(text="Show👁️", callback_data="show"),
        InlineKeyboardButton(text="Edit✏️", callback_data="edit")
    ]
])

back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_list")
    ]
])

def create_utc_times_keyboard():
    now_utc = datetime.now(timezone.utc)  # aware datetime
    offsets = list(range(-12, 13))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    row = []

    for i, offset in enumerate(offsets):
        offset_tz = timezone(timedelta(hours=offset))
        local_time = now_utc.astimezone(offset_tz)
        time_str = local_time.strftime("%H:%M")
        sign = f"+{offset}" if offset >= 0 else f"{offset}"
        tz_text = f"UTC{sign}({time_str})"
        button = InlineKeyboardButton(text=tz_text, callback_data=sign)
        row.append(button)
        if len(row) == 3:
            keyboard.inline_keyboard.append(row)
            row = []

    if row:
        keyboard.inline_keyboard.append(row)
    return keyboard

utc_times_keyboard = create_utc_times_keyboard()