# config.py

# BotFather থেকে নেওয়া টোকেন
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# শুধু এই ID গুলো কমান্ড দিতে পারবে (নিজের Telegram ID দিন)
# নিজের ID জানতে @userinfobot এ /start দিন
ADMIN_IDS = [
    123456789,   # আপনার ID
    # 987654321, # আরও অ্যাডমিন লাগলে যোগ করুন
]

# ডিফল্ট সেটিংস
DEFAULT_TIMEOUT = 8          # সেকেন্ড
DEFAULT_TEST_URL = "https://google.com/"
MAX_WORKERS = 300            # একসাথে কতটা চেক হবে
SCRAPE_FILE = "scraped_proxies.txt"
OUTPUT_DIR = "outputs"
