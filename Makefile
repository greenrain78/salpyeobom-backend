.PHONY: dev test migrate deploy start stop restart status logs

dev:
	uv run uvicorn app.main:app --reload

test:
	uv run pytest -v

migrate:
	uv run aerich upgrade

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
