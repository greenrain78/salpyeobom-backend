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
| 인증 | JWT (python-jose, HS256) |
| 패키지 관리 | uv |
| Python | 3.11+ |
| 테스트 | pytest + pytest-asyncio (SQLite in-memory) |
| 린터/포매터 | ruff |
| 타입 체킹 | mypy |

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
요청 → Router (app/routers/) → Schema 검증 (app/schemas/) → 모델 조회 (app/models/) → 응답
```

- **라우터** (`app/routers/`): HTTP 엔드포인트만. 비즈니스 로직 금지.
- **스키마** (`app/schemas/`): Pydantic 모델. 모든 입출력은 스키마를 통해.
- **모델** (`app/models/`): Tortoise ORM 모델. DB 접근은 여기서만.
- **코어** (`app/core/`): 인증, 예외, 의존성. 여기를 수정할 때는 신중하게.

### 의존성 주입
- 인증이 필요한 엔드포인트: `Depends(get_current_user)` 사용 필수
- 인증 없는 공개 엔드포인트는 라우터 파일 상단에 주석으로 명시

### 응답 형식
- 성공: Pydantic 스키마 직접 반환 (FastAPI가 직렬화)
- 에러: `app/core/exceptions.py`의 커스텀 예외 사용
- 공통 래퍼가 필요하면 `app/schemas/common.py` 참조

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
patients = await Patient.filter(is_active=True).all()

# 절대 금지 — raw SQL
await conn.execute("SELECT * FROM patients WHERE ...")
```

### 새 엔드포인트 추가 패턴
1. `app/schemas/`에 요청/응답 Pydantic 스키마 먼저 정의
2. `app/routers/`에 라우터 함수 구현
3. `tests/`에 테스트 작성 (최소: 성공 케이스 + 인증 실패 케이스)
4. `make check` 통과 확인 후 커밋

### DB 스키마 변경 패턴
1. `app/models/`에서 모델 수정
2. `uv run aerich migrate` 실행 → `migrations/` 에 새 마이그레이션 파일 생성
3. `make migrate` (= `aerich upgrade`) 실행 → 마이그레이션을 DB에 적용
4. `migrations/` 는 `.gitignore` 처리 — 커밋하지 않고 `app/models/` 의 모델 변경만 커밋

---

## 개발 워크플로우

```bash
# 개발 시작
make dev            # 개발 서버 실행

# 코드 작성 후
make fix            # ruff 자동 수정 (포맷 + 린트 autofix)
make check          # 전체 품질 검사 (lint + typecheck + test)

# 커밋 전
make check          # 반드시 통과해야 커밋 가능 (pre-commit hook이 자동 검사)
```

---

## 파일 구조

```
salpyeobom-backend/
├── app/
│   ├── main.py              # FastAPI 앱 팩토리 (create_app)
│   ├── config.py            # 환경변수 설정 (Settings)
│   ├── database.py          # Tortoise ORM 초기화
│   ├── core/
│   │   ├── dependencies.py  # get_current_user 의존성
│   │   ├── exceptions.py    # 커스텀 HTTP 예외
│   │   └── security.py      # JWT + bcrypt
│   ├── models/
│   │   ├── user.py          # User 모델
│   │   └── patient.py       # Patient, Situation, SituationAction, TimeseriesData
│   ├── routers/
│   │   ├── auth.py          # POST /register, POST /login, GET /me
│   │   ├── dashboard.py     # GET /summary
│   │   ├── patients.py      # GET /, GET /{id}/details, GET /{id}/timeseries
│   │   └── situations.py    # GET /active, POST /{id}/actions
│   └── schemas/             # Pydantic 스키마 (입출력 계약)
├── tests/
│   ├── conftest.py          # pytest fixtures (client, auth_client)
│   └── test_*.py            # 엔드포인트별 테스트
├── scripts/                 # 배포/시드 스크립트
├── migrations/              # aerich 마이그레이션 (.gitignore 처리 — git 추적 안 함)
├── CLAUDE.md                # 이 파일 — AI 런타임 설정
├── AGENTS.md                # AI 에이전트 작업 가이드
├── pyproject.toml           # 의존성 + 도구 설정
├── Makefile                 # 개발 명령어
└── .pre-commit-config.yaml  # pre-commit 훅
```

---

## 환경 변수

`.env` 파일을 직접 읽거나 수정하지 말 것. 항상 `app/config.py`의 `settings` 객체를 사용:

```python
from app.config import settings

db_url = settings.DATABASE_URL
secret = settings.SECRET_KEY
```

`.env.example`을 참고해 새 환경변수를 추가할 때는 반드시 두 파일 모두 업데이트.

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
| 마이그레이션 없는 모델 변경 | `uv run aerich migrate` 로 생성 후 `make migrate` 로 적용 |
| 테스트 없는 엔드포인트 | 반드시 `tests/test_*.py` 작성 |
| `git push --force` | PR + 리뷰 |
