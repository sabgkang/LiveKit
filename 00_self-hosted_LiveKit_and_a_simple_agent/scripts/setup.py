"""Create private local configuration without overwriting existing credentials."""
import json
import os
from pathlib import Path
import re
import secrets

ROOT = Path(__file__).resolve().parents[1]


def read_env(path):
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep or not re.fullmatch(r'[A-Z][A-Z0-9_]*', key):
            raise ValueError('環境設定格式錯誤，請使用 KEY=value。')
        values[key] = value.strip()
    return values


def setup(root=ROOT):
    env_path = root / '.env'
    if not env_path.exists():
        content = (root / '.env.example').read_text()
        content = content.replace('LIVEKIT_API_KEY=\n', 'LIVEKIT_API_KEY=local_' + secrets.token_hex(12) + '\n')
        content = content.replace('LIVEKIT_API_SECRET=\n', 'LIVEKIT_API_SECRET=' + secrets.token_hex(32) + '\n')
        with env_path.open('x') as stream:
            stream.write(content)
    env_path.chmod(0o600)
    env = read_env(env_path)
    key, secret = env.get('LIVEKIT_API_KEY', ''), env.get('LIVEKIT_API_SECRET', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,}', key) or not re.fullmatch(r'[A-Za-z0-9_-]{32,}', secret):
        raise ValueError('自架金鑰格式錯誤；key 至少 8 字元、secret 至少 32 字元，只使用英數字、底線或連字號。')
    runtime = root / 'runtime'
    runtime.mkdir(mode=0o700, exist_ok=True)
    runtime.chmod(0o700)
    config = (
        'port: 7880\nbind_addresses:\n  - 127.0.0.1\n'
        'rtc:\n  node_ip: 127.0.0.1\n  use_external_ip: false\n'
        '  tcp_port: 7881\n  udp_port: 7882\n  enable_loopback_candidate: true\n'
        '  ips:\n    includes:\n      - 127.0.0.0/8\n'
        'logging:\n  level: info\nkeys:\n'
        f'  {json.dumps(key)}: {json.dumps(secret)}\n'
    )
    config_path = runtime / 'livekit.yaml'
    config_path.write_text(config)
    config_path.chmod(0o600)
    print('已準備 .env 與 runtime/livekit.yaml（不顯示金鑰）。')
    if not env.get('LIVEKIT_INFERENCE_API_KEY') or not env.get('LIVEKIT_INFERENCE_API_SECRET'):
        print('請在 .env 填入 LIVEKIT_INFERENCE_API_KEY 與 LIVEKIT_INFERENCE_API_SECRET。')


if __name__ == '__main__':
    os.umask(0o077)
    try:
        setup()
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc)) from None
