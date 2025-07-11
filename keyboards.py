from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

remind_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Create", callback_data="create"),
        InlineKeyboardButton(text="Delete", callback_data="delete"),
        InlineKeyboardButton(text="Show", callback_data="show"),
        InlineKeyboardButton(text="Edit", callback_data="edit")
    ]
])