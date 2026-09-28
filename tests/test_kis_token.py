import json
import unittest
from unittest.mock import Mock, patch

from integrations.kis_token import cached_token, TokenStore


class TokenTests(unittest.TestCase):
    def setUp(self):
        self.state = {}
        self.store = Mock()
        self.store.read.side_effect = lambda: dict(self.state)
        self.store.write.side_effect = lambda value: self.state.update(value)
        self.response = Mock()
        self.response.json.return_value = {'access_token':'test-only-token', 'expires_in':86400}

    def run_at(self, now, prepare=True):
        with patch('integrations.kis_token.TokenStore', return_value=self.store), patch('integrations.kis_token.time.time', return_value=now):
            return cached_token('test-key', 'test-secret', 'unused.enc', 10, prepare=prepare)

    @patch.dict('os.environ', {'GITHUB_ACTIONS':'true', 'KIS_ALLOW_INITIAL_TOKEN':'true'})
    @patch('integrations.kis_token.requests.post')
    def test_one_issuance_across_three_runs_and_next_day(self, post):
        post.return_value = self.response
        start = 1790542800
        for offset in (0, 6*3600, 9*3600+35*60, 10*3600):
            self.assertEqual(self.run_at(start+offset), 'test-only-token')
        self.assertEqual(post.call_count, 1)
        self.run_at(start+86401)
        self.assertEqual(post.call_count, 2)

    @patch.dict('os.environ', {'GITHUB_ACTIONS':'true', 'KIS_ALLOW_INITIAL_TOKEN':'false'})
    @patch('integrations.kis_token.requests.post')
    def test_missing_cache_does_not_issue(self, post):
        with self.assertRaisesRegex(RuntimeError, 'cache missing'):
            self.run_at(1790542800)
        post.assert_not_called()

    @patch.dict('os.environ', {'GITHUB_ACTIONS':'true', 'KIS_ALLOW_INITIAL_TOKEN':'true'})
    @patch('integrations.kis_token.requests.post')
    def test_failed_issuance_never_retried(self, post):
        post.side_effect = RuntimeError('private diagnostic')
        with self.assertRaisesRegex(RuntimeError, 'no retry'):
            self.run_at(1790542800)
        with self.assertRaisesRegex(RuntimeError, 'limited'):
            self.run_at(1790542900)
        post.assert_called_once()

    @patch('integrations.kis_token.requests.post')
    def test_query_process_cannot_issue(self, post):
        with self.assertRaises(RuntimeError):
            self.run_at(1790542800, prepare=False)
        post.assert_not_called()

    def test_ciphertext_hides_token_and_rejects_wrong_key(self):
        store = TokenStore('unused.enc', 'key', 'secret')
        encoded = store.cipher.encrypt(json.dumps({'token':'private-token'}).encode())
        self.assertNotIn(b'private-token', encoded)
        self.assertEqual(json.loads(store.cipher.decrypt(encoded))['token'], 'private-token')
        with self.assertRaises(Exception):
            TokenStore('unused.enc', 'key', 'wrong').cipher.decrypt(encoded)

    @patch('integrations.kis_token.requests.post')
    def test_corrupt_cache_fails_without_request(self, post):
        with patch('integrations.kis_token.Path.exists', return_value=True), patch('integrations.kis_token.Path.read_bytes', return_value=b'broken'):
            with self.assertRaisesRegex(RuntimeError, 'cannot be read'):
                cached_token('key', 'secret', 'unused.enc', 10, prepare=True)
        post.assert_not_called()

    @patch('integrations.kis_token.requests.post')
    def test_same_day_expired_token_cannot_be_reissued(self, post):
        self.state.update({'token':'expired-test-token','expiresAt':1790542800,'lastAttempt':1790542700})
        with self.assertRaisesRegex(RuntimeError, 'limited'):
            self.run_at(1790542900)
        post.assert_not_called()
