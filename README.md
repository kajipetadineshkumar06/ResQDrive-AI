# ResQDrive_AI
AI-powered roadside assistance

ResQDrive AI is a vehicle-service and emergency assistance application. Its main components are a FastAPI backend, a React and TypeScript frontend, MySQL persistence, provider assignment and service-request workflows, route and ETA support, notifications, and an optional local Ollama integration.

## Project layout

- `backend/` contains the FastAPI application, authentication, service workflows, database access, and backend tests.
- `frontend/` contains the Vite application and customer-facing interface.
- `database/sql/migrations/` contains the SQL migration files currently present.
- `backend/ADMIN_BOOTSTRAP.md` documents the guarded first-admin bootstrap process.

## Prerequisites

- Python 3.10 or newer. The source uses modern Python type syntax; check the pinned dependencies against your chosen Python release.
- Node.js and npm compatible with the versions in `frontend/package-lock.json`.
- A disposable local MySQL database for backend development. Do not use production credentials or data for local setup.
- Ollama only when local AI diagnosis is enabled.

## Local setup

### Backend

From the `backend` directory:

1. Create and activate a virtual environment.
2. Install the dependencies with `python -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and configure it locally. Keep real credentials out of this repository.
4. Use a disposable database and verify its schema before starting the API. The migration set is incomplete; see [Known limitations](#known-limitations).
5. Start the development server with `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000` only when the database and scheduled background behavior are safe for local testing.

Backend configuration names include `APP_ENV`, `CORS_ALLOWED_ORIGINS`, `AUTO_CREATE_TABLES`, `DATABASE_URL`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `JWT_SECRET_KEY`, `ADMIN_JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `GOOGLE_MAPS_API_KEY`, `OLLAMA_ENABLED`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`, and `PROVIDER_TIMEOUT_SECONDS`. Use either `DATABASE_URL` or the separate `DB_*` settings according to the backend configuration. The templates contain development examples and placeholders; replace credential placeholders only in your local `.env` files.

`ADMIN_BOOTSTRAP_ENABLED` is a temporary opt-in for the documented first-admin bootstrap. Follow `backend/ADMIN_BOOTSTRAP.md` and disable the option after bootstrap.

### Frontend

From the `frontend` directory:

1. Install the locked dependencies with `npm ci`.
2. Copy `.env.example` to `.env` and configure `VITE_API_URL` locally.
3. Start the development server with `npm run dev -- --host 127.0.0.1`.

## Tests and build

From `backend`, run the backend test suite with:

```powershell
python -m unittest discover -s tests -v
```

From `frontend`, run the production build and the TypeScript build check with:

```powershell
npm run build
```

Both commands require their project dependencies. Keep tests on isolated local fixtures; do not use a production database or real service credentials.

## Known limitations

- Migration readiness is unverified. `database/sql/migrations/000_core_schema_baseline.sql` is a proposed baseline for 15 ORM tables, and `001_agent_events.sql` is the existing agent-events migration; neither has been executed or verified on MySQL. The deployed schema and migration history remain unknown. Do not treat automatic table creation as a production migration plan.
- No payment gateway integration is present in this project snapshot, so payment checkout and settlement are unavailable. Pricing or invoice code alone does not confirm that payment was collected.
- Firebase notification delivery requires Firebase Admin credentials. No service-account credential is included in this copy, and end-to-end delivery has not been verified.
- Google Maps routing requires a restricted backend key configured through `GOOGLE_MAPS_API_KEY`. No live API request or key validation was performed during publication preparation.
- Ollama is optional. If enabled, the configured local service and model must be available.
- Starting the backend may activate scheduled assignment or notification work. Use only a disposable database and controlled test data until those behaviors are reviewed.
- This project has not been verified as production-ready.

## Deployment configuration (not yet deployed)

### Vercel frontend

- Create the Vercel project with `frontend/` as its root directory.
- Use `npm run build` as the build command and `dist` as the output directory.
- Set the build-time variable `VITE_API_URL` to the backend's public HTTPS base URL. The production build rejects a missing or non-HTTPS value.
- `frontend/vercel.json` rewrites browser routes to `index.html`, so refreshing a React Router URL returns the SPA entry point.

### Railway backend

- Create the Railway service with `backend/` as its root directory. `backend/railway.toml` supplies the production Uvicorn command and `/health` health-check path; the command binds to `0.0.0.0` and Railway's injected `PORT`, without reload mode.
- The Railway start command sets `APP_ENV=production`. Configure `CORS_ALLOWED_ORIGINS` (the exact Vercel HTTPS origin), `DATABASE_URL` or all of `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`, `JWT_SECRET_KEY`, and `ADMIN_JWT_SECRET_KEY`. Keep `AUTO_CREATE_TABLES` unset or false; production rejects true. Use distinct, strong signing secrets. `GOOGLE_MAPS_API_KEY` is needed if Google Maps routing is enabled.
- Production startup requires an explicit `SCHEDULER_ENABLED` choice. For an initial single Railway API replica, set it to true so automatic assignment, timeout recovery, and scheduled notifications continue. Do not scale the API to multiple replicas: the scheduler is process-local, so replicas would duplicate jobs. Setting it false disables those jobs; this project does not yet provide a separate scheduler service or distributed job lock.
- Set `REDIS_URL` to a deployment Redis URL if the RQ background-job endpoints are used. Without it, the existing local-development fallback remains `localhost:6379`. The RQ worker is a separate process (`python -m workers.worker`) and must also be provisioned if queued jobs are used; no Railway worker service is configured here.

Firebase push delivery is not ready for deployment in this snapshot: messaging calls exist, but no Firebase Admin app/credential initialization was found. Google Maps and Ollama remain separately configured optional integrations. Database schema and migration execution must be verified in disposable staging before deployment; `/health` is liveness-only and does not verify database readiness.
