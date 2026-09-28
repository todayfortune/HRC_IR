import os
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from integrations.env import load_env, require_env
from integrations.kis_token import cached_token, TokenStore

if __name__ == '__main__':
    load_env()
    key, secret = require_env('KIS_APP_KEY', 'KIS_APP_SECRET')
    path = os.environ['KIS_TOKEN_CACHE_PATH']
    store = TokenStore(path, key, secret)
    if not store.read():
        # Migration guard: old workflows discarded the morning token. Do not
        # issue again within 24h of their last successful refresh.
        snapshot = Path(__file__).resolve().parents[1] / 'data/market_latest.json'
        if snapshot.exists():
            previous = json.loads(snapshot.read_text(encoding='utf-8')).get('updatedAt')
            if previous:
                import time
                last = datetime.fromisoformat(previous).timestamp()
                if time.time() - last < 86400:
                    store.write({'lastAttempt': last})
                    raise RuntimeError('Initial cache migration: last KIS refresh is less than 24h old; refusing another token issuance.')
    cached_token(key, secret, path, 15, prepare=True)
