# bot.py
import asyncio
import os
import random
import time
from collections import defaultdict
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import (
    BOT_TOKEN,
    ADMIN_IDS,
    DEFAULT_TIMEOUT,
    DEFAULT_TEST_URL,
    MAX_WORKERS,
    MAX_CHECK,
    OUTPUT_DIR,
)
from scraper import scrape_all
from checker import check_bulk

# ---------- State ----------
running_jobs = {}   # user_id -> dict


def is_admin(uid):
    return uid in ADMIN_IDS


async def deny(update: Update):
    await update.message.reply_text(
        "🚫 আপনি Admin নন। এই বট শুধু Admin ব্যবহার করতে পারবে।"
    )


# ==================== /start ====================
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await deny(update)

    text = (
        "🤖 *Proxy Scraper & Checker Bot*\n\n"
        "📋 *কমান্ড সমূহ:*\n"
        "• `/check <method>` — প্রক্সি সংগ্রহ + চেক\n"
        "   method: `http`, `socks4`, `socks5`, `all`\n"
        "• `/check http 10` — HTTP, টাইমআউট ১০s\n"
        "• `/status` — চলমান কাজের অবস্থা\n"
        "• `/stop` — চলমান কাজ বন্ধ\n"
        "• `/help` — সাহায্য\n\n"
        "📂 শেষে Live প্রক্সি TXT ফাইলে পাঠানো হবে।"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await deny(update)
    await cmd_start(update, ctx)


# ==================== /status ====================
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await deny(update)

    if not running_jobs:
        return await update.message.reply_text("✅ কোনো কাজ চলছে না।")

    lines = ["📊 *চলমান কাজ:*\n"]
    for uid, job in running_jobs.items():
        lines.append(
            f"👤 `{uid}`\n"
            f"   method: `{job.get('method')}`\n"
            f"   done: `{job.get('done', 0)}/{job.get('total', 0)}`\n"
            f"   live: `{job.get('live', 0)}`\n"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ==================== /stop ====================
async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await deny(update)

    uid = update.effective_user.id
    if uid in running_jobs:
        running_jobs[uid]["stop"] = True
        await update.message.reply_text("🛑 বন্ধ করার অনুরোধ পাঠানো হয়েছে...")
    else:
        await update.message.reply_text("❌ আপনার কোনো কাজ চলছে না।")


# ==================== /check ====================
async def cmd_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        return await deny(update)

    if uid in running_jobs and running_jobs[uid].get("running"):
        return await update.message.reply_text(
            "⚠️ আপনার একটা কাজ ইতিমধ্যেই চলছে। `/stop` দিয়ে বন্ধ করুন।",
            parse_mode="Markdown",
        )

    args = ctx.args
    method = args[0].lower() if args else "http"
    if method not in ("http", "socks4", "socks5", "all"):
        return await update.message.reply_text(
            "❌ ভুল method। ব্যবহার করুন: `http`, `socks4`, `socks5`, `all`",
            parse_mode="Markdown",
        )

    timeout = DEFAULT_TIMEOUT
    if len(args) >= 2 and args[1].isdigit():
        timeout = max(3, min(int(args[1]), 30))  # ৩-৩০s এর মধ্যে

    running_jobs[uid] = {
        "running": True,
        "stop": False,
        "method": method,
        "done": 0,
        "total": 0,
        "live": 0,
    }

    msg = await update.message.reply_text(
        f"🔍 *কাজ শুরু হয়েছে...*\n"
        f"Method: `{method}`\nTimeout: `{timeout}s`\n\n"
        f"⏳ প্রক্সি সংগ্রহ করা হচ্ছে...",
        parse_mode="Markdown",
    )

    try:
        await run_job(update, ctx, msg, uid, method, timeout)
    except Exception as e:
        print(f"[run_job ERROR] {e}")
        try:
            await msg.edit_text(f"❌ Error: `{e}`", parse_mode="Markdown")
        except Exception:
            pass
    finally:
        running_jobs.pop(uid, None)


# ==================== CORE JOB ====================
async def run_job(update, ctx, msg, uid, method, timeout):
    t0 = time.time()

    # ---------- Scrape ----------
    proxies = await scrape_all(method)

    if running_jobs.get(uid, {}).get("stop"):
        return await msg.edit_text("🛑 বাতিল করা হয়েছে।")

    if not proxies:
        return await msg.edit_text("❌ কোনো প্রক্সি সংগ্রহ করা যায়নি।")

    # shuffle + limit (Railway RAM বাঁচানোর জন্য)
    random.shuffle(proxies)
    total_scraped = len(proxies)
    if len(proxies) > MAX_CHECK:
        proxies = proxies[:MAX_CHECK]

    running_jobs[uid]["total"] = len(proxies)

    await msg.edit_text(
        f"✅ সংগ্রহ হয়েছে: `{total_scraped}` টি প্রক্সি\n"
        f"🎯 চেক করা হবে: `{len(proxies)}` টি\n"
        f"⏳ চেক করা হচ্ছে (timeout {timeout}s)...\n"
        f"Method: `{method}`",
        parse_mode="Markdown",
    )

    # ---------- Check ----------
    loop = asyncio.get_running_loop()
    last_edit = [0.0]

    def progress(done, total, live):
        """থ্রেড থেকে কল হয় — তাই run_coroutine_threadsafe ব্যবহার"""
        running_jobs[uid]["done"] = done
        running_jobs[uid]["live"] = live

        if time.time() - last_edit[0] < 2:
            return
        last_edit[0] = time.time()

        text = (
            f"🔍 *চেক চলছে...*\n"
            f"✅ Live: `{live}`\n"
            f"📊 Progress: `{done}/{total}`\n"
            f"Method: `{method}` | Timeout: `{timeout}s`"
        )
        asyncio.run_coroutine_threadsafe(_safe_edit(msg, text), loop)

    check_method = "http" if method == "all" else method

    live = await loop.run_in_executor(
        None,
        lambda: check_bulk(
            proxies,
            check_method,
            DEFAULT_TEST_URL,
            timeout,
            MAX_WORKERS,
            progress,
        ),
    )

    if running_jobs.get(uid, {}).get("stop"):
        return await msg.edit_text(
            f"🛑 বাতিল করা হয়েছে। Live পাওয়া গেছে: `{len(live)}`",
            parse_mode="Markdown",
        )

    # ---------- No live ----------
    if not live:
        return await msg.edit_text("😔 কোনো Live প্রক্সি পাওয়া যায়নি।")

    # ---------- Build TXT ----------
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{OUTPUT_DIR}/live_{method}_{ts}.txt"

    by_country = defaultdict(list)
    for item in live:
        by_country[item["country"]].append(item)

    country_sorted = sorted(by_country.items(), key=lambda x: -len(x[1]))

    with open(filename, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write(f"  LIVE PROXY REPORT — Method: {method.upper()}\n")
        f.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"  Total Live: {len(live)}\n")
        f.write(f"  Countries: {len(by_country)}\n")
        f.write("=" * 60 + "\n\n")

        # Summary
        f.write("📊 SUMMARY BY COUNTRY\n")
        f.write("-" * 60 + "\n")
        for country, items in country_sorted:
            avg_ping = sum(i["ping"] for i in items) // len(items)
            f.write(
                f"  {country:<30} : {len(items):>5} proxies (avg {avg_ping}ms)\n"
            )
        f.write("\n" + "=" * 60 + "\n\n")

        # Details
        f.write("📋 DETAILS (grouped by country)\n")
        f.write("=" * 60 + "\n\n")
        for country, items in country_sorted:
            f.write(f"🌍 {country}  ({len(items)} proxies)\n")
            f.write("-" * 60 + "\n")
            for i in sorted(items, key=lambda x: x["ping"]):
                f.write(
                    f"  {i['proxy']:<25} | method: {i['method']:<7} | ping: {i['ping']}ms\n"
                )
            f.write("\n")

        # Plain list
        f.write("=" * 60 + "\n")
        f.write("📄 PLAIN LIST\n")
        f.write("=" * 60 + "\n")
        for i in live:
            f.write(f"{i['proxy']}\n")

    # ---------- Send ----------
    top_countries = "\n".join(
        f"  • {c}: `{len(items)}`" for c, items in country_sorted[:10]
    )
    caption = (
        f"✅ *চেক সম্পন্ন!*\n\n"
        f"🌐 Method: `{method}`\n"
        f"📊 মোট Live: `{len(live)}`\n"
        f"🌍 দেশ: `{len(by_country)}`\n"
        f"⏱ সময়: `{int(time.time() - t0)}s`\n\n"
        f"*Top Countries:*\n{top_countries}"
    )

    await msg.edit_text(caption, parse_mode="Markdown")
    await update.message.reply_document(
        document=open(filename, "rb"),
        filename=os.path.basename(filename),
        caption=f"📁 Live proxies ({len(live)})",
    )


async def _safe_edit(msg, text):
    try:
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception:
        pass


# ==================== ERROR ====================
async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    print(f"[BOT ERROR] {ctx.error}")


# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("stop", cmd_stop))

    app.add_error_handler(on_error)

    print("🤖 Bot চালু হচ্ছে...")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
