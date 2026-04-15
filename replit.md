# TikTok Downloader Telegram Bot

## Overview
A full-featured Telegram bot that downloads TikTok videos without watermark, with a complete admin panel.

## Architecture
- **Language**: Python 3.11
- **Framework**: python-telegram-bot 20.7
- **Downloader**: yt-dlp
- **Storage**: JSON files (no external DB required)

## Files
- `main.py` — Bot entry point, all user-facing handlers
- `config.py` — Constants and config
- `database.py` — JSON-based data storage (users, bans, admins, stats, settings, logs)
- `handlers/downloader.py` — TikTok download logic using yt-dlp
- `handlers/admin.py` — Full admin panel with inline keyboard

## Data Storage
All data is stored in the `data/` directory as JSON files:
- `data/users.json` — Registered users
- `data/admins.json` — Admin user IDs
- `data/banned.json` — Banned users
- `data/stats.json` — Download stats
- `data/settings.json` — Bot settings
- `data/logs.txt` — Activity logs

## Admin Panel Features (15 total)
1. Bot Statistics (users, downloads, bans)
2. Users List (first 20 shown)
3. Broadcast Message to all users
4. Ban User (with reason)
5. Unban User
6. Banned Users List
7. Add Admin
8. Remove Admin
9. Admin List
10. Bot Settings panel
11. Toggle Maintenance Mode
12. Toggle Force Join (channel subscription wall)
13. Message specific user
14. Export users as CSV
15. View/Clear Logs + Download Stats

## Bot Features
- TikTok video download (no watermark) via yt-dlp
- User stats (/stats)
- Force join channel gate
- Maintenance mode
- Inline buttons throughout

## Environment Variables
- `TELEGRAM_BOT_TOKEN` — Required, from @BotFather

## Running
```
python3 main.py
```
