import base64
import hashlib
import hmac
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'web'))
from tokens import issue_token


def decode(part):
    return base64.urlsafe_b64decode(part + '=' * (-len(part) % 4))


class TokenTests(unittest.TestCase):
    def test_signature_expiry_room_scope_and_named_dispatch(self):
        result = issue_token('local_key', 's' * 64, now=1000)
        header, payload, signature = result['token'].split('.')
        self.assertEqual(json.loads(decode(header))['alg'], 'HS256')
        self.assertTrue(hmac.compare_digest(
            hmac.new(b's' * 64, (header + '.' + payload).encode(), hashlib.sha256).digest(), decode(signature)))
        claims = json.loads(decode(payload))
        self.assertEqual(claims['exp'], 1300)
        self.assertEqual(claims['iss'], 'local_key')
        self.assertEqual(claims['sub'], result['identity'])
        self.assertEqual(claims['video']['room'], result['room'])
        self.assertEqual(claims['video']['canPublishSources'], ['microphone'])
        self.assertNotIn('roomAdmin', claims['video'])
        self.assertNotIn('inference', claims)
        self.assertEqual(claims['roomConfig']['agents'], [{'agentName': 'local-voice'}])

    def test_sessions_get_different_rooms_and_identities(self):
        first, second = [issue_token('key', 's' * 64) for _ in range(2)]
        self.assertNotEqual(first['room'], second['room'])
        self.assertNotEqual(first['identity'], second['identity'])

    def test_missing_credentials_fail_closed(self):
        for key, secret in (('', 's' * 64), ('key', ''), ('key', 'short')):
            with self.assertRaises(ValueError):
                issue_token(key, secret)


if __name__ == '__main__':
    unittest.main()
