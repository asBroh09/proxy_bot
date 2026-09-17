# config.py

# BotFather থেকে নেওয়া টোকেন
BOT_TOKEN = "7965662511:AAGxCU-xI9sJpfFD5YCBFSl043LEeK9Fb8I"

# শুধু এই ID গুলো কমান্ড দিতে পারবে (নিজের Telegram ID দিন)
# নিজের ID জানতে @userinfobot এ /start দিন
ADMIN_IDS = [
    8524951580,   # আপনার ID
    # 987654321, # আরও অ্যাডমিন লাগলে যোগ করুন
]

# ডিফল্ট সেটিংস
DEFAULT_TIMEOUT = 8          # সেকেন্ড
DEFAULT_TEST_URL = "https://google.com/"
MAX_WORKERS = 300            # একসাথে কতটা চেক হবে
SCRAPE_FILE = "scraped_proxies.txt"
OUTPUT_DIR = "outputs"
