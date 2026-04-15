import json
import os
from datetime import datetime
from config import ADMIN_IDS_FILE, USERS_FILE, BANNED_FILE, STATS_FILE, SETTINGS_FILE, LOGS_FILE

os.makedirs("data", exist_ok=True)
os.makedirs("downloads", exist_ok=True)


def _read(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def _write(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ─── USERS ────────────────────────────────────────────────────────────────────

def add_user(user_id: int, username: str = "", full_name: str = ""):
    users = _read(USERS_FILE, {})
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "id": user_id,
            "username": username,
            "full_name": full_name,
            "joined": datetime.now().isoformat(),
            "downloads": 0,
        }
        _write(USERS_FILE, users)


def get_all_users() -> dict:
    return _read(USERS_FILE, {})


def get_user(user_id: int) -> dict:
    users = _read(USERS_FILE, {})
    return users.get(str(user_id), {})


def user_count() -> int:
    return len(_read(USERS_FILE, {}))


def increment_downloads(user_id: int):
    users = _read(USERS_FILE, {})
    uid = str(user_id)
    if uid in users:
        users[uid]["downloads"] = users[uid].get("downloads", 0) + 1
        _write(USERS_FILE, users)
    bump_stat("total_downloads")


def update_user_info(user_id: int, username: str, full_name: str):
    users = _read(USERS_FILE, {})
    uid = str(user_id)
    if uid in users:
        users[uid]["username"] = username
        users[uid]["full_name"] = full_name
        _write(USERS_FILE, users)


# ─── BANS ─────────────────────────────────────────────────────────────────────

def ban_user(user_id: int, reason: str = ""):
    banned = _read(BANNED_FILE, {})
    banned[str(user_id)] = {"reason": reason, "date": datetime.now().isoformat()}
    _write(BANNED_FILE, banned)


def unban_user(user_id: int):
    banned = _read(BANNED_FILE, {})
    banned.pop(str(user_id), None)
    _write(BANNED_FILE, banned)


def is_banned(user_id: int) -> bool:
    banned = _read(BANNED_FILE, {})
    return str(user_id) in banned


def get_banned() -> dict:
    return _read(BANNED_FILE, {})


# ─── ADMINS ───────────────────────────────────────────────────────────────────

def get_admins() -> list:
    return _read(ADMIN_IDS_FILE, [])


def add_admin(user_id: int):
    admins = get_admins()
    if user_id not in admins:
        admins.append(user_id)
        _write(ADMIN_IDS_FILE, admins)


def remove_admin(user_id: int):
    admins = get_admins()
    if user_id in admins:
        admins.remove(user_id)
        _write(ADMIN_IDS_FILE, admins)


def is_admin(user_id: int) -> bool:
    return user_id in get_admins()


def set_first_admin(user_id: int):
    if not get_admins():
        _write(ADMIN_IDS_FILE, [user_id])


# ─── STATS ────────────────────────────────────────────────────────────────────

def bump_stat(key: str):
    stats = _read(STATS_FILE, {})
    stats[key] = stats.get(key, 0) + 1
    _write(STATS_FILE, stats)


def get_stats() -> dict:
    return _read(STATS_FILE, {})


# ─── SETTINGS ─────────────────────────────────────────────────────────────────

def get_settings() -> dict:
    defaults = {
        "maintenance": False,
        "force_join": False,
        "force_join_channel": "",
        "welcome_message": "Welcome! Send me a TikTok link to download it without watermark.",
        "max_downloads_per_user": 0,
    }
    saved = _read(SETTINGS_FILE, {})
    defaults.update(saved)
    return defaults


def update_setting(key: str, value):
    settings = get_settings()
    settings[key] = value
    _write(SETTINGS_FILE, settings)


# ─── LOGS ─────────────────────────────────────────────────────────────────────

def write_log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"
    with open(LOGS_FILE, "a") as f:
        f.write(line)


def read_logs(last_n: int = 30) -> str:
    if not os.path.exists(LOGS_FILE):
        return "No logs yet."
    with open(LOGS_FILE, "r") as f:
        lines = f.readlines()
    return "".join(lines[-last_n:]) or "No logs yet."


def clear_logs():
    with open(LOGS_FILE, "w") as f:
        f.write("")
