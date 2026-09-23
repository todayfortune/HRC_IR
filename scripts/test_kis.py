from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integrations.env import load_env, require_env
from integrations.kis import KisReadOnlyClient

def main() -> None:
    load_env()
    app_key, app_secret = require_env("KIS_APP_KEY", "KIS_APP_SECRET")
    client = KisReadOnlyClient(app_key, app_secret)
    print("[1/2] KIS 인증 요청...")
    client.authenticate()
    print("[1/2] KIS 인증 성공 (토큰은 출력하지 않음)")
    print("[2/2] 삼성전자(005930) 현재가 조회...")
    quote = client.get_domestic_quote("005930")
    print(f"[2/2] {quote.name} 현재가={quote.price:,}원 등락률={quote.change_rate:+.2f}% 거래량={quote.volume:,}")

if __name__ == "__main__":
    main()
