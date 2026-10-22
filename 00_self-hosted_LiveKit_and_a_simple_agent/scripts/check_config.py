import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.settings import Settings
from scripts.setup import read_env


if __name__ == '__main__':
    try:
        Settings.from_env(read_env(ROOT / '.env'))
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc)) from None
    print('模型設定與憑證分離檢查通過。')
