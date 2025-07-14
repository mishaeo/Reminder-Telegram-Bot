import asyncio
from datetime import datetime
from aiogram import Bot
from database import get_all_reminders, delete_reminder_by_id


async def reminder_loop(bot: Bot):
    while True:
        try:
            reminders = await get_all_reminders()
            now = datetime.utcnow().replace(second=0, microsecond=0)

            for reminder in reminders:
                reminder_time = datetime.strptime(reminder['reminder_time'], '%Y-%m-%d %H:%M')
                if reminder_time <= now:
                    message = f"🔔 Напоминание: <b>{reminder['title']}</b>\n\n{reminder['message'] or ''}"
                    await bot.send_message(chat_id=reminder['telegram_id'], text=message, parse_mode="HTML")
                    await delete_reminder_by_id(reminder['id'])

        except Exception as e:
            print(f"[reminder_loop ERROR] {e}")

        await asyncio.sleep(60)  # Проверять каждую минуту
