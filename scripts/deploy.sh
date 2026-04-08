#!/usr/bin/env bash
# 배포 (git pull → 의존성 → 마이그레이션 → 재시작)
# 사용법: bash scripts/deploy.sh
set -euo pipefail

cd "$(dirname "$0")/.."

git pull origin main
uv sync --no-dev
uv run aerich upgrade
sudo systemctl restart salpyeobom-backend

echo "✓ 배포 완료 ($(date '+%Y-%m-%d %H:%M:%S'))"
