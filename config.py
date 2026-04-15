import os

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

ADMIN_IDS_FILE = "data/admins.json"
USERS_FILE = "data/users.json"
BANNED_FILE = "data/banned.json"
STATS_FILE = "data/stats.json"
SETTINGS_FILE = "data/settings.json"
LOGS_FILE = "data/logs.txt"

DOWNLOADS_DIR = "downloads"

VERSION = "1.0.0"
BOT_NAME = "TikTok Downloader Bot"
