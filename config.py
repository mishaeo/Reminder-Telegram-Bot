from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found!")

if not APP_URL:
    raise ValueError("APP_URL not found!")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found!")