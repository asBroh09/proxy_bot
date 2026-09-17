# config.py

# BotFather থেকে নেওয়া টোকেন
BOT_TOKEN = "7965662511:AAGxCU-xI9sJpfFD5YCBFSl043LEeK9Fb8I"

# শুধু এই ID গুলো কমান্ড দিতে পারবে
ADMIN_IDS = [
    8524951580,   # আপনার Telegram ID দিন
]

# ডিফল্ট সেটিংস
DEFAULT_TIMEOUT = 8
DEFAULT_TEST_URL = "https://google.com/"

# ⬇️ এই দুইটা লাইন ছিল না — এটাই error এর কারণ
MAX_WORKERS = 50         # একসাথে কতটা চেক হবে
MAX_CHECK = 3000         # সর্বোচ্চ কতটা প্রক্সি চেক করবে

OUTPUT_DIR = "outputs"
