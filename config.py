from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env

TELEGRAM_BOT_API_KEY= os.getenv('TELEGRAM_BOT_API_KEY')
ADMIN_ID= os.getenv('ADMIN_ID')
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"