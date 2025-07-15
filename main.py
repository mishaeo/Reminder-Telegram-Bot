import asyncio
import logging
import sys
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from datetime import datetime, timezone

from handlers import router
from config import BOT_TOKEN
from database import init_db, get_all_reminders_all, delete_reminder_by_id



async def reminder_cleaner(bot: Bot):
    while True:
        reminders = await get_all_reminders_all()  # нужна отдельная версия, возвращающая все напоминания
        now = datetime.now(timezone.utc)  # лучше сравнивать с UTC

        for reminder in reminders:
            reminder_time = reminder.reminder_time

            # Приводим reminder_time к UTC, если он без timezone
            if reminder_time.tzinfo is None:
                reminder_time = reminder_time.replace(tzinfo=timezone.utc)

            if reminder_time <= now:
                text = f"🔔 Напоминание: {reminder.title}\n🕒 {reminder_time.strftime('%Y-%m-%d %H:%M')}\n📩 {reminder.message or 'Без сообщения'}"
                try:
                    await bot.send_message(int(reminder.telegram_id), text)
                    await delete_reminder_by_id(reminder.id)
                    print(f"[Cleaner] Отправлено и удалено напоминание ID {reminder.id}")
                except Exception as e:
                    print(f"[Cleaner] ❌ Ошибка при отправке напоминания ID {reminder.id}: {e}")

        await asyncio.sleep(30)



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

    asyncio.create_task(reminder_cleaner(bot))

    await bot.set_webhook(WEBHOOK_URL)

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

