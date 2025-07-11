import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from handlers import router
from config import BOT_TOKEN
from database import init_db, delete_expired_reminders

# Функция удаления просроченных сообщений каждую минуту
async def reminder_cleaner():
    while True:
        try:
            print("[Cleaner] Running delete_expired_reminders()...")
            await delete_expired_reminders()
            print("[Cleaner] Waiting 60 seconds...")
            await asyncio.sleep(60)
        except Exception as e:
            print(f"[Cleaner] Exception occurred: {e}")

# Главная асинхронная функция
async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    asyncio.create_task(reminder_cleaner())

    await dp.start_polling(bot)

# Точка входа при запуске скрипта
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info('Bot is off')