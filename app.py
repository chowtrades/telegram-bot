"""
$CHOW community Telegram bot, deployed on Render as a Flask web service
using webhook mode.

Features:
  - Auto-welcome + scam warning for new members
  - /rules, /about, /help, /start commands (edit text in replies.py)
  - /announce <text> — admin-only, checked live against Telegram's actual
    chat admin list (no hardcoded admin IDs)
  - Basic anti-spam: flood control (mutes fast posters) and a short grace
    period blocking new members from posting links

IMPORTANT SETUP STEPS (do these once in Telegram, not in code):
  1. Add this bot to your group and promote it to admin with at least
     "Delete messages" and "Restrict members" permissions — anti-spam and
     muting won't work without this.
  2. Message @BotFather -> /setprivacy -> select this bot -> Disable.
     By default Telegram bots only see commands and messages that mention
     them. Disabling privacy mode lets the bot see all group messages,
     which the anti-spam checks need.

On startup, the app automatically registers its webhook with Telegram using:
  - TELEGRAM_TOKEN        (you set this in Render's dashboard -> Environment)
  - RENDER_EXTERNAL_URL   (set automatically by Render for every web service)
"""

import logging
import os
import re
import time

import requests
from flask import Flask, request

from replies import PROJECT_NAME, SCAM_WARNING_TEXT, WELCOME_TEXT, get_reply

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("telegram-bot")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
API_BASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

app = Flask(__name__)

# ─── Anti-spam config ──────────────────────────────────────────────────
FLOOD_MAX_MESSAGES = 5          # messages...
FLOOD_WINDOW_SECONDS = 10       # ...within this many seconds counts as flooding
FLOOD_MUTE_SECONDS = 600        # mute duration when flooding is detected

NEW_MEMBER_LINK_GRACE_SECONDS = 300  # new members can't post links for 5 min
URL_RE = re.compile(r"https?://|t\.me/|www\.", re.IGNORECASE)

ADMIN_CACHE_TTL = 60  # seconds, avoid hammering getChatMember on every message

# In-memory state. This is a single-process bot (Render's WEB_CONCURRENCY=1
# default for this app), so this is fine, but it resets on every redeploy
# or restart — that's expected and acceptable for a lightweight bot.
_message_times: dict[tuple[int, int], list[float]] = {}
_join_times: dict[tuple[int, int], float] = {}
_admin_cache: dict[tuple[int, int], tuple[bool, float]] = {}


def set_webhook() -> None:
    """Register this service's URL with Telegram so it starts receiving updates."""
    if not TELEGRAM_TOKEN:
        log.warning("TELEGRAM_TOKEN is not set — skipping webhook registration.")
        return
    if not RENDER_EXTERNAL_URL:
        log.warning("RENDER_EXTERNAL_URL is not set — skipping webhook registration "
                     "(this is expected when running locally).")
        return

    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook/{TELEGRAM_TOKEN}"
    try:
        resp = requests.post(f"{API_BASE}/setWebhook", json={"url": webhook_url}, timeout=10)
        resp.raise_for_status()
        log.info("Webhook set to %s -> %s", webhook_url, resp.json())
    except requests.RequestException:
        log.exception("Failed to set Telegram webhook")


def send_message(chat_id: int, text: str, parse_mode: str = "Markdown") -> None:
    try:
        resp = requests.post(
            f"{API_BASE}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=10,
        )
        if not resp.ok:
            log.error("sendMessage failed (%s): %s", resp.status_code, resp.text)
    except requests.RequestException:
        log.exception("Failed to send message to chat %s", chat_id)


def delete_message(chat_id: int, message_id: int) -> None:
    try:
        resp = requests.post(
            f"{API_BASE}/deleteMessage",
            json={"chat_id": chat_id, "message_id": message_id},
            timeout=10,
        )
        if not resp.ok:
            log.error("deleteMessage failed (%s): %s", resp.status_code, resp.text)
    except requests.RequestException:
        log.exception("Failed to delete message %s in chat %s", message_id, chat_id)


def mute_user(chat_id: int, user_id: int, seconds: int) -> None:
    try:
        resp = requests.post(
            f"{API_BASE}/restrictChatMember",
            json={
                "chat_id": chat_id,
                "user_id": user_id,
                "permissions": {"can_send_messages": False},
                "until_date": int(time.time()) + seconds,
            },
            timeout=10,
        )
        if not resp.ok:
            log.error("restrictChatMember failed (%s): %s", resp.status_code, resp.text)
    except requests.RequestException:
        log.exception("Failed to mute user %s in chat %s", user_id, chat_id)


def is_admin(chat_id: int, user_id: int) -> bool:
    """Check live against Telegram whether this user is an admin/creator of the chat."""
    cache_key = (chat_id, user_id)
    cached = _admin_cache.get(cache_key)
    now = time.time()
    if cached and now - cached[1] < ADMIN_CACHE_TTL:
        return cached[0]

    result = False
    try:
        resp = requests.get(
            f"{API_BASE}/getChatMember",
            params={"chat_id": chat_id, "user_id": user_id},
            timeout=10,
        )
        resp.raise_for_status()
        status = resp.json().get("result", {}).get("status")
        result = status in ("administrator", "creator")
    except requests.RequestException:
        log.exception("Failed to check admin status for user %s in chat %s", user_id, chat_id)

    _admin_cache[cache_key] = (result, now)
    return result


def handle_new_members(chat_id: int, new_members: list) -> None:
    for member in new_members:
        if member.get("is_bot"):
            continue
        _join_times[(chat_id, member["id"])] = time.time()
        name = member.get("first_name") or "there"
        send_message(chat_id, WELCOME_TEXT.format(project=PROJECT_NAME, name=name))
        send_message(chat_id, SCAM_WARNING_TEXT)


def check_flood(chat_id: int, user_id: int) -> bool:
    """Record this message and return True if the user is flooding."""
    key = (chat_id, user_id)
    now = time.time()
    times = [t for t in _message_times.get(key, []) if now - t < FLOOD_WINDOW_SECONDS]
    times.append(now)
    _message_times[key] = times
    return len(times) > FLOOD_MAX_MESSAGES


def is_new_member_posting_link(chat_id: int, user_id: int, text: str) -> bool:
    joined_at = _join_times.get((chat_id, user_id))
    if joined_at is None:
        return False
    if time.time() - joined_at > NEW_MEMBER_LINK_GRACE_SECONDS:
        return False
    return bool(URL_RE.search(text))


def handle_command(chat_id: int, user_id: int, text: str) -> None:
    command = text.strip().split()[0].split("@")[0]

    if command == "/announce":
        if not is_admin(chat_id, user_id):
            send_message(chat_id, "🚫 This command is for admins only.")
            return
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /announce <message>")
            return
        send_message(chat_id, f"📢 *Announcement*\n\n{parts[1]}")
        return

    reply = get_reply(text)
    if reply:
        send_message(chat_id, reply)


@app.route("/", methods=["GET"])
def health() -> tuple[str, int]:
    """Render pings this to confirm the service is alive."""
    return "Bot is running.", 200


@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook() -> tuple[str, int]:
    update = request.get_json(silent=True) or {}
    message = update.get("message") or update.get("edited_message")

    if not message:
        return "ok", 200

    chat_id = message["chat"]["id"]
    chat_type = message["chat"].get("type", "private")

    if "new_chat_members" in message:
        handle_new_members(chat_id, message["new_chat_members"])
        return "ok", 200

    text = message.get("text")
    user = message.get("from") or {}
    user_id = user.get("id")
    message_id = message.get("message_id")

    if not text or user_id is None:
        return "ok", 200

    if text.startswith("/"):
        handle_command(chat_id, user_id, text)
        return "ok", 200

    # Anti-spam only applies in groups, not 1:1 chats with the bot.
    if chat_type in ("group", "supergroup"):
        if is_new_member_posting_link(chat_id, user_id, text):
            delete_message(chat_id, message_id)
            send_message(chat_id, "⚠️ New members can't post links for the first few minutes. Message removed.")
            return "ok", 200

        if check_flood(chat_id, user_id):
            delete_message(chat_id, message_id)
            mute_user(chat_id, user_id, FLOOD_MUTE_SECONDS)
            send_message(chat_id, "🔇 Muted for spamming.")
            return "ok", 200

    reply = get_reply(text)
    if reply:
        send_message(chat_id, reply)

    return "ok", 200


# Register the webhook once when the app process starts (works under gunicorn too).
set_webhook()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
