import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
BOT_DATA_SPREADSHEET_ID = os.getenv("BOT_DATA_SPREADSHEET_ID")
