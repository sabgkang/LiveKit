"""Minimal HS256 issuer for local room-scoped LiveKit participant tokens."""
import base64
import hashlib
import hmac
import json
import secrets
import time


def encode_part(value):
    return base64.urlsafe_b64encode(json.dumps(value, separators=(',', ':')).encode()).rstrip(b'=').decode()


def issue_token(api_key, api_secret, now=None):
    if not api_key or len(api_secret) < 32:
        raise ValueError('自架 LiveKit 憑證未設定或 secret 太短。')
    now = int(time.time() if now is None else now)
    room = 'voice-' + secrets.token_hex(12)
    identity = 'user-' + secrets.token_hex(12)
    claims = {
        'iss': api_key, 'sub': identity, 'name': '本機使用者',
        'iat': now, 'nbf': now - 5, 'exp': now + 300,
        'video': {'roomJoin': True, 'room': room, 'canPublish': True,
                  'canPublishSources': ['microphone'], 'canSubscribe': True, 'canPublishData': True},
        'roomConfig': {'emptyTimeout': 60, 'departureTimeout': 10, 'maxParticipants': 2,
                       'agents': [{'agentName': 'local-voice'}]},
    }
    body = encode_part({'alg': 'HS256', 'typ': 'JWT'}) + '.' + encode_part(claims)
    signature = hmac.new(api_secret.encode(), body.encode(), hashlib.sha256).digest()
    token = body + '.' + base64.urlsafe_b64encode(signature).rstrip(b'=').decode()
    return {'token': token, 'room': room, 'identity': identity}
