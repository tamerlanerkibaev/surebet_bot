import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

DEFAULT_BANK = 100000.0
DEFAULT_ROUND_STEP = 500
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_BANK = float(os.getenv("DEFAULT_BANK", 100000.0))
DEFAULT_ROUND_STEP = int(os.getenv("DEFAULT_ROUND_STEP", 500))

if not BOT_TOKEN:
    raise ValueError("Укажи BOT_TOKEN в файле .env!")
