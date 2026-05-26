# 살펴봄 (salpyeobom-backend)

고령자 원격 모니터링 백엔드 API. FastAPI(async) + Tortoise ORM + PostgreSQL.

상세 런타임 규칙은 [`CLAUDE.md`](./CLAUDE.md), DB 스키마는 [`docs/database-schema.md`](./docs/database-schema.md) 참고.

---

## 빠른 시작

### 1. 최초 설치

```bash
bash scripts/install.sh
# → .env 파일을 생성하고 중단됨 (DB 정보·SECRET_KEY 입력 필요)
```

### 2. `.env` 설정

```bash
vim .env
# DATABASE_URL=postgres://user:pass@127.0.0.1:5432/salpyeobom
# SECRET_KEY=$(openssl rand -hex 32)
```

### 3. 재실행

```bash
bash scripts/install.sh
# → DB 마이그레이션 적용 + systemd 서비스 등록 (배포 환경)
```

### 4. 로컬 개발

```bash
# 백엔드 + 프론트엔드 한 번에 (권장)
.\dev                   # Windows — dev.cmd 래퍼 (uv run python dev.py 와 동일)
uv run python dev.py    # 직접 실행 (모든 OS)
# → BE :8000, FE :3000. Ctrl+C 한 번에 둘 다 정리

# 개별 실행
make dev                # 백엔드만 (uvicorn --reload)
cd frontend && npm run dev   # 프론트엔드만 (Next.js)

make test               # 테스트 실행 (SQLite in-memory)
make check              # lint + typecheck + test (커밋 전 필수)
make migrate            # aerich upgrade
make seed               # 데모용 시드 데이터 (user_1001 등)
```

> 최초 1회: `cd frontend && cp .env.local.example .env.local && npm install`

### 5. 배포

```bash
bash scripts/deploy.sh
```

---

## 라우터 / 엔드포인트

| 라우터 | prefix | 주요 경로 |
|--------|--------|----------|
| `auth` | `/api/v1/auth` | `POST /register`, `POST /login`, `GET /me` |
| `dashboard` | `/api/v1/dashboard` | `GET /summary` |
| `patients` | `/api/v1/patients` | `GET ""`, `GET /{id}/details` |
| `situations` | `/api/v1/situations` | `GET /active` |

OpenAPI 문서: 개발 서버 기동 후 `http://localhost:8000/docs`.

---

## 폴더 구조

```
app/
├── main.py          # FastAPI 앱 팩토리 (create_app)
├── config.py        # 환경변수 (Settings)
├── database.py      # Tortoise 초기화 + 모델 등록
├── core/            # 인증·예외·의존성
├── models/          # Tortoise ORM 모델
├── routers/         # HTTP 엔드포인트
└── schemas/         # Pydantic 입출력 스키마

tests/               # pytest (SQLite in-memory)
scripts/             # install/deploy/seed/start/stop/status
docs/                # database-schema.md 등 레퍼런스
notebooks/           # ADL 데이터 적재·검증·분석 노트북
migrations/          # aerich 마이그레이션 (gitignore)
```
