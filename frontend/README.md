# 살펴봄 행정망 — 웹 프론트엔드

지자체 취약계층 안전 관리 시스템의 관제 대시보드입니다.  
담당자(공무원·복지사)가 로그인 후 실시간 상황을 모니터링하고, 대상자 상세 정보를 조회하며, 조치를 기록합니다.

---

## 프로젝트 구조

```
web_salpyobom/
├── index.html       # 전체 UI (로그인 + 대시보드)
├── css/
│   └── style.css    # 커스텀 스타일 (Tailwind 보조)
└── js/
    ├── data.js      # API 클라이언트 (서버 통신 전담)
    └── app.js       # UI 로직 (렌더링, 이벤트, 상태 관리)
```

### 파일별 역할

#### `js/data.js` — API 클라이언트
서버와의 모든 HTTP 통신을 담당합니다. `app.js`는 이 파일의 `API` 객체만 사용합니다.

```
API_BASE       서버 주소 상수. 서버 URL이 바뀌면 여기만 수정.
buildHeaders() 로그인 토큰이 있으면 자동으로 Authorization 헤더 추가.
apiRequest()   fetch 래퍼. 응답이 ok가 아니면 throw.
API            각 엔드포인트를 메서드로 노출한 객체.
```

새 API 엔드포인트가 생기면 `API` 객체에 메서드 한 줄만 추가하면 됩니다.

#### `js/app.js` — UI 로직
크게 5개 섹션으로 구성됩니다.

| 섹션 | 역할 |
|------|------|
| **상수** (`CATEGORY_BADGE`, `ALERT_THEMES`) | 뱃지·알림 색상 설정. 스타일 변경 시 여기만 수정. |
| **인증** (`initAuth`, `handleLogin`, `handleSignup`) | 로그인·회원가입 폼 처리 |
| **대시보드** (`showDashboard`, `loadDashboardSummary`, `loadActiveSituations`) | 로그인 성공 후 데이터 로드 |
| **상황 테이블** (`renderSituationsTable`, `situationRow`) | 활성 상황 목록 렌더링 |
| **환자 상세** (`loadPatientDetail`, `renderDetailPanel`) | 우측 상세 패널 |
| **DOM 유틸** (`el`, `val`, `setText`, `on`, ...) | 반복 DOM 코드를 짧게 줄인 헬퍼 |

#### `index.html`
두 개의 레이어로 구성됩니다.

- `#login-screen` — 초기 로그인/회원가입 화면 (기본 표시)
- `#dashboard-wrap` — 대시보드 전체 (로그인 성공 시 표시)

JS가 두 레이어의 `display`를 직접 전환합니다. 서버사이드 렌더링 없이 순수 정적 파일로 동작합니다.

---

## 로컬 실행 방법

별도 빌드 과정 없이 정적 파일 서버만 있으면 됩니다.

```bash
# 방법 1: npx serve
cd web_salpyobom
npx serve -l 8080

# 방법 2: VS Code Live Server 확장
# index.html 열고 우측 하단 "Go Live" 클릭 → localhost:5500 자동 실행
```

> **주의:** `file://` 프로토콜로 직접 열면 CORS 오류가 발생합니다. 반드시 로컬 서버를 통해 접속하세요.

---

## API 연동

백엔드 서버: `http://salpyeobom.kro.kr:8000`  
API 문서(Swagger): `http://salpyeobom.kro.kr:8000/docs`

### 현재 연동된 엔드포인트

| 메서드 | 경로 | 용도 |
|--------|------|------|
| POST | `/api/v1/auth/register` | 회원가입 |
| POST | `/api/v1/auth/login` | 로그인 → JWT 토큰 발급 |
| GET  | `/api/v1/auth/me` | 로그인 사용자 정보 조회 |
| GET  | `/api/v1/dashboard/summary` | 상단 통계 카드 (응급/경고/정상 건수) |
| GET  | `/api/v1/situations/active` | 실시간 상황 목록 |
| POST | `/api/v1/situations/{id}/actions` | 조치 등록 (유선 연락 / 업무 일지) |
| GET  | `/api/v1/patients/{id}/details` | 환자 상세 정보 |

### 인증 방식
로그인 성공 시 JWT 토큰을 `sessionStorage`에 저장합니다.  
탭을 닫으면 세션이 만료되어 재로그인이 필요합니다.

### CORS
로컬 개발 시 백엔드에서 `localhost:5500` (또는 사용하는 포트)을 허용해줘야 합니다.  
백엔드 팀에 요청하거나, 개발 중에는 브라우저 확장 프로그램 **"Allow CORS"** 로 임시 우회할 수 있습니다.

---

## 현재 구현된 기능

- [x] 회원가입 / 로그인 / 로그아웃
- [x] 대시보드 통계 카드 (응급·경고·정상 건수 실시간 표시)
- [x] 실시간 상황 목록 테이블 (카테고리 뱃지, 진행 상태 표시)
- [x] 환자 상세 정보 패널 (클릭 시 우측에 표시)
- [x] 조치 등록 — 유선 연락 / 업무 일지 기록
- [x] 실시간 시계

---

## 앞으로 구현할 기능

사이드바 메뉴에 항목은 있지만 아직 연결되지 않은 페이지들입니다.

#### 관제 리스트 (`/api/v1/patients`)
전체 대상자 목록을 페이지네이션으로 조회하는 화면.  
API는 `page`, `limit`, `search_name` 파라미터를 지원합니다.

#### 지역별 상황판
지도 위에 대상자 위치와 상태를 시각화하는 화면.  
지도 라이브러리(카카오맵, Leaflet 등) 연동이 필요합니다.

#### 대상자 DB 관리
대상자 등록·수정·삭제 기능. 백엔드 API 추가 필요.

#### 보고서 생성
기간별 상황 이력을 PDF 또는 Excel로 내보내기. 백엔드 API 추가 필요.

#### 알림 기능
헤더의 벨 아이콘에 실제 알림 연결.  
웹소켓 또는 주기적 폴링으로 신규 상황 발생 시 알림을 표시합니다.

#### 환자 타임시리즈 차트
API에 `/api/v1/patients/{id}/timeseries`가 이미 구현되어 있습니다.  
`mae_score`(이상 감지 점수) 변화를 꺾은선 그래프로 보여주는 기능을 상세 패널에 추가할 수 있습니다.  
Chart.js 등 차트 라이브러리 연동이 필요합니다.

---

## 기술 스택

| 항목 | 내용 |
|------|------|
| 언어 | HTML / CSS / Vanilla JavaScript (빌드 도구 없음) |
| CSS 프레임워크 | Tailwind CSS (CDN) |
| 아이콘 | Font Awesome 6 |
| 폰트 | Noto Sans KR |
| 통신 | Fetch API (axios 미사용) |
| 인증 | JWT Bearer Token (`sessionStorage` 저장) |

---

## 주요 ID 목록 (HTML ↔ JS 연결 참고)

| ID | 위치 | 용도 |
|----|------|------|
| `login-screen` | 로그인 화면 전체 래퍼 | JS에서 display 전환 |
| `dashboard-wrap` | 대시보드 전체 래퍼 | JS에서 display 전환 |
| `stat-emergency` / `stat-warning` / `stat-normal` / `stat-total` | 통계 카드 숫자 | API 응답으로 갱신 |
| `situations-tbody` | 상황 테이블 tbody | JS가 동적으로 행 생성 |
| `detail-*` | 우측 상세 패널 각 필드 | 환자 클릭 시 갱신 |
| `btn-action-call` / `btn-action-log` | 조치 버튼 | 클릭 시 API 호출 |
| `sidebar-username` / `sidebar-email` | 사이드바 사용자 정보 | 로그인 후 갱신 |
