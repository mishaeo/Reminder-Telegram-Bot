import aiosqlite
from datetime import datetime
from typing import List, Dict, Any

DB_NAME = "database.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT NOT NULL,
            title TEXT NOT NULL,
            reminder_time DATETIME NOT NULL,
            message TEXT
        )
        """)
        await db.commit()


async def create_user_remind(telegram_id: int, title: str, reminder_time: datetime, message: str):
    if isinstance(reminder_time, str):
        reminder_time = datetime.strptime(reminder_time, "%Y-%m-%d %H:%M")

    formatted_time = reminder_time.replace(second=0).strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO reminders (telegram_id, title, reminder_time, message)
            VALUES (?, ?, ?, ?)
        """, (telegram_id, title, formatted_time, message))
        await db.commit()

async def delete_expired_reminders():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            DELETE FROM reminders WHERE reminder_time <= datetime('now', 'localtime')
        """)
        await db.commit()
        print(f"[Cleaner] Deleted {cursor.rowcount} expired reminders")

async def get_user_reminders(telegram_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT id, title, reminder_time, message
            FROM reminders
            WHERE telegram_id = ?
            ORDER BY reminder_time ASC
        """, (telegram_id,))
        rows = await cursor.fetchall()

    reminders = []
    for row in rows:
        reminders.append({
            "id": row[0],
            "title": row[1],
            "reminder_time": row[2],
            "message": row[3]
        })

    return reminders


