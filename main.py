import asyncio

from aiogram import Dispatcher
from handlers import router, scheduler
from bot_instance import bot

async def main():
    dp = Dispatcher()
    dp.include_router(router)

    scheduler.start()

    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Bot is off')