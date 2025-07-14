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
from database import init_db
from tasks import reminder_loop  # ✅ импортируем из tasks

# Получаем переменные окружения
APP_URL = os.getenv("APP_URL", "").rstrip("/")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

# Webhook и запуск aiohttp
async def on_startup(app):
    await init_db()
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(reminder_loop(bot))  # ✅ запускаем фоновую задачу
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

