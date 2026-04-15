from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import database as db
import os


def admin_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
            InlineKeyboardButton("👥 Users", callback_data="admin_users"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("🔨 Ban User", callback_data="admin_ban"),
        ],
        [
            InlineKeyboardButton("✅ Unban User", callback_data="admin_unban"),
            InlineKeyboardButton("🚫 Banned List", callback_data="admin_banned_list"),
        ],
        [
            InlineKeyboardButton("👑 Add Admin", callback_data="admin_add_admin"),
            InlineKeyboardButton("❌ Remove Admin", callback_data="admin_remove_admin"),
        ],
        [
            InlineKeyboardButton("📋 Admin List", callback_data="admin_admin_list"),
            InlineKeyboardButton("🔧 Settings", callback_data="admin_settings"),
        ],
        [
            InlineKeyboardButton("🛠️ Maintenance", callback_data="admin_maintenance"),
            InlineKeyboardButton("📨 Message User", callback_data="admin_msg_user"),
        ],
        [
            InlineKeyboardButton("📁 Export Users", callback_data="admin_export"),
            InlineKeyboardButton("📜 View Logs", callback_data="admin_logs"),
        ],
        [
            InlineKeyboardButton("🗑️ Clear Logs", callback_data="admin_clear_logs"),
            InlineKeyboardButton("📥 Download Stats", callback_data="admin_dl_stats"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def settings_keyboard():
    settings = db.get_settings()
    maint = "🟢 ON" if settings["maintenance"] else "🔴 OFF"
    fj = "🟢 ON" if settings["force_join"] else "🔴 OFF"
    keyboard = [
        [InlineKeyboardButton(f"🛠️ Maintenance Mode: {maint}", callback_data="toggle_maintenance")],
        [InlineKeyboardButton(f"📌 Force Join: {fj}", callback_data="toggle_force_join")],
        [InlineKeyboardButton(f"📣 Set Force Join Channel", callback_data="set_force_channel")],
        [InlineKeyboardButton(f"✏️ Edit Welcome Message", callback_data="edit_welcome")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ You are not an admin.")
        return
    await update.message.reply_text(
        "👑 *Admin Panel*\n\nChoose an option:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_keyboard(),
    )


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if not db.is_admin(user_id):
        await query.edit_message_text("⛔ Access denied.")
        return

    data = query.data

    if data == "admin_panel":
        await query.edit_message_text(
            "👑 *Admin Panel*\n\nChoose an option:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_keyboard(),
        )

    elif data == "admin_stats":
        stats = db.get_stats()
        users = db.get_all_users()
        total_dl = stats.get("total_downloads", 0)
        total_users = len(users)
        banned = len(db.get_banned())
        admins = len(db.get_admins())
        text = (
            "📊 *Bot Statistics*\n\n"
            f"👥 Total Users: `{total_users}`\n"
            f"📥 Total Downloads: `{total_dl}`\n"
            f"🚫 Banned Users: `{banned}`\n"
            f"👑 Admins: `{admins}`\n"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
        )

    elif data == "admin_users":
        users = db.get_all_users()
        total = len(users)
        lines = [f"👥 *Users List* ({total} total)\n"]
        for uid, u in list(users.items())[:20]:
            name = u.get("full_name", "Unknown")
            dls = u.get("downloads", 0)
            lines.append(f"• {name} (`{uid}`) — {dls} downloads")
        if total > 20:
            lines.append(f"\n_...and {total - 20} more_")
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
        )

    elif data == "admin_broadcast":
        context.user_data["admin_action"] = "broadcast"
        await query.edit_message_text(
            "📢 *Broadcast*\n\nSend the message you want to broadcast to all users:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]]),
        )

    elif data == "admin_ban":
        context.user_data["admin_action"] = "ban"
        await query.edit_message_text(
            "🔨 *Ban User*\n\nSend the user ID to ban (optionally add reason after a space):\n`123456789 spam`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]]),
        )

    elif data == "admin_unban":
        context.user_data["admin_action"] = "unban"
        await query.edit_message_text(
            "✅ *Unban User*\n\nSend the user ID to unban:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]]),
        )

    elif data == "admin_banned_list":
        banned = db.get_banned()
        if not banned:
            text = "✅ No banned users."
        else:
            lines = [f"🚫 *Banned Users* ({len(banned)} total)\n"]
            for uid, info in banned.items():
                reason = info.get("reason", "—")
                lines.append(f"• `{uid}` — {reason}")
            text = "\n".join(lines)
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
        )

    elif data == "admin_add_admin":
        context.user_data["admin_action"] = "add_admin"
        await query.edit_message_text(
            "👑 *Add Admin*\n\nSend the user ID to promote:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]]),
        )

    elif data == "admin_remove_admin":
        context.user_data["admin_action"] = "remove_admin"
        await query.edit_message_text(
            "❌ *Remove Admin*\n\nSend the user ID to demote:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]]),
        )

    elif data == "admin_admin_list":
        admins = db.get_admins()
        if not admins:
            text = "No admins configured."
        else:
            lines = [f"👑 *Admin List* ({len(admins)} total)\n"]
            for aid in admins:
                user = db.get_user(aid)
                name = user.get("full_name", "Unknown") if user else "Unknown"
                lines.append(f"• {name} (`{aid}`)")
            text = "\n".join(lines)
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
        )

    elif data == "admin_settings":
        settings = db.get_settings()
        text = (
            "🔧 *Bot Settings*\n\n"
            f"🛠️ Maintenance: `{'ON' if settings['maintenance'] else 'OFF'}`\n"
            f"📌 Force Join: `{'ON' if settings['force_join'] else 'OFF'}`\n"
            f"📣 Channel: `{settings['force_join_channel'] or 'Not set'}`\n"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=settings_keyboard(),
        )

    elif data == "toggle_maintenance":
        settings = db.get_settings()
        new_val = not settings["maintenance"]
        db.update_setting("maintenance", new_val)
        status = "enabled" if new_val else "disabled"
        db.write_log(f"Admin {user_id} {status} maintenance mode")
        await query.edit_message_text(
            f"🛠️ Maintenance mode *{'enabled' if new_val else 'disabled'}*.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=settings_keyboard(),
        )

    elif data == "toggle_force_join":
        settings = db.get_settings()
        new_val = not settings["force_join"]
        db.update_setting("force_join", new_val)
        await query.edit_message_text(
            f"📌 Force join *{'enabled' if new_val else 'disabled'}*.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=settings_keyboard(),
        )

    elif data == "set_force_channel":
        context.user_data["admin_action"] = "set_force_channel"
        await query.edit_message_text(
            "📣 Send the channel username (e.g. @mychannel):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_settings")]]),
        )

    elif data == "edit_welcome":
        context.user_data["admin_action"] = "edit_welcome"
        await query.edit_message_text(
            "✏️ Send the new welcome message:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_settings")]]),
        )

    elif data == "admin_maintenance":
        settings = db.get_settings()
        new_val = not settings["maintenance"]
        db.update_setting("maintenance", new_val)
        status = "enabled" if new_val else "disabled"
        db.write_log(f"Admin {user_id} {status} maintenance mode via quick toggle")
        await query.edit_message_text(
            f"🛠️ Maintenance mode *{status}*.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
        )

    elif data == "admin_msg_user":
        context.user_data["admin_action"] = "msg_user_id"
        await query.edit_message_text(
            "📨 *Message User*\n\nSend the user ID first:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]]),
        )

    elif data == "admin_export":
        users = db.get_all_users()
        lines = ["ID,Username,Name,Joined,Downloads"]
        for uid, u in users.items():
            lines.append(
                f"{uid},{u.get('username','')},{u.get('full_name','')},{u.get('joined','')},{u.get('downloads',0)}"
            )
        csv_text = "\n".join(lines)
        csv_path = "data/users_export.csv"
        with open(csv_path, "w") as f:
            f.write(csv_text)
        await query.message.reply_document(
            document=open(csv_path, "rb"),
            filename="users_export.csv",
            caption=f"📁 Users export — {len(users)} users",
        )
        await query.edit_message_text(
            "✅ Export sent above.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
        )

    elif data == "admin_logs":
        logs = db.read_logs(30)
        if len(logs) > 3500:
            logs = logs[-3500:]
        await query.edit_message_text(
            f"📜 *Recent Logs*\n\n```\n{logs}\n```",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
        )

    elif data == "admin_clear_logs":
        db.clear_logs()
        await query.edit_message_text(
            "🗑️ Logs cleared.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
        )

    elif data == "admin_dl_stats":
        users = db.get_all_users()
        stats = db.get_stats()
        total_dl = stats.get("total_downloads", 0)
        top = sorted(users.values(), key=lambda u: u.get("downloads", 0), reverse=True)[:10]
        lines = [f"📥 *Download Statistics*\n\nTotal: `{total_dl}`\n\n🏆 Top Users:"]
        for i, u in enumerate(top, 1):
            lines.append(f"{i}. {u.get('full_name', 'Unknown')} — {u.get('downloads', 0)} downloads")
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]),
        )


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handles admin text input for pending actions. Returns True if handled."""
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        return False

    action = context.user_data.get("admin_action")
    if not action:
        return False

    text = update.message.text.strip()
    context.user_data.pop("admin_action", None)

    if action == "broadcast":
        users = db.get_all_users()
        sent, failed = 0, 0
        for uid in users:
            try:
                await context.bot.send_message(int(uid), text)
                sent += 1
            except Exception:
                failed += 1
        db.write_log(f"Admin {user_id} broadcast to {sent} users ({failed} failed)")
        await update.message.reply_text(
            f"📢 Broadcast complete!\n✅ Sent: {sent}\n❌ Failed: {failed}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]),
        )
        return True

    elif action == "ban":
        parts = text.split(None, 1)
        try:
            ban_id = int(parts[0])
            reason = parts[1] if len(parts) > 1 else "No reason"
            db.ban_user(ban_id, reason)
            db.write_log(f"Admin {user_id} banned {ban_id}: {reason}")
            await update.message.reply_text(
                f"🔨 User `{ban_id}` has been banned.\nReason: {reason}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]),
            )
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID.")
        return True

    elif action == "unban":
        try:
            unban_id = int(text)
            db.unban_user(unban_id)
            db.write_log(f"Admin {user_id} unbanned {unban_id}")
            await update.message.reply_text(
                f"✅ User `{unban_id}` has been unbanned.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]),
            )
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID.")
        return True

    elif action == "add_admin":
        try:
            new_admin = int(text)
            db.add_admin(new_admin)
            db.write_log(f"Admin {user_id} promoted {new_admin}")
            await update.message.reply_text(
                f"👑 User `{new_admin}` is now an admin.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]),
            )
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID.")
        return True

    elif action == "remove_admin":
        try:
            rem_admin = int(text)
            if rem_admin == user_id:
                await update.message.reply_text("❌ You cannot demote yourself.")
            else:
                db.remove_admin(rem_admin)
                db.write_log(f"Admin {user_id} demoted {rem_admin}")
                await update.message.reply_text(
                    f"✅ User `{rem_admin}` removed from admins.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]),
                )
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID.")
        return True

    elif action == "set_force_channel":
        db.update_setting("force_join_channel", text)
        await update.message.reply_text(
            f"✅ Force join channel set to {text}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Settings", callback_data="admin_settings")]]),
        )
        return True

    elif action == "edit_welcome":
        db.update_setting("welcome_message", text)
        await update.message.reply_text(
            "✅ Welcome message updated.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Settings", callback_data="admin_settings")]]),
        )
        return True

    elif action == "msg_user_id":
        try:
            target_id = int(text)
            context.user_data["msg_user_target"] = target_id
            context.user_data["admin_action"] = "msg_user_text"
            await update.message.reply_text(
                f"📨 Now send the message for user `{target_id}`:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]]),
            )
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID.")
        return True

    elif action == "msg_user_text":
        target_id = context.user_data.pop("msg_user_target", None)
        if target_id:
            try:
                await context.bot.send_message(target_id, f"📨 Message from admin:\n\n{text}")
                db.write_log(f"Admin {user_id} messaged user {target_id}")
                await update.message.reply_text(
                    f"✅ Message sent to `{target_id}`.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]),
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Failed to send: {e}")
        return True

    return False
