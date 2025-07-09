import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from handlers import router 
from config import BOT_TOKEN

# Главная асинхронная функция
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

# Точка входа при запуске скрипта
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info('Bot is off')