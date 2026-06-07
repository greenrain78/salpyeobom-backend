# CLAUDE.md — salpyeobom-backend AI 런타임 설정

> 이 파일은 AI 에이전트가 이 프로젝트에서 작업할 때마다 자동으로 적용되는 런타임 설정입니다.
> 프롬프트에 매번 반복할 필요 없이, 여기 정의된 규칙이 항상 유효합니다.

---

## 프로젝트 개요

**살펴봄(salpyeobom)** 은 고령자 원격 모니터링 백엔드 API입니다.

| 항목 | 값 |
|------|----|
| 프레임워크 | FastAPI (async) |
| ORM | Tortoise ORM + asyncpg |
| DB | PostgreSQL |
| 마이그레이션 | Aerich |
| 인증 | JWT (python-jose, HS256) + bcrypt |
| 패키지 관리 | uv |
| Python | 3.11+ |
| 테스트 | pytest + pytest-asyncio (SQLite in-memory) |
| 린터/포매터 | ruff |
| 타입 체킹 | mypy |
| 이메일/PDF | Resend API + LibreOffice(`soffice`) headless (.docx→PDF 변환) |
| 프론트엔드 | 정적 HTML/CSS/Vanilla JS — 백엔드가 `frontend/` 를 `/` 에 마운트해 함께 서빙 |

> **앱의 전체 그림**: 단순 CRUD API 가 아니다. (1) ADL 원시 데이터(`adl_raw_records`)를
> 조회·집계하는 API, (2) 그 데이터로 위험예측 보고서(.docx)를 생성하고 PDF 로 변환해
> 이메일 발송하는 파이프라인, (3) 합성 데이터 생성·검증 파이프라인(`scripts/synthetic/`),
> (4) 복지사 대시보드 정적 프론트(`frontend/`)를 한 프로세스로 서빙한다. 자세한 흐름은
> 아래 **"데이터·보고서·이메일 파이프라인"** 섹션 참조.

---

## 절대 규칙 (위반 불가)

```
NEVER: raw SQL 사용 — 반드시 Tortoise ORM 쿼리 API만 사용
NEVER: .env 파일 직접 수정 — app/config.py의 Settings 클래스를 통해서만 접근
NEVER: DROP TABLE, DELETE FROM (조건 없이), TRUNCATE 실행
NEVER: git push --force 또는 --no-verify
NEVER: 테스트 없이 새 엔드포인트 추가
NEVER: 비밀키, 패스워드를 코드에 하드코딩
NEVER: aerich 마이그레이션 없이 모델 스키마 변경
```

---

## 아키텍처 패턴

### 레이어 구조 (반드시 준수)
```
요청 → Router (app/routers/) → Schema 검증 (app/schemas/)
     → Service (app/services/, app/core/email.py)   ← 비즈니스 로직
     → 모델 조회 (app/models/) → 응답
```

- **라우터** (`app/routers/`): HTTP 입출력만 (파라미터 파싱, 의존성, 상태코드). **비즈니스 로직 금지.**
- **서비스** (`app/services/`): 라우터에서 분리한 비즈니스 로직 — 필터 구성, 인메모리 집계/그룹핑/정렬, 변환. **순수 함수 위주**로 DB 없이 단위 테스트 가능하게 작성한다. (예: `services/adl_raw.py`, `services/adl_raw_transform.py`. 이메일/PDF 변환 로직은 `core/email.py` 에 위치.)
- **스키마** (`app/schemas/`): Pydantic 모델. 모든 입출력은 스키마를 통해. 도메인 범주형 값(예: `ActionStatus`)은 `app/models/enums.py` 의 `StrEnum` 이 단일 출처.
- **모델** (`app/models/`): Tortoise ORM 모델. DB 접근은 여기서만.
- **코어** (`app/core/`): 인증(`security.py`)·예외(`exceptions.py`)·의존성(`dependencies.py`)·이메일(`email.py`). 여기를 수정할 때는 신중하게.

> **로직을 어디에 둘지**: 라우터 함수가 길어지거나(쿼리 필터 분기, 루프 집계, 변환) DB 없이
> 테스트하고 싶은 순수 계산이 생기면 `app/services/` 로 빼낸다. `adl_raw` 라우터가 이 패턴의
> 레퍼런스다 — 라우터는 얇고, 필터/집계는 `services/adl_raw.py`, 1440분 배열 변환은
> `services/adl_raw_transform.py` 에 있다.

### 의존성 주입
- 인증이 필요한 엔드포인트: `Depends(get_current_user)` 사용 필수. 라우터 전체를 보호할 때는 `APIRouter(dependencies=[Depends(get_current_user)])` 로 묶는다 (`patients`·`adl_raw`·`reports` 가 이 방식).
- 인증 없는 공개 엔드포인트는 라우터 파일 상단에 주석으로 명시

### 응답 형식
- 성공: **`SuccessResponse[T]` 래퍼**(`app/schemas/common.py`)로 감싸 `{ "status": "success", "data": ... }` 형태로 반환하는 것이 신규 라우터의 표준이다 (`patients`·`adl_raw`·`reports`). 도메인 페이로드는 제네릭 `T` 스키마로 정의한다.
- 에러: `app/core/exceptions.py`의 커스텀 예외(`HTTPException` 상속) 사용. `app/main.py` 의 핸들러가 모든 에러를 `{ "status": "error", "message": ... }` 로 직렬화한다 (422 검증 오류 포함).

---

## 코딩 규칙

### 타입 어노테이션
```python
# 좋음
async def get_patient(patient_id: str, user: User = Depends(get_current_user)) -> PatientDetail:

# 나쁨
async def get_patient(patient_id, user=Depends(get_current_user)):
```

### ORM 쿼리
```python
# 좋음 — Tortoise ORM API 사용
patient = await Patient.get_or_none(patient_id=patient_id)
active = await Situation.filter(action_status__not="조치 완료").all()

# 절대 금지 — raw SQL
await conn.execute("SELECT * FROM patients WHERE ...")
```

### 새 엔드포인트 추가 패턴
1. `app/schemas/`에 요청/응답 Pydantic 스키마 먼저 정의 (응답은 `SuccessResponse[T]` 래핑 고려)
2. 비즈니스 로직(필터·집계·변환)이 있으면 `app/services/` 에 순수 함수로 분리하고 단위 테스트
3. `app/routers/`에 라우터 함수 구현 (얇게 — 입출력과 서비스 호출만)
4. `tests/`에 테스트 작성 (최소: 성공 케이스 + 인증 실패 케이스)
5. `poe check` 통과 확인 후 커밋

### DB 스키마 변경 패턴
> **모델/스키마 작업 전 `docs/database-schema.md` 를 먼저 읽을 것.** 4개 테이블의 구조·ERD·필드 의미가 한 문서에 정리되어 있어, `app/models/` 의 여러 파일을 일일이 열지 않아도 전체 스키마를 파악할 수 있다.

1. `app/models/`에서 모델 수정
2. `uv run aerich migrate` 실행 → `migrations/` 에 새 마이그레이션 파일 생성
3. `poe migrate` (= `aerich upgrade`) 실행 → 마이그레이션을 DB에 적용
4. `migrations/` 는 `.gitignore` 처리 — 커밋하지 않고 `app/models/` 의 모델 변경만 커밋
5. **`docs/database-schema.md`** 의 해당 테이블 표(필드/제약/관계)를 변경 내용에 맞게 갱신 후 `app/models/` 변경과 함께 커밋
   - `app/models/*.py` 를 편집하면 PostToolUse 훅이 이 문서 갱신을 자동으로 상기시킨다 (`.claude/settings.json`)

---

## 개발 워크플로우

태스크 러너는 [poethepoet](https://poethepoet.natn.io/) (`poe`). 정의는 `pyproject.toml`의 `[tool.poe.tasks]`.

```bash
# 최초 1회 (머신당) — Windows / WSL / Ubuntu 동일
uv tool install poethepoet

# 개발 시작 — 백엔드가 frontend/ 를 정적 서빙하므로 한 프로세스로 전체 앱(API+프론트)이 뜬다.
poe run             # API+프론트 모두 :8000 에서 실행 (auto-reload) — 로컬 DB(.env.local)
poe run-remote      # 동일하되 원격 DB(.env) 연결 (USE_REMOTE_DB=1)

# 코드 작성 후
poe fix             # ruff 자동 수정 (포맷 + 린트 autofix)
poe check           # 전체 품질 검사 (lint + format-check + typecheck + test)

# DB
poe migrate         # aerich upgrade — 마이그레이션 적용
poe load-derived    # data/derived/patients.jsonl → DB 적재 (멱등 upsert)

# 커밋 전
poe check           # 반드시 통과해야 커밋 가능 (pre-commit hook이 자동 검사)
```

> `poe`만 입력하면 사용 가능한 전체 태스크 목록이 출력된다.
> `uv tool install` 없이 쓰려면 `uv run poe <task>` 폴백도 가능 (이미 dev deps에 포함).
> 배포/서버 제어(`deploy`·`start`·`stop`·`status`·`logs`)는 Linux/systemd 전용.

---

## 라우터 / 엔드포인트

모든 prefix 는 `/api/v1/*`. `patients`·`adl_raw`·`reports` 는 라우터 전체가 인증 보호된다.

| 라우터 | prefix | 주요 경로 |
|--------|--------|----------|
| `auth` | `/api/v1/auth` | `POST /register`, `POST /login`, `GET /me` |
| `dashboard` | `/api/v1/dashboard` | `GET /summary` |
| `patients` | `/api/v1/patients` | `GET ""`, `GET /{id}/details` |
| `situations` | `/api/v1/situations` | `GET /active` |
| `adl_raw` | `/api/v1/adl-raw` | `GET ""`(목록·필터·페이지), `GET /recipients`, `GET /recipients/{id}/records`, `GET /{id}`(상세) |
| `reports` | `/api/v1/reports` | `GET ""`(보고서 목록·일자별 그룹+위험/주의/사망 집계), `GET /{id}/file`(PDF 인라인 서빙), `POST /email`(보고서 PDF 이메일 발송) |

그 외 모든 경로(`/`, `index.html`, `css/*`, `js/*`)는 `frontend/` 정적 파일로 서빙된다
(`app/main.py` 의 `StaticFiles` 마운트). OpenAPI 문서: `http://localhost:8000/docs`.

---

## 데이터·보고서·이메일 파이프라인

이 백엔드는 CRUD 외에 오프라인 파이프라인을 포함한다. 코드 작업 시 어느 단계인지 먼저 파악할 것.

1. **합성 데이터 생성** (`scripts/synthetic/`, 오프라인):
   `scenario_gen.py`(페르소나+60일 시나리오) → `expander.py`(1440분 배열+스칼라로 확장,
   `adl_raw_records` 스키마에 맞춤) → `run_batch.py`(N명×3클래스 배치 → JSONL 또는 DB) →
   `validate_batch.py`(실데이터 대비 KS 분포 검증). 합성 식별자는 `SYN-{응급|사망|평소}-NNNNN`.
2. **파생 메타 적재** (`scripts/load_derived.py`): `adl_raw_records` 에서 오프라인 1회 파생해
   고정한 `data/derived/patients.jsonl` 을 `Patient`·`Situation` 테이블로 멱등 적재.
   (런타임 시드 개념은 폐기됨 — `docs/database-schema.md` 참조.)
3. **보고서 생성** (`scripts/report_generate.py`): `adl_raw_records` 조회 → matplotlib 차트 →
   `python-docx` 위험예측보고서 `.docx` 를 `out/reports/` 에 생성.
4. **이메일 발송** (`POST /api/v1/reports/email` → `app/core/email.py`):
   `out/reports/` 의 `.docx` 를 **LibreOffice(`soffice`) headless** 로 PDF 변환 후 Resend API 로
   첨부 발송. 블로킹 변환·발송은 `anyio.to_thread` 로 오프로드. 경로 탈출(`../`)은 차단된다.
   → `soffice` 미설치 또는 Resend 키 미설정 시 502(`EmailSendFailed`).

---

## 파일 구조

```
salpyeobom-backend/
├── app/
│   ├── main.py              # FastAPI 앱 팩토리 (create_app) — 라우터 등록 + frontend/ 정적 마운트
│   ├── config.py            # 환경변수 설정 (Settings) — .env + .env.local 로드
│   ├── database.py          # Tortoise ORM 초기화 + 모델 등록(MODELS)
│   ├── core/
│   │   ├── dependencies.py  # get_current_user 의존성
│   │   ├── exceptions.py    # 커스텀 HTTP 예외 (인증/리포트/이메일)
│   │   ├── security.py      # JWT + bcrypt
│   │   └── email.py         # 보고서 .docx→PDF 변환 + Resend 이메일 발송 (비즈니스 로직)
│   ├── models/
│   │   ├── user.py          # User 모델
│   │   ├── patient.py       # Patient, Situation
│   │   ├── adl_raw.py       # AdlRawRecord (ADL 원시 샘플 + 합성 데이터)
│   │   └── enums.py         # 도메인 범주형 StrEnum (ActionStatus 등) — 단일 출처
│   ├── routers/             # HTTP 엔드포인트 (얇게 — 입출력만)
│   │   ├── auth.py          # POST /register, POST /login, GET /me
│   │   ├── dashboard.py     # GET /summary
│   │   ├── patients.py      # GET "", GET /{id}/details
│   │   ├── situations.py    # GET /active
│   │   ├── adl_raw.py       # GET "", /recipients, /recipients/{id}/records, /{id}
│   │   └── reports.py       # POST /email (보고서 PDF 이메일 발송)
│   ├── services/            # 비즈니스 로직 (라우터에서 분리한 순수 함수)
│   │   ├── adl_raw.py       # 필터 구성 + 인메모리 집계/그룹핑/정렬
│   │   └── adl_raw_transform.py  # 1440분/24시간 배열 변환·재집계
│   └── schemas/             # Pydantic 스키마 (입출력 계약) — common.py 에 SuccessResponse[T]
├── frontend/                # 정적 복지사 대시보드 (index.html, css/, js/) — 백엔드가 / 에 서빙
├── tests/
│   ├── conftest.py          # pytest fixtures (client, auth_client)
│   └── test_*.py            # 엔드포인트·서비스·보안·UAT 테스트
├── scripts/
│   ├── *.sh                 # install/deploy/start/stop/status (Linux/systemd)
│   ├── load_derived.py      # data/derived/patients.jsonl → DB 적재 (멱등 upsert)
│   ├── seed_users.py        # 데모 계정 시드 (admin/admin1234, 멱등)
│   ├── report_generate.py   # adl_raw_records → 차트 + 위험예측보고서 .docx (out/reports/)
│   ├── report_to_docx.py    # 마크다운 → .docx 변환 (참고용 대안 포맷)
│   └── synthetic/           # 합성 데이터 파이프라인 (scenario_gen→expander→run_batch→validate_batch)
├── data/derived/            # patients.jsonl — 오프라인 1회 생성한 파생 메타 아티팩트 (커밋됨)
├── out/                     # 산출물 — reports/(.docx,PDF,차트), synthetic/(batch.jsonl) (gitignore)
├── prompts/                 # 보고서/합성 생성용 LLM 프롬프트 템플릿
├── notebooks/               # ADL 데이터 적재·검증·분석 노트북
├── docs/
│   └── database-schema.md   # DB 스키마 레퍼런스 (4개 테이블 + ERD + 필드 의미)
├── migrations/              # aerich 마이그레이션 (.gitignore 처리 — git 추적 안 함)
├── CLAUDE.md                # 이 파일 — AI 런타임 설정
├── AGENTS.md                # AI 에이전트 작업 가이드
├── pyproject.toml           # 의존성 + 도구 설정 + poe 태스크
└── .pre-commit-config.yaml  # pre-commit 훅
```

---

## 환경 변수

`.env` 파일을 직접 읽거나 수정하지 말 것. 항상 `app/config.py`의 `settings` 객체를 사용:

```python
from app.config import settings

db_url = settings.DATABASE_URL
secret = settings.SECRET_KEY
api_key = settings.RESEND_API_KEY
```

### 로드 우선순위 (`app/config.py`)
- 기본: `.env`(원격/기본) → `.env.local`(로컬 개발용) 순으로 로드, **뒤 파일이 우선** → 로컬 DB.
- `USE_REMOTE_DB=1` 이면 `.env.local` 을 건너뛰고 `.env` 만 로드 → 원격 DB (`poe run-remote` 가 이 변수를 설정).

### 주요 설정 키
| 키 | 용도 |
|----|------|
| `DATABASE_URL` | PostgreSQL 연결 (`postgres://...`) |
| `SECRET_KEY` / `ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT |
| `CORS_ORIGINS` | 쉼표 구분 허용 Origin 목록 (`main.py` 가 localhost↔127.0.0.1 자동 확장) |
| `RESEND_API_KEY` | 보고서 이메일 발송용 Resend API 키 ([resend.com/api-keys](https://resend.com/api-keys)) |
| `RESEND_FROM` | 발신 주소 (도메인 인증 전에는 계정 소유자 본인에게만 발송 가능) |

`.env.example`을 참고해 새 환경변수를 추가할 때는 반드시 `Settings` 클래스와 `.env.example` 을 함께 업데이트.

---

## 테스트 작성 기준

- **테스트 DB**: SQLite in-memory (PostgreSQL이 없어도 로컬 실행 가능)
- **픽스처**: `conftest.py`의 `client` (비인증), `auth_client` (인증됨) 사용
- **커버리지 기준**: 70% 이상 (CI에서 강제)
- **최소 테스트 케이스**:
  - 성공 응답 (200/201)
  - 인증 실패 (401) — 보호된 엔드포인트
  - 잘못된 입력 (422) — 필요한 경우

---

## 금지 패턴 요약

| 하면 안 되는 것 | 대신 할 것 |
|----------------|------------|
| raw SQL | Tortoise ORM `.filter()`, `.get()`, `.create()` |
| 하드코딩 비밀값 | `settings.secret_key` |
| `print()` 디버깅 | logger 사용 또는 제거 |
| 마이그레이션 없는 모델 변경 | `uv run aerich migrate` 로 생성 후 `poe migrate` 로 적용 |
| 테스트 없는 엔드포인트 | 반드시 `tests/test_*.py` 작성 |
| `git push --force` | PR + 리뷰 |
