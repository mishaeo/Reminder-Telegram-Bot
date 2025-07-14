import asyncio
import logging
import sys
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from handlers import router
from config import BOT_TOKEN
from database import init_db, delete_expired_reminders

# Получаем переменные окружения
APP_URL = os.getenv("APP_URL").rstrip("/")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

# Запуск задачи по отправке напоминаний
async def reminder_dispatcher():
    from database import get_all_reminders, delete_reminder_by_id
    from datetime import datetime
    while True:
        try:
            now = datetime.now().replace(second=0, microsecond=0)
            reminders = await get_all_reminders()

            for reminder in reminders:
                reminder_time = datetime.strptime(reminder['reminder_time'], '%Y-%m-%d %H:%M')

                if reminder_time <= now:
                    try:
                        await bot.send_message(
                            chat_id=reminder['telegram_id'],
                            text=f"🔔 Reminder: {reminder['title']}\n\n💬 {reminder['message']}"
                        )
                        await delete_reminder_by_id(reminder['id'])
                        print(f"[Dispatcher] Sent and deleted reminder: {reminder['title']}")
                    except Exception as e:
                        print(f"[Dispatcher] Failed to send reminder: {e}")

            await asyncio.sleep(30)  # Проверка каждые полминуты

        except Exception as e:
            print(f"[Dispatcher] Exception: {e}")
            await asyncio.sleep(30)

# Webhook и запуск aiohttp
async def on_startup(app):
    await init_db()
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(reminder_dispatcher())
    print(f"[Webhook] Установлен: {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    print("[Webhook] Удалён")

def create_app():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    return app

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    web.run_app(create_app(), host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
