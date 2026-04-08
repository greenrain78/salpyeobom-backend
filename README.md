

## 살펴봄

# .env 파일 설정
cp .env.example .env
# DATABASE_URL 수정 후

# 개발 서버 실행
uv run uvicorn app.main:app --reload

# 테스트
uv run pytest -v