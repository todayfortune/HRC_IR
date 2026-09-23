# Linux server deployment

This project uses an always-on server and a persistent Telethon session. GitHub Actions is not the default because this workspace has no repository/deployment pipeline that can deliver generated daily JSON back to the running application.

1. Install the project at `/opt/stock_view` and create `.venv`.
2. Put `.env` at `/opt/stock_view/.env`; keep it readable only by the service account.
3. Run `scripts/create_telegram_session.py` once as the `stockview` user on the server.
4. Copy the three unit files to `/etc/systemd/system/`.
5. Enable `stock-view.service` and `telegram-update.timer`.

The timer runs at minute 00 and 30 in `Asia/Seoul`, catches up after downtime, and stores only configured excerpts in the daily report JSON. Telegram attachment files and PDFs are not copied.
