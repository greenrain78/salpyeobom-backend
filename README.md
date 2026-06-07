# 살펴봄 (salpyeobom-backend)

고령자 원격 모니터링 백엔드 API. ADL 원시 데이터를 수집·전처리하고 AI 모델 추론
결과를 바탕으로 복지사 대시보드에 실시간 위험도(정상/주의/초고위험)를 제공한다.

상세 런타임 규칙은 [`CLAUDE.md`](./CLAUDE.md), DB 스키마는 [`docs/database-schema.md`](./docs/database-schema.md) 참고.

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| 백엔드 | FastAPI (async), Tortoise ORM, asyncpg, Aerich |
| 데이터베이스 | PostgreSQL (운영), SQLite in-memory (테스트) |
| 인증 | JWT (python-jose, HS256), bcrypt |
| 프론트엔드 | 정적 HTML/CSS/Vanilla JS (빌드 도구 없음), Tailwind CSS(CDN) |
| AI / 데이터 | Sliding Window 전처리, Hierarchical GRU AutoEncoder (Track A/B) |
| 패키지 관리 | uv (Python 3.11+) |
| 품질 | pytest + pytest-asyncio, ruff, mypy, pre-commit |
| 운영 | systemd, poethepoet (`poe`) 태스크 러너 |

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

태스크 러너는 **`poe` ([poethepoet](https://poethepoet.natn.io/))** — Windows / WSL / Ubuntu 동일 동작.

```bash
# 최초 1회 (머신당)
uv tool install poethepoet
# 프론트는 정적 파일이라 별도 설치 과정이 없다.

# 앱 실행 — 백엔드가 frontend/ 를 정적 서빙하므로 한 프로세스로 API+프론트가 모두 :8000 에 뜬다.
poe run                 # API+프론트 (uvicorn --reload, :8000) — 로컬 DB
poe run-remote          # 동일하되 원격 DB(.env) 연결

poe test                # 테스트 실행 (SQLite in-memory)
poe check               # lint + format + typecheck + test (커밋 전 필수)
poe fix                 # ruff 자동 수정 (lint autofix + format)
poe migrate             # aerich upgrade

poe                     # 전체 태스크 목록
```

> 폴백: `uv tool install` 없이도 `uv run poe <task>` 로 동일하게 실행 가능 (이미 dev deps에 포함).

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
| `adl_raw` | `/api/v1/adl-raw` | `GET ""`, `GET /recipients`, `GET /recipients/{id}/records`, `GET /{id}` |
| `reports` | `/api/v1/reports` | `POST /email` (보고서 PDF 이메일 발송) |

그 외 경로(`/`, css/js 등)는 `frontend/` 정적 파일로 서빙된다. OpenAPI 문서: 개발 서버 기동 후 `http://localhost:8000/docs`.

---

## 폴더 구조

```
app/
├── main.py          # FastAPI 앱 팩토리 (create_app) + frontend/ 정적 마운트
├── config.py        # 환경변수 (Settings) — .env + .env.local
├── database.py      # Tortoise 초기화 + 모델 등록
├── core/            # 인증·예외·의존성·이메일(email.py)
├── models/          # Tortoise ORM 모델 (+ enums.py)
├── routers/         # HTTP 엔드포인트 (얇게)
├── services/        # 비즈니스 로직 (필터·집계·변환 — 순수 함수)
└── schemas/         # Pydantic 입출력 스키마 (common.py: SuccessResponse[T])

frontend/            # 정적 복지사 대시보드 (백엔드가 / 에 서빙)
tests/               # pytest (SQLite in-memory)
scripts/             # install/deploy/start/stop/status + load_derived/report/synthetic
data/derived/        # patients.jsonl — 오프라인 파생 메타 (load_derived 적재)
out/                 # 산출물 reports/(.docx,PDF), synthetic/ (gitignore)
docs/                # database-schema.md 등 레퍼런스
notebooks/           # ADL 데이터 적재·검증·분석 노트북
migrations/          # aerich 마이그레이션 (gitignore)
```

---

## 팀원

| 이름 | 역할 | 담당 |
|------|------|------|
| 김대원 | AI / 데이터 | 데이터 전처리(Sliding Window) 파이프라인 구축, Hierarchical GRU AE 모델 아키텍처 설계, Track A/B 학습 및 파인튜닝 코드 구현 |
| 김재섭 | 프론트엔드 / 기획 | 복지사 대시보드 UI/UX 설계, 실시간 위험도 레벨(정상/주의/초고위험) 연동, 어텐션 가중치 기반 직관적 시각화(Heatmap, Bar chart) 컴포넌트 구현 |
| 이지민 | 백엔드 / DB | PostgreSQL 비동기 연동, 1시간 주기 실시간 데이터 스트리밍 수신, sliding window 텐서 적재 및 AI 모델 추론 API 파이프라인 스크립트 완성 |
| 윤아림 | PM | 프로젝트 요구사항 정의, 일정 관리, 최종 결과 분석, 문서 작성 및 발표 총괄 |
