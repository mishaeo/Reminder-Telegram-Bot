from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


create_reminder_button = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Create a reminder")]
    ],
    resize_keyboard=True
)
