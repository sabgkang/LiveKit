#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
docker_cmd=(docker)
if [[ "${1:-}" == '--sudo-docker' && "$#" == 1 ]]; then
  docker_cmd=(sudo docker)
elif [[ "$#" != 0 ]]; then
  echo '用法：bash scripts/start.sh [--sudo-docker]' >&2
  exit 2
fi
python3 scripts/setup.py
python3 scripts/check_config.py
if ! "${docker_cmd[@]}" info >/dev/null; then
  echo 'Docker 檢查失敗；請依上方錯誤判斷 daemon 未啟動或 socket 權限不足。' >&2
  echo '若為權限不足，可在本機執行：bash scripts/start.sh --sudo-docker' >&2
  exit 1
fi
python3 scripts/preflight.py
"${docker_cmd[@]}" compose config --quiet
"${docker_cmd[@]}" compose up -d --build --wait --wait-timeout 240
python3 scripts/smoke.py
echo '請開啟 http://localhost:3000，選擇 Jabra 麥克風與喇叭。'
