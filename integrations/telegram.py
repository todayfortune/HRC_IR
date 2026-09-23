from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession

@dataclass(frozen=True)
class ChannelMessage:
    id: int
    date: datetime | None
    text: str

def _session(value: str):
    if len(value) > 100 and not any(char in value for char in ("/", "\\")):
        return StringSession(value)
    path = Path(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)

async def recent_channel_messages(api_id: int, api_hash: str, session: str, channel: str, limit: int = 20) -> list[ChannelMessage]:
    """Create/reuse a Telegram session and read recent channel messages only."""
    client = TelegramClient(_session(session), api_id, api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram 세션 인증이 필요합니다. 먼저 scripts/create_telegram_session.py를 실행하세요.")
        messages = await client.get_messages(channel, limit=limit)
        return [ChannelMessage(m.id, m.date, m.message or "") for m in messages]
    finally:
        await client.disconnect()

async def create_session(api_id: int, api_hash: str, session: str) -> None:
    """Interactively authorize and persist a Telethon session."""
    client = TelegramClient(_session(session), api_id, api_hash)
    await client.start()
    await client.disconnect()
