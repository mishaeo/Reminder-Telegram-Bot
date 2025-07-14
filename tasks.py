import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
from database import get_all_reminders, delete_reminder_by_id


async def reminder_loop(bot: Bot):
    print("[Reminder loop] Started")

    while True:
        try:
            reminders = await get_all_reminders()
            now = datetime.now().replace(second=0, microsecond=0)
            print(f"[Reminder loop] Checking at {now}, found {len(reminders)} reminders")

            for reminder in reminders:
                try:
                    reminder_time = datetime.strptime(reminder['reminder_time'], '%Y-%m-%d %H:%M')

                    # Допуск ±1 минута (если бот "проснулся" чуть позже)
                    if reminder_time <= now <= reminder_time + timedelta(minutes=1):
                        message = f"🔔 Напоминание: <b>{reminder['title']}</b>\n\n{reminder['message'] or ''}"
                        await bot.send_message(chat_id=reminder['telegram_id'], text=message, parse_mode="HTML")
                        await delete_reminder_by_id(reminder['id'])
                        print(f"[Reminder loop] Sent reminder ID {reminder['id']} to {reminder['telegram_id']}")

                except Exception as reminder_error:
                    print(f"[Reminder loop] Error with reminder ID {reminder.get('id')}: {reminder_error}")

        except Exception as e:
            print(f"[Reminder loop ERROR] {e}")

        await asyncio.sleep(60)

