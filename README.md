# $CHOW Community Telegram Bot (Flask + Render)

A community-management Telegram bot: welcomes new members, posts a scam
warning, and provides `/rules`, `/links`, `/about`, plus basic anti-spam
and an admin-only `/announce` command. Runs as a Flask web service and
talks to Telegram over a webhook.

## ⚠️ Required one-time setup in Telegram (not in code)

1. **Add the bot to your group and make it an admin**, with at least
   *Delete messages* and *Restrict members* permissions. Without this,
   the anti-spam features (deleting spam, muting floods) silently won't
   work.
2. **Disable the bot's privacy mode**: message **@BotFather** →
   `/setprivacy` → select this bot → **Disable**. By default, Telegram
   bots only see commands and messages that mention them. Disabling
   privacy mode lets the bot see all group messages, which anti-spam
   needs to function.

## How it works

- `app.py` — Flask app with a `/webhook/<TELEGRAM_TOKEN>` route Telegram
  posts updates to, a `/` health-check route for Render, new-member
  welcome handling, anti-spam (flood control + a link-posting grace
  period for new members), and the admin-only `/announce` command
  (checked live against Telegram's real admin list — no hardcoded IDs).
- `replies.py` — all of the bot's text content and simple commands.
  **Edit the CONFIG section at the top** (`RULES_TEXT`, `LINKS_TEXT`,
  `ABOUT_TEXT`, `WELCOME_TEXT`, `SCAM_WARNING_TEXT`) with your project's
  real info — it currently has placeholder text marked `EDIT-ME`.
- On startup, the app automatically calls Telegram's `setWebhook` API
  using `RENDER_EXTERNAL_URL` (set automatically by Render) and
  `TELEGRAM_TOKEN` (you set this yourself). No manual webhook step
  needed.

## Commands

- `/start`, `/help` — basic info
- `/rules` — group rules
- `/links` — official links
- `/about` — about the project
- `/announce <text>` — admins only; posts a formatted announcement

## Anti-spam behavior

- **New-member link grace period**: for 5 minutes after joining, a new
  member's messages containing links are deleted automatically.
- **Flood control**: more than 5 messages in 10 seconds gets the
  message deleted and the user muted for 10 minutes.
- These thresholds are constants near the top of `app.py`
  (`FLOOD_MAX_MESSAGES`, `FLOOD_WINDOW_SECONDS`, `FLOOD_MUTE_SECONDS`,
  `NEW_MEMBER_LINK_GRACE_SECONDS`) if you want to tune them.
- State is kept in memory, so it resets on every redeploy/restart —
  fine for a lightweight bot.

## Deploying on Render

1. Push this repo to GitHub.
2. In Render, create a **New Web Service** and connect this repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add an environment variable: `TELEGRAM_TOKEN` = *(your bot token from
   @BotFather)*.
6. Deploy. Once live, the app registers its own webhook automatically.
7. Complete the two Telegram setup steps above (admin + privacy mode).

## Running locally (optional)

```bash
pip install -r requirements.txt
export TELEGRAM_TOKEN=your-token-here
python app.py
```

Locally there's no public HTTPS URL, so webhook registration is skipped
automatically. To test locally you'd need a tunnel (e.g. ngrok) and to
set `RENDER_EXTERNAL_URL` to that tunnel URL.
