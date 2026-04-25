# Web App (Next.js MVP)

This app is the first control-room MVP for AI Parliament.

## Features in this increment

- Dashboard page to create debates quickly
- Debate details page with auto-refresh event timeline
- API integration against the FastAPI backend

## Run locally

1. Install dependencies:
   - `npm install`
2. Start dev server:
   - `npm run dev`
3. Open:
   - `http://localhost:3000`

## Environment variables

Set in `apps/web/.env.local` if needed:

- `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`)
- `NEXT_PUBLIC_TENANT_ID` (default `tenant-int-001`)
- `NEXT_PUBLIC_USER_ID` (default `web-user-1`)
- `NEXT_PUBLIC_USER_ROLE` (default `admin`)
