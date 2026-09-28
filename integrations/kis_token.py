"""Encrypted, fail-closed token reuse across scheduled market updates."""
import base64
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from cryptography.fernet import Fernet


class TokenStore:
    def __init__(self, path, app_key, app_secret):
        self.path = Path(path)
        key = hashlib.sha256(("HRC-KIS-token-v1\0" + app_key + "\0" + app_secret).encode()).digest()
        self.cipher = Fernet(base64.urlsafe_b64encode(key))

    def read(self):
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.cipher.decrypt(self.path.read_bytes()))
        except Exception:
            raise RuntimeError("KIS token cache cannot be read; refusing automatic reissue.") from None

    def write(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_bytes(self.cipher.encrypt(json.dumps(state).encode()))
        temporary.chmod(0o600)
        temporary.replace(self.path)


def cached_token(app_key, app_secret, path, timeout, *, prepare=False):
    store = TokenStore(path, app_key, app_secret)
    state = store.read()
    now = time.time()
    if state.get('token') and state.get('expiresAt', 0) > now + 60:
        print('KIS token: reuse (no tokenP request)')
        return state['token']
    if not prepare:
        raise RuntimeError('KIS token unavailable or expired; run token preparation first. No reissue attempted.')
    last = state.get('lastAttempt', 0)
    today = datetime.fromtimestamp(now, ZoneInfo('Asia/Seoul')).date()
    if last and (now - last < 86400 or datetime.fromtimestamp(last, ZoneInfo('Asia/Seoul')).date() == today):
        raise RuntimeError('KIS token issuance limited to once per 24 hours / KST day.')
    if not state and os.getenv('GITHUB_ACTIONS') == 'true' and os.getenv('KIS_ALLOW_INITIAL_TOKEN') != 'true':
        raise RuntimeError('KIS token cache missing; afternoon/manual runs cannot issue a replacement.')
    # Persist the attempt before contacting KIS. Failure does not trigger retries.
    store.write({'lastAttempt': now})
    try:
        response = requests.post('https://openapi.koreainvestment.com:9443/oauth2/tokenP',
            json={'grant_type':'client_credentials','appkey':app_key,'appsecret':app_secret}, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        token = payload['access_token']
        expiry = now + min(float(payload['expires_in']), 86400)
        if payload.get('access_token_token_expired'):
            expiry = min(expiry, datetime.strptime(payload['access_token_token_expired'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=ZoneInfo('Asia/Seoul')).timestamp())
        if not token or expiry <= now + 60:
            raise ValueError('Invalid token validity')
    except Exception:
        raise RuntimeError('KIS token issuance failed; no retry. Existing market data preserved.') from None
    store.write({'token':token, 'expiresAt':expiry, 'lastAttempt':now})
    print('KIS token: issued once; encrypted cache saved')
    return token
