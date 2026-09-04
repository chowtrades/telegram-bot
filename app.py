"""
Simple command/reply Telegram bot, deployed on Render as a Flask web service
using webhook mode.

On startup, the app automatically registers its webhook with Telegram using:
  - TELEGRAM_TOKEN        (you set this in Render's dashboard -> Environment)
  - RENDER_EXTERNAL_URL   (set automatically by Render for every web service)

No manual "setWebhook" step is needed once TELEGRAM_TOKEN is set in Render.
"""

import logging
import os

import requests
from flask import Flask, request

from replies import get_reply

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("telegram-bot")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
API_BASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

app = Flask(__name__)


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


def send_message(chat_id: int, text: str) -> None:
    try:
        requests.post(
            f"{API_BASE}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
    except requests.RequestException:
        log.exception("Failed to send message to chat %s", chat_id)


@app.route("/", methods=["GET"])
def health() -> tuple[str, int]:
    """Render pings this to confirm the service is alive."""
    return "Bot is running.", 200


@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook() -> tuple[str, int]:
    update = request.get_json(silent=True) or {}
    message = update.get("message") or update.get("edited_message")

    if message and "text" in message:
        chat_id = message["chat"]["id"]
        text = message["text"]
        reply = get_reply(text)
        if reply:
            send_message(chat_id, reply)

    return "ok", 200


# Register the webhook once when the app process starts (works under gunicorn too).
set_webhook()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
