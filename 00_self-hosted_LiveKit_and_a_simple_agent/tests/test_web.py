from io import BytesIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'web'))
from server import Handler


class HandlerTests(unittest.TestCase):
    """Exercise request boundaries without opening sockets in the sandbox."""
    def request(self, *, host='localhost:3000', origin='http://localhost:3000', body=b'{}', ready=True):
        handler = object.__new__(Handler)
        handler.path = '/api/token'
        handler.headers = {'Host': host, 'Origin': origin, 'Content-Type': 'application/json', 'Content-Length': str(len(body))}
        handler.rfile = BytesIO(body)
        result = []
        handler.send_content = lambda code, content: result.append((code, content))
        with patch('server.upstream_ready', return_value=ready), patch.dict('os.environ', {
            'LIVEKIT_API_KEY': 'local-key', 'LIVEKIT_API_SECRET': 's' * 64,
            'LIVEKIT_INFERENCE_API_SECRET': 'cloud-secret-never-expose',
        }):
            handler.do_POST()
        return result[0]

    def test_dns_rebinding_and_cross_origin_requests_rejected(self):
        self.assertEqual(self.request(host='attacker.invalid:3000')[0], 403)
        self.assertEqual(self.request(origin='https://attacker.invalid')[0], 403)
        self.assertEqual(self.request(origin='null')[0], 403)

    def test_unready_services_return_503(self):
        self.assertEqual(self.request(ready=False)[0], 503)

    def test_client_cannot_choose_room_or_grants(self):
        self.assertEqual(self.request(body=b'{"room":"admin"}')[0], 400)
        self.assertEqual(self.request(body=b'not json')[0], 400)

    def test_response_has_no_cloud_credentials(self):
        code, content = self.request()
        self.assertEqual(code, 200)
        self.assertNotIn('cloud-secret', str(content))
        self.assertEqual(content['url'], 'ws://127.0.0.1:7880')


if __name__ == '__main__':
    unittest.main()
