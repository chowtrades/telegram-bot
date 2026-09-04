# Telegram Bot (Flask + Render)

A simple command/reply Telegram bot. Runs as a Flask web service and talks to
Telegram over a webhook.

## How it works

- `app.py` — Flask app with a `/webhook/<TELEGRAM_TOKEN>` route that Telegram
  posts updates to, and a `/` health-check route Render uses to confirm the
  service is alive.
- `replies.py` — all the bot's replies. Edit `COMMANDS` and `KEYWORDS` here to
  change what the bot says.
- On startup, the app automatically calls Telegram's `setWebhook` API using
  `RENDER_EXTERNAL_URL` (set automatically by Render) and `TELEGRAM_TOKEN`
  (you set this yourself). No manual webhook step needed.

## Deploying on Render

1. Push this repo to GitHub.
2. In Render, create a **New Web Service** and connect this repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add an environment variable: `TELEGRAM_TOKEN` = *(your bot token from
   @BotFather)*.
6. Deploy. Once live, the app registers its own webhook automatically — no
   further setup needed.
7. Message your bot on Telegram to confirm it responds to `/start`.

## Customizing replies

Open `replies.py`:

- Add a new exact command by adding a key to `COMMANDS`, e.g. `"/price": "..."`.
- Add a new keyword trigger by adding a tuple to `KEYWORDS`.

## Running locally (optional)

```bash
pip install -r requirements.txt
export TELEGRAM_TOKEN=your-token-here
python app.py
```

Locally there's no public HTTPS URL, so webhook registration is skipped
automatically (you'll see a log message). To test locally you'd need a
tunnel (e.g. ngrok) and to set `RENDER_EXTERNAL_URL` to that tunnel URL.
