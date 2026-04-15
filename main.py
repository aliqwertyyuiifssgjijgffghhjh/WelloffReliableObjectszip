import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

import database as db
from config import BOT_TOKEN, BOT_NAME, VERSION
from handlers.admin import admin_panel, handle_admin_callback, handle_admin_text
from handlers.downloader import download_tiktok, cleanup_file, extract_tiktok_url

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def find_tiktok_url(text: str) -> str | None:
    """Return extracted TikTok URL from any message text, or None."""
    return extract_tiktok_url(text)


def main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📥 How to Download", callback_data="how_to"),
            InlineKeyboardButton("ℹ️ About", callback_data="about"),
        ],
        [InlineKeyboardButton("📊 My Stats", callback_data="my_stats")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ─── /start ───────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or "", user.full_name or "")
    db.update_user_info(user.id, user.username or "", user.full_name or "")
    db.write_log(f"User {user.id} ({user.full_name}) started the bot")

    # Set first user as admin automatically
    db.set_first_admin(user.id)

    settings = db.get_settings()

    # Maintenance check (skip for admins)
    if settings["maintenance"] and not db.is_admin(user.id):
        await update.message.reply_text("🛠️ Bot is under maintenance. Please try again later.")
        return

    # Force join check
    if settings["force_join"] and settings["force_join_channel"]:
        channel = settings["force_join_channel"]
        try:
            member = await context.bot.get_chat_member(channel, user.id)
            if member.status in ["left", "kicked"]:
                keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{channel.lstrip('@')}")]]
                keyboard.append([InlineKeyboardButton("✅ I Joined", callback_data="check_join")])
                await update.message.reply_text(
                    f"⚠️ You must join {channel} to use this bot.",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                return
        except Exception:
            pass

    welcome = settings.get("welcome_message", "Welcome! Send me a TikTok link to download it without watermark.")
    await update.message.reply_text(
        f"👋 *Hello {user.first_name}!*\n\n{welcome}\n\n"
        f"Just paste any TikTok link and I'll download it *without watermark* instantly! 🚀",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard(),
    )


# ─── /help ────────────────────────────────────────────────────────────────────

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *How to use this bot:*\n\n"
        "1. Copy a TikTok video link\n"
        "2. Paste it here in the chat\n"
        "3. The bot will download and send the video *without watermark* ✨\n\n"
        "*Supported links:*\n"
        "• `https://www.tiktok.com/@user/video/...`\n"
        "• `https://vm.tiktok.com/...`\n"
        "• `https://vt.tiktok.com/...`\n\n"
        "*Commands:*\n"
        "/start — Start the bot\n"
        "/help — Show this help\n"
        "/stats — Your download stats\n"
        "/admin — Admin panel (admins only)\n"
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="home")]]),
    )


# ─── /stats ───────────────────────────────────────────────────────────────────

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id)
    if not u:
        await update.message.reply_text("No stats yet. Send a TikTok link to get started!")
        return
    downloads = u.get("downloads", 0)
    joined = u.get("joined", "—")[:10]
    text = (
        f"📊 *Your Statistics*\n\n"
        f"👤 Name: {user.full_name}\n"
        f"📥 Downloads: `{downloads}`\n"
        f"📅 Joined: `{joined}`\n"
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="home")]]),
    )


# ─── MESSAGE HANDLER ──────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text or ""

    db.add_user(user.id, user.username or "", user.full_name or "")
    db.update_user_info(user.id, user.username or "", user.full_name or "")

    if db.is_banned(user.id):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    settings = db.get_settings()
    if settings["maintenance"] and not db.is_admin(user.id):
        await update.message.reply_text("🛠️ Bot is under maintenance. Please try again later.")
        return

    # Handle admin text inputs
    if await handle_admin_text(update, context):
        return

    # Extract TikTok URL from the message (handles share text, short links, full links)
    tiktok_url = find_tiktok_url(text)
    if tiktok_url:
        await process_download(update, context, tiktok_url)
    else:
        await update.message.reply_text(
            "❓ Please send a valid TikTok link.\n\nExample:\n`https://vm.tiktok.com/xxxxx`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard(),
        )


async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    user = update.effective_user
    msg = await update.message.reply_text("⏳ Downloading your video, please wait...")

    db.write_log(f"User {user.id} requested download: {url}")

    result = await download_tiktok(url)

    if not result["success"]:
        error = result.get("error", "Unknown error")
        db.write_log(f"Download failed for {user.id}: {error}")
        await msg.edit_text(
            f"❌ *Download failed!*\n\n`{error[:200]}`\n\n"
            "Please make sure the link is valid and the video is public.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Try Again", callback_data="how_to")]]),
        )
        return

    file_path = result["path"]
    title = result.get("title", "TikTok Video")[:50]
    author = result.get("author", "Unknown")
    duration = result.get("duration", 0)
    views = result.get("views", 0)

    caption = (
        f"✅ *Downloaded Successfully!*\n\n"
        f"🎵 *{title}*\n"
        f"👤 Author: {author}\n"
        f"⏱️ Duration: {duration}s\n"
        f"👁️ Views: {views:,}\n\n"
        f"_No watermark_ 🚫💧"
    )

    try:
        await msg.edit_text("📤 Uploading video...")
        with open(file_path, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Download Another", callback_data="how_to")],
                    [InlineKeyboardButton("📊 My Stats", callback_data="my_stats")],
                ]),
            )
        await msg.delete()
        db.increment_downloads(user.id)
        db.write_log(f"Download success for {user.id}: {title}")
    except Exception as e:
        await msg.edit_text(f"❌ Failed to send video: {str(e)[:200]}")
        db.write_log(f"Upload failed for {user.id}: {str(e)}")
    finally:
        cleanup_file(file_path)


# ─── CALLBACKS ────────────────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data.startswith("admin_") or data.startswith("toggle_") or data.startswith("set_"):
        await handle_admin_callback(update, context)
        return

    if data == "home":
        settings = db.get_settings()
        welcome = settings.get("welcome_message", "Send me a TikTok link to download it without watermark.")
        await query.edit_message_text(
            f"👋 *Hello {user.first_name}!*\n\n{welcome}\n\n"
            "Just paste any TikTok link and I'll download it *without watermark* instantly! 🚀",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard(),
        )

    elif data == "how_to":
        await query.edit_message_text(
            "📖 *How to download:*\n\n"
            "1️⃣ Open TikTok app\n"
            "2️⃣ Find the video you want\n"
            "3️⃣ Tap *Share* → *Copy Link*\n"
            "4️⃣ Paste the link here\n"
            "5️⃣ Wait a few seconds ✨\n\n"
            "*Supported formats:*\n"
            "• TikTok full links\n"
            "• TikTok short links (vm.tiktok.com)\n",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="home")]]),
        )

    elif data == "about":
        await query.edit_message_text(
            f"ℹ️ *About {BOT_NAME}*\n\n"
            f"🤖 Version: `{VERSION}`\n"
            f"🎯 Purpose: Download TikTok videos without watermark\n"
            f"⚡ Fast, free, and easy to use!\n\n"
            f"_Just send any TikTok link and get your video!_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="home")]]),
        )

    elif data == "my_stats":
        u = db.get_user(user.id)
        if not u:
            await query.edit_message_text(
                "No stats yet. Send a TikTok link to get started!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="home")]]),
            )
            return
        downloads = u.get("downloads", 0)
        joined = u.get("joined", "—")[:10]
        await query.edit_message_text(
            f"📊 *Your Statistics*\n\n"
            f"👤 Name: {user.full_name}\n"
            f"📥 Downloads: `{downloads}`\n"
            f"📅 Joined: `{joined}`\n",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="home")]]),
        )

    elif data == "check_join":
        settings = db.get_settings()
        channel = settings.get("force_join_channel", "")
        if not channel:
            await query.edit_message_text("✅ You're good to go! Send /start")
            return
        try:
            member = await context.bot.get_chat_member(channel, user.id)
            if member.status not in ["left", "kicked"]:
                await query.edit_message_text(
                    "✅ *Verified!* You can now use the bot.\n\nSend any TikTok link!",
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await query.answer("⚠️ Please join the channel first!", show_alert=True)
        except Exception:
            await query.edit_message_text("✅ Access granted! Send any TikTok link.")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info(f"🤖 {BOT_NAME} v{VERSION} is starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
