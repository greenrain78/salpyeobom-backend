#!/usr/bin/env bash
# 서버 최초 1회 실행
# 사용법: bash scripts/install.sh
set -euo pipefail

cd "$(dirname "$0")/.."

# 시스템 패키지
sudo apt-get install -y make curl

# uv 설치
if ! command -v uv &>/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  source "$HOME/.local/bin/env"
fi

# 의존성 설치
uv sync --no-dev

# .env 설정
if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "⚠  .env 파일을 열어 DATABASE_URL과 SECRET_KEY를 설정하세요."
  echo "   SECRET_KEY 생성: openssl rand -hex 32"
  echo ""
  exit 0
fi

# DB 마이그레이션
if [ ! -d migrations ]; then
  uv run aerich init -t app.database.TORTOISE_ORM
  uv run aerich init-db
else
  uv run aerich upgrade
fi

# systemd 서비스 등록
SERVICE=/etc/systemd/system/salpyeobom-backend.service
sudo tee "$SERVICE" > /dev/null <<EOF
[Unit]
Description=Salpyeobom Backend
After=network.target postgresql.service

[Service]
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$HOME/.local/bin/uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
EnvironmentFile=$(pwd)/.env
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now salpyeobom-backend

echo "✓ 설치 완료"
echo "  상태: sudo systemctl status salpyeobom-backend"
echo "  로그: sudo journalctl -u salpyeobom-backend -f"
