export PATH := $(HOME)/.local/bin:$(PATH)

.PHONY: dev test migrate seed seed-reset deploy start stop restart status logs help

.DEFAULT_GOAL := help

help:
	@echo "사용 가능한 명령어:"
	@echo "  make dev          개발 서버 실행 (auto-reload)"
	@echo "  make test         테스트 실행"
	@echo "  make migrate      DB 마이그레이션 적용"
	@echo "  make seed         더미 데이터 생성"
	@echo "  make seed-reset   더미 데이터 초기화 후 재생성"
	@echo "  make deploy       배포 (git pull → sync → migrate → restart)"
	@echo "  make start        서버 시작"
	@echo "  make stop         서버 중지"
	@echo "  make restart      서버 재시작"
	@echo "  make status       서버 상태 확인"
	@echo "  make logs         실시간 로그"

.DEFAULT:
	@echo "알 수 없는 명령어: '$@'"
	@echo "사용 가능한 명령어 목록: make help"
	@exit 1

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
