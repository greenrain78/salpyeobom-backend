# Salpyeobom Frontend

Next.js 15 (App Router) + TypeScript + Tailwind CSS v4 + shadcn/ui.

Companion to the FastAPI backend in this repo.

## Quick start

```bash
# 최초 1회
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_BASE_URL 조정 필요시
npm install
```

이후에는 프로젝트 루트에서 **`uv run python dev.py`** 한 번으로 백엔드(`:8000`)와
프론트엔드(`:3000`)를 함께 띄우는 것이 가장 편합니다. Ctrl+C 한 번이면 둘 다 정리됩니다.

프론트만 따로 띄우려면:

```bash
cd frontend
npm run dev    # → http://localhost:3000
```

백엔드는 `NEXT_PUBLIC_API_BASE_URL`(기본 `http://localhost:8000`)에서 가동되어야 합니다.
CORS 의 `http://localhost:3000` 허용은 `app/config.py` 에 이미 설정되어 있습니다.

## Scripts

- `npm run dev` — start dev server on :3000
- `npm run build` — production build
- `npm run start` — run production build
- `npm run lint` — ESLint (Next.js core-web-vitals + TS)
- `npm run typecheck` — `tsc --noEmit`

## Pages

- `/login`, `/register`
- `/` — dashboard (총 모니터링 인원)
- `/patients` — 환자 목록 + 검색 + 페이지네이션
- `/patients/[patientId]` — 환자 상세
- `/situations` — 활성 상황 + 조치 등록
