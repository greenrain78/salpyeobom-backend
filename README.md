

## 살펴봄

# .env 파일 설정
cp .env.example .env
sudo iptables -I INPUT 5 -p tcp --dport 8000 -j ACCEPT
# DATABASE_URL 수정 후

# 개발 서버 실행
uv run uvicorn app.main:app --reload

# 테스트
uv run pytest -v

# 1. 최초 설치
bash scripts/install.sh
# → .env 파일 생성 후 중단됨

# 2. .env 설정
vim .env
# DATABASE_URL=postgres://user:pass@localhost:5432/salpyeobom
# SECRET_KEY=$(openssl rand -hex 32)

# 3. 재실행 (migrate + systemd 등록)
bash scripts/install.sh

# 이후 배포
bash scripts/deploy.sh
