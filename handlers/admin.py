import html as html_mod
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import database as db

HTML = ParseMode.HTML


def h(text) -> str:
    return html_mod.escape(str(text))


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
        [InlineKeyboardButton("📣 Set Force Join Channel", callback_data="set_force_channel")],
        [InlineKeyboardButton("✏️ Edit Welcome Message", callback_data="edit_welcome")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_btn(label="🔙 Back", cb="admin_panel"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=cb)]])


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ You are not an admin.")
        return
    await update.message.reply_text(
        "👑 <b>Admin Panel</b>\n\nChoose an option:",
        parse_mode=HTML,
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

    # ── Admin Panel home ──────────────────────────────────────────────────────
    if data == "admin_panel":
        await query.edit_message_text(
            "👑 <b>Admin Panel</b>\n\nChoose an option:",
            parse_mode=HTML,
            reply_markup=admin_keyboard(),
        )

    # ── Statistics ────────────────────────────────────────────────────────────
    elif data == "admin_stats":
        stats = db.get_stats()
        total_users = db.user_count()
        banned = len(db.get_banned())
        admins = len(db.get_admins())
        total_dl = stats.get("total_downloads", 0)
        await query.edit_message_text(
            "📊 <b>Bot Statistics</b>\n\n"
            f"👥 Total Users: <code>{total_users}</code>\n"
            f"📥 Total Downloads: <code>{total_dl}</code>\n"
            f"🚫 Banned Users: <code>{banned}</code>\n"
            f"👑 Admins: <code>{admins}</code>\n",
            parse_mode=HTML,
            reply_markup=back_btn(),
        )

    # ── Users list ────────────────────────────────────────────────────────────
    elif data == "admin_users":
        users = db.get_all_users()
        total = len(users)
        lines = [f"👥 <b>Users List</b> ({total} total)\n"]
        for uid, u in list(users.items())[:20]:
            name = h(u.get("full_name", "Unknown"))
            dls = u.get("downloads", 0)
            lines.append(f"• {name} (<code>{uid}</code>) — {dls} downloads")
        if total > 20:
            lines.append(f"\n<i>...and {total - 20} more</i>")
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=HTML,
            reply_markup=back_btn(),
        )

    # ── Broadcast ─────────────────────────────────────────────────────────────
    elif data == "admin_broadcast":
        context.user_data["admin_action"] = "broadcast"
        await query.edit_message_text(
            "📢 <b>Broadcast</b>\n\nSend the message you want to broadcast to all users:",
            parse_mode=HTML,
            reply_markup=back_btn("❌ Cancel"),
        )

    # ── Ban ───────────────────────────────────────────────────────────────────
    elif data == "admin_ban":
        context.user_data["admin_action"] = "ban"
        await query.edit_message_text(
            "🔨 <b>Ban User</b>\n\nSend the user ID to ban (optionally add reason after a space):\n"
            "<code>123456789 spam</code>",
            parse_mode=HTML,
            reply_markup=back_btn("❌ Cancel"),
        )

    # ── Unban ─────────────────────────────────────────────────────────────────
    elif data == "admin_unban":
        context.user_data["admin_action"] = "unban"
        await query.edit_message_text(
            "✅ <b>Unban User</b>\n\nSend the user ID to unban:",
            parse_mode=HTML,
            reply_markup=back_btn("❌ Cancel"),
        )

    # ── Banned list ───────────────────────────────────────────────────────────
    elif data == "admin_banned_list":
        banned = db.get_banned()
        if not banned:
            text = "✅ No banned users."
        else:
            lines = [f"🚫 <b>Banned Users</b> ({len(banned)} total)\n"]
            for uid, info in banned.items():
                reason = h(info.get("reason", "—"))
                lines.append(f"• <code>{uid}</code> — {reason}")
            text = "\n".join(lines)
        await query.edit_message_text(text, parse_mode=HTML, reply_markup=back_btn())

    # ── Add admin ─────────────────────────────────────────────────────────────
    elif data == "admin_add_admin":
        context.user_data["admin_action"] = "add_admin"
        await query.edit_message_text(
            "👑 <b>Add Admin</b>\n\nSend the user ID to promote:",
            parse_mode=HTML,
            reply_markup=back_btn("❌ Cancel"),
        )

    # ── Remove admin ──────────────────────────────────────────────────────────
    elif data == "admin_remove_admin":
        context.user_data["admin_action"] = "remove_admin"
        await query.edit_message_text(
            "❌ <b>Remove Admin</b>\n\nSend the user ID to demote:",
            parse_mode=HTML,
            reply_markup=back_btn("❌ Cancel"),
        )

    # ── Admin list ────────────────────────────────────────────────────────────
    elif data == "admin_admin_list":
        admins = db.get_admins()
        if not admins:
            text = "No admins configured."
        else:
            lines = [f"👑 <b>Admin List</b> ({len(admins)} total)\n"]
            for aid in admins:
                user = db.get_user(aid)
                name = h(user.get("full_name", "Unknown")) if user else "Unknown"
                lines.append(f"• {name} (<code>{aid}</code>)")
            text = "\n".join(lines)
        await query.edit_message_text(text, parse_mode=HTML, reply_markup=back_btn())

    # ── Settings panel ────────────────────────────────────────────────────────
    elif data == "admin_settings":
        settings = db.get_settings()
        await query.edit_message_text(
            "🔧 <b>Bot Settings</b>\n\n"
            f"🛠️ Maintenance: <code>{'ON' if settings['maintenance'] else 'OFF'}</code>\n"
            f"📌 Force Join: <code>{'ON' if settings['force_join'] else 'OFF'}</code>\n"
            f"📣 Channel: <code>{h(settings['force_join_channel'] or 'Not set')}</code>\n",
            parse_mode=HTML,
            reply_markup=settings_keyboard(),
        )

    # ── Toggle maintenance ────────────────────────────────────────────────────
    elif data in ("toggle_maintenance", "admin_maintenance"):
        settings = db.get_settings()
        new_val = not settings["maintenance"]
        db.update_setting("maintenance", new_val)
        status = "enabled" if new_val else "disabled"
        db.write_log(f"Admin {user_id} {status} maintenance mode")
        if data == "toggle_maintenance":
            await query.edit_message_text(
                f"🛠️ Maintenance mode <b>{status}</b>.",
                parse_mode=HTML,
                reply_markup=settings_keyboard(),
            )
        else:
            await query.edit_message_text(
                f"🛠️ Maintenance mode <b>{status}</b>.",
                parse_mode=HTML,
                reply_markup=back_btn(),
            )

    # ── Toggle force join ─────────────────────────────────────────────────────
    elif data == "toggle_force_join":
        settings = db.get_settings()
        new_val = not settings["force_join"]
        db.update_setting("force_join", new_val)
        await query.edit_message_text(
            f"📌 Force join <b>{'enabled' if new_val else 'disabled'}</b>.",
            parse_mode=HTML,
            reply_markup=settings_keyboard(),
        )

    # ── Set force join channel ────────────────────────────────────────────────
    elif data == "set_force_channel":
        context.user_data["admin_action"] = "set_force_channel"
        await query.edit_message_text(
            "📣 Send the channel username (e.g. <code>@mychannel</code>):",
            parse_mode=HTML,
            reply_markup=back_btn("❌ Cancel", "admin_settings"),
        )

    # ── Edit welcome message ──────────────────────────────────────────────────
    elif data == "edit_welcome":
        context.user_data["admin_action"] = "edit_welcome"
        await query.edit_message_text(
            "✏️ Send the new welcome message:",
            parse_mode=HTML,
            reply_markup=back_btn("❌ Cancel", "admin_settings"),
        )

    # ── Message user ──────────────────────────────────────────────────────────
    elif data == "admin_msg_user":
        context.user_data["admin_action"] = "msg_user_id"
        await query.edit_message_text(
            "📨 <b>Message User</b>\n\nSend the user ID first:",
            parse_mode=HTML,
            reply_markup=back_btn("❌ Cancel"),
        )

    # ── Export users ──────────────────────────────────────────────────────────
    elif data == "admin_export":
        users = db.get_all_users()
        lines = ["ID,Username,Name,Joined,Downloads"]
        for uid, u in users.items():
            lines.append(
                f"{uid},{u.get('username','')},{u.get('full_name','').replace(',', ' ')},"
                f"{u.get('joined','')},{u.get('downloads',0)}"
            )
        csv_path = "data/users_export.csv"
        with open(csv_path, "w") as f:
            f.write("\n".join(lines))
        await query.message.reply_document(
            document=open(csv_path, "rb"),
            filename="users_export.csv",
            caption=f"📁 Users export — {len(users)} users",
        )
        await query.edit_message_text(
            "✅ Export sent above.",
            reply_markup=back_btn(),
        )

    # ── View logs ─────────────────────────────────────────────────────────────
    elif data == "admin_logs":
        logs = db.read_logs(30)
        if len(logs) > 3500:
            logs = logs[-3500:]
        await query.edit_message_text(
            f"📜 <b>Recent Logs</b>\n\n<pre>{h(logs)}</pre>",
            parse_mode=HTML,
            reply_markup=back_btn(),
        )

    # ── Clear logs ────────────────────────────────────────────────────────────
    elif data == "admin_clear_logs":
        db.clear_logs()
        await query.edit_message_text("🗑️ Logs cleared.", reply_markup=back_btn())

    # ── Download stats ────────────────────────────────────────────────────────
    elif data == "admin_dl_stats":
        users = db.get_all_users()
        stats = db.get_stats()
        total_dl = stats.get("total_downloads", 0)
        top = sorted(users.values(), key=lambda u: u.get("downloads", 0), reverse=True)[:10]
        lines = [f"📥 <b>Download Statistics</b>\n\nTotal: <code>{total_dl}</code>\n\n🏆 Top Users:"]
        for i, u in enumerate(top, 1):
            lines.append(f"{i}. {h(u.get('full_name', 'Unknown'))} — {u.get('downloads', 0)} downloads")
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=HTML,
            reply_markup=back_btn(),
        )


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle pending admin text input. Returns True if the message was consumed."""
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        return False

    action = context.user_data.get("admin_action")
    if not action:
        return False

    text = update.message.text.strip()
    context.user_data.pop("admin_action", None)

    def reply(msg, **kw):
        return update.message.reply_text(msg, parse_mode=HTML, **kw)

    # ── Broadcast ─────────────────────────────────────────────────────────────
    if action == "broadcast":
        users = db.get_all_users()
        sent = failed = 0
        for uid in users:
            try:
                await context.bot.send_message(int(uid), text)
                sent += 1
            except Exception:
                failed += 1
        db.write_log(f"Admin {user_id} broadcast to {sent} users ({failed} failed)")
        await reply(
            f"📢 Broadcast complete!\n✅ Sent: <b>{sent}</b>\n❌ Failed: <b>{failed}</b>",
            reply_markup=back_btn("🔙 Admin Panel"),
        )
        return True

    # ── Ban ───────────────────────────────────────────────────────────────────
    elif action == "ban":
        parts = text.split(None, 1)
        try:
            ban_id = int(parts[0])
            reason = parts[1] if len(parts) > 1 else "No reason"
            db.ban_user(ban_id, reason)
            db.write_log(f"Admin {user_id} banned {ban_id}: {reason}")
            await reply(
                f"🔨 User <code>{ban_id}</code> has been banned.\nReason: {h(reason)}",
                reply_markup=back_btn("🔙 Admin Panel"),
            )
        except ValueError:
            await reply("❌ Invalid user ID.")
        return True

    # ── Unban ─────────────────────────────────────────────────────────────────
    elif action == "unban":
        try:
            unban_id = int(text)
            db.unban_user(unban_id)
            db.write_log(f"Admin {user_id} unbanned {unban_id}")
            await reply(
                f"✅ User <code>{unban_id}</code> has been unbanned.",
                reply_markup=back_btn("🔙 Admin Panel"),
            )
        except ValueError:
            await reply("❌ Invalid user ID.")
        return True

    # ── Add admin ─────────────────────────────────────────────────────────────
    elif action == "add_admin":
        try:
            new_admin = int(text)
            db.add_admin(new_admin)
            db.write_log(f"Admin {user_id} promoted {new_admin}")
            await reply(
                f"👑 User <code>{new_admin}</code> is now an admin.",
                reply_markup=back_btn("🔙 Admin Panel"),
            )
        except ValueError:
            await reply("❌ Invalid user ID.")
        return True

    # ── Remove admin ──────────────────────────────────────────────────────────
    elif action == "remove_admin":
        try:
            rem_admin = int(text)
            if rem_admin == user_id:
                await reply("❌ You cannot demote yourself.")
            else:
                db.remove_admin(rem_admin)
                db.write_log(f"Admin {user_id} demoted {rem_admin}")
                await reply(
                    f"✅ User <code>{rem_admin}</code> removed from admins.",
                    reply_markup=back_btn("🔙 Admin Panel"),
                )
        except ValueError:
            await reply("❌ Invalid user ID.")
        return True

    # ── Set force join channel ────────────────────────────────────────────────
    elif action == "set_force_channel":
        db.update_setting("force_join_channel", text)
        await reply(
            f"✅ Force join channel set to <code>{h(text)}</code>",
            reply_markup=back_btn("🔙 Settings", "admin_settings"),
        )
        return True

    # ── Edit welcome message ──────────────────────────────────────────────────
    elif action == "edit_welcome":
        db.update_setting("welcome_message", text)
        await reply(
            "✅ Welcome message updated.",
            reply_markup=back_btn("🔙 Settings", "admin_settings"),
        )
        return True

    # ── Message user — step 1: get target ID ─────────────────────────────────
    elif action == "msg_user_id":
        try:
            target_id = int(text)
            context.user_data["msg_user_target"] = target_id
            context.user_data["admin_action"] = "msg_user_text"
            await reply(
                f"📨 Now send the message for user <code>{target_id}</code>:",
                reply_markup=back_btn("❌ Cancel"),
            )
        except ValueError:
            await reply("❌ Invalid user ID.")
        return True

    # ── Message user — step 2: send message ──────────────────────────────────
    elif action == "msg_user_text":
        target_id = context.user_data.pop("msg_user_target", None)
        if target_id:
            try:
                await context.bot.send_message(target_id, f"📨 Message from admin:\n\n{text}")
                db.write_log(f"Admin {user_id} messaged user {target_id}")
                await reply(
                    f"✅ Message sent to <code>{target_id}</code>.",
                    reply_markup=back_btn("🔙 Admin Panel"),
                )
            except Exception as e:
                await reply(f"❌ Failed to send: {h(str(e))}")
        return True

    return False
