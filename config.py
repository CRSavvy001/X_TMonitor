import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
RAILWAY_ENV = os.getenv("RAILWAY_ENVIRONMENT", "development")

# Check interval in seconds (5.5s for free tier)
CHECK_INTERVAL = 5.5

# API endpoint
TWITTER_API_BASE = "https://api.twitterapi.io/v1"
