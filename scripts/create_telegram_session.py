from __future__ import annotations
import asyncio
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integrations.env import load_env, require_env
from integrations.telegram import create_session

async def run() -> None:
    load_env()
    api_id, api_hash, session = require_env("TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_SESSION")
    print("Telegram 세션 인증을 시작합니다. 인증정보는 저장하거나 출력하지 않습니다.")
    await create_session(int(api_id), api_hash, session)
    print("Telegram 세션 준비 완료")

if __name__ == "__main__":
    asyncio.run(run())
