"""
All bot text content and simple command/keyword replies live here.

Everything in the CONFIG section below is a placeholder — replace it with
your project's real info before the bot goes live in your group. Nothing
else in this file needs to change for basic customization.
"""

# ─── CONFIG: edit this section with your real project info ────────────
PROJECT_NAME = "$CHOW"

WELCOME_TEXT = (
    "🐕🌎 Welcome to the {project} community, {name}!\n"
    "Trade • Travel • Give Back — glad you're here.\n\n"
    "Check out /rules for the group rules and /about to learn what "
    "{project} is all about."
)

SCAM_WARNING_TEXT = (
    "⚠️ *Stay safe:*\n"
    "• Admins will *never* DM you first.\n"
    "• We will *never* ask for your seed phrase or private keys.\n"
    "• Beware fake support accounts and fake giveaways."
)

RULES_TEXT = (
    "📜 *Group Rules*\n"
    "1. Be respectful — no harassment, hate speech, or spam.\n"
    "2. No unsolicited DMs or promoting other projects.\n"
    "3. No financial advice — DYOR.\n"
    "4. Follow admins and moderators.\n"
    "5. Violations may result in a mute or ban."
)

ABOUT_TEXT = (
    f"🐕 *About {PROJECT_NAME}*\n"
    f"{PROJECT_NAME} is a Solana community built around trade, travel, "
    "and giving back — not just another token. Weekly giveaways, real "
    "community content, and a brand you can actually belong to. 🌎"
)
# ────────────────────────────────────────────────────────────────────

COMMANDS = {
    "/start": f"👋 Hi! I'm the {PROJECT_NAME} bot. Type /help to see what I can do.",
    "/help": (
        "Here's what I understand:\n"
        "/rules - group rules\n"
        "/about - about the project\n"
        "/announce <text> - admins only, post an announcement"
    ),
    "/rules": RULES_TEXT,
    "/about": ABOUT_TEXT,
}

# Case-insensitive substring matches — optional flavor, checked only if no
# command matched. Order matters — first match wins.
KEYWORDS = [
    (("gm", "good morning"), "GM! ☀️"),
]


def get_reply(text: str) -> str | None:
    """Return a reply for the given incoming message text, or None to stay silent."""
    stripped = text.strip()
    command = stripped.split()[0].split("@")[0] if stripped else ""

    if command in COMMANDS:
        return COMMANDS[command]

    lowered = stripped.lower()
    for triggers, reply in KEYWORDS:
        if any(trigger in lowered for trigger in triggers):
            return reply

    # Stay quiet on everything else — this is a group chat, not a 1:1 bot,
    # so we don't want to reply to every random message.
    return None
