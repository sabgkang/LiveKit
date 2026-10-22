"""Probe running local services; a browser voice test is still required."""
import base64
import json
import urllib.error
import urllib.request


def main():
    try:
        for url in ('http://127.0.0.1:7880/', 'http://127.0.0.1:8081/', 'http://127.0.0.1:3000/health'):
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status != 200:
                    raise ValueError('健康檢查失敗。')
        request = urllib.request.Request('http://127.0.0.1:3000/api/token', data=b'{}',
                                        headers={'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:3000'})
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.load(response)
        payload = result['token'].split('.')[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
        if claims['video']['room'] != result['room'] or claims['roomConfig']['agents'][0]['agentName'] != 'local-voice':
            raise ValueError('房間或 Agent dispatch 設定錯誤。')
    except (OSError, ValueError, KeyError, urllib.error.URLError):
        raise SystemExit('啟動驗證失敗；請查看 docker compose ps 與 docker compose logs --tail=100。') from None
    print('LiveKit、Agent、網頁與 token 端點就緒。尚需瀏覽器實測 Cloud 語音。')


if __name__ == '__main__':
    main()
