"""
All bot reply logic lives here. Edit COMMANDS and KEYWORDS to customize
what your bot says — no need to touch app.py.
"""

# Exact-match commands, e.g. "/start", "/help"
COMMANDS = {
    "/start": (
        "👋 Hi! I'm your bot, up and running on Render.\n\n"
        "Type /help to see what I can do."
    ),
    "/help": (
        "Here's what I understand:\n"
        "/start - say hello\n"
        "/help - show this message\n"
        "/about - who I am\n\n"
        "I'll also reply to a few keywords — try saying \"hello\" or \"thanks\"."
    ),
    "/about": (
        "I'm a simple command/reply Telegram bot, running on Render "
        "and built with Python + Flask."
    ),
}

# Case-insensitive substring matches, checked if no exact command matched.
# Order matters — first match wins.
KEYWORDS = [
    (("hello", "hi", "hey"), "Hey there! 👋"),
    (("thanks", "thank you"), "You're welcome! 🙌"),
    (("bye", "goodbye"), "See you later!"),
]


def get_reply(text: str) -> str | None:
    """Return a reply for the given incoming message text, or None to stay silent."""
    stripped = text.strip()

    if stripped in COMMANDS:
        return COMMANDS[stripped]

    lowered = stripped.lower()
    for triggers, reply in KEYWORDS:
        if any(trigger in lowered for trigger in triggers):
            return reply

    # Fallback for anything else.
    return "Sorry, I didn't understand that. Type /help to see what I can do."
