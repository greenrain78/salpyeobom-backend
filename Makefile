export PATH := $(HOME)/.local/bin:$(PATH)

.PHONY: dev test migrate seed seed-reset deploy start stop restart status logs \
        lint format typecheck check fix install-hooks help

.DEFAULT_GOAL := help

help:
	@echo "사용 가능한 명령어:"
	@echo ""
	@echo "  [개발]"
	@echo "  make dev           개발 서버 실행 (auto-reload)"
	@echo "  make test          테스트 실행 (커버리지 포함)"
	@echo "  make migrate       DB 마이그레이션 적용"
	@echo "  make seed          더미 데이터 생성"
	@echo "  make seed-reset    더미 데이터 초기화 후 재생성"
	@echo ""
	@echo "  [품질 검사 — 하네스]"
	@echo "  make lint          ruff 린트 검사"
	@echo "  make format        ruff 포맷 적용"
	@echo "  make typecheck     mypy 타입 체킹"
	@echo "  make check         전체 품질 검사 (lint + format + typecheck + test)"
	@echo "  make fix           ruff 자동 수정 (lint autofix + format)"
	@echo "  make install-hooks pre-commit 훅 설치"
	@echo ""
	@echo "  [배포]"
	@echo "  make deploy        배포 (git pull → sync → migrate → restart)"
	@echo "  make start         서버 시작"
	@echo "  make stop          서버 중지"
	@echo "  make restart       서버 재시작"
	@echo "  make status        서버 상태 확인"
	@echo "  make logs          실시간 로그"

.DEFAULT:
	@echo "알 수 없는 명령어: '$@'"
	@echo "사용 가능한 명령어 목록: make help"
	@exit 1

# ── 개발 ─────────────────────────────────────────────────────────────────────

dev:
	uv run uvicorn app.main:app --reload

test:
	uv run pytest -v

migrate:
	uv run aerich upgrade

seed:
	uv run python scripts/seed.py

seed-reset:
	uv run python scripts/seed.py --reset

# ── 품질 검사 (하네스 피드백 루프) ──────────────────────────────────────────

lint:
	uv run ruff check app/ tests/

format:
	uv run ruff format app/ tests/

typecheck:
	uv run mypy app/

check:
	@echo "=== [1/4] ruff lint ==="
	uv run ruff check app/ tests/
	@echo "=== [2/4] ruff format check ==="
	uv run ruff format --check app/ tests/
	@echo "=== [3/4] mypy typecheck ==="
	uv run mypy app/
	@echo "=== [4/4] pytest + coverage ==="
	uv run pytest -v
	@echo ""
	@echo "모든 품질 검사 통과!"

fix:
	@echo "ruff 자동 수정 중..."
	uv run ruff check --fix app/ tests/
	uv run ruff format app/ tests/
	@echo "완료. make check 로 결과를 확인하세요."

install-hooks:
	@echo "현재 환경에서는 git hook 대신 'make check'를 커밋 전에 직접 실행하세요."
	@echo "CI/CD (GitHub Actions)가 push 시 자동으로 전체 검사를 수행합니다."

# ── 배포 ─────────────────────────────────────────────────────────────────────

deploy:
	bash scripts/deploy.sh

start:
	bash scripts/start.sh

stop:
	bash scripts/stop.sh

restart:
	bash scripts/stop.sh && bash scripts/start.sh

status:
	bash scripts/status.sh

logs:
	sudo journalctl -u salpyeobom-backend -f
