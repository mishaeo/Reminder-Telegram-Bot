import aiosqlite

DB_NAME = "database.db"

async def create_or_update_user(telegram_id: int, time: str, date: str, message: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO data (telegram_id, time, date, message)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                time=excluded.time,
                date=excluded.date,
                message=excluded.message
        """, (telegram_id, time, date, message))
        await db.commit()
