# Recall Atlas — Engineering Status

Status reflects the implementation and documentation audit on 2026-11-07. Planned documentation is not evidence that a feature exists.

## Architecture verified

- Frontend: React 19, TypeScript, Vite, React Router 7.
- Backend: FastAPI with SQLAlchemy.
- Database: PostgreSQL is the only supported application, development, migration, and test database. SQLite runtime search has been removed. The active local `.env` and `.env.example` target PostgreSQL; the legacy, data-bearing `dev.db` is retained for a separate, verified import and has not been migrated.
- Deployment storage: a private S3-compatible adapter is supported and required outside development/test. Local development/tests use private filesystem storage.
- Data: PostgreSQL-compatible UUID models and an initial Alembic migration are present; pgvector is not the active embedding storage implementation.
- Search: `/api/v1/search?q=...` uses PostgreSQL full-text search. A separate hybrid route attempts embeddings; keyword search remains available. pgvector is not the active embedding store.
- Uploads: FastAPI upload initiation/completion routes persist private files using local storage in development or S3-compatible storage in deployment, then enqueue processing records.
- Email: Resend configuration and an email service exist.
- Runtime safety: non-local API startup requires a strong `SECRET_KEY` and an existing or safely bootstrapped administrator.
- Authentication: self-hosted email/password registration and verification, scrypt password hashing, 14-day revocable server-side sessions, logout, password reset, CSRF/origin checks, and request-scoped user/admin dependencies are implemented.
- Tests: pytest requires a dedicated PostgreSQL database and isolates each run in a disposable schema. The previous full suite passed against SQLite before this PostgreSQL-only test switch; this environment has no PostgreSQL server/CLI/container runtime, so the suite has not yet been rerun against PostgreSQL. No repeatable frontend/browser test framework is configured.

## Project tracker

| Area | Status | Evidence and remaining work |
|---|---|---|
| Responsive visual system and application shell | COMPLETE | Shared design tokens, desktop navigation, mobile navigation, page states, and Recall Atlas styling are implemented in `frontend/src`. Production build and lint pass. |
| Homepage and question search | COMPLETE | Homepage submits a query to the existing search route; result links preserve the query in the URL and show available source document/page references. |
| Question reading and source provenance | PARTIAL | Question text, quality status, page, and document ID are shown. Keyword/hybrid search and document question lists filter out held questions. Authorized source preview/download routes are implemented. |
| Collections | PARTIAL | Listing and creation use the existing API. Collection item retrieval, item addition/removal UI, editing, and deletion are not implemented by the current API. |
| Bookmarks | PARTIAL | Search/detail can add and remove bookmarks; the library can list and remove them. The previously unmounted router is now registered and covered by backend integration assertions. The API returns identifiers only, not descriptive item metadata. |
| Notifications | PARTIAL | Existing notification list is displayed. Read-state mutation and timestamps/destinations are not returned by the API. |
| Profile and account flows | PARTIAL | Login, registration, email verification, password reset, session lookup, logout, profile editing, and deletion requests with admin review are implemented. Approved deletion anonymizes account identifiers and removes private associations while retaining contribution records and source documents. Retention and legal policy approval are still required. Registration/reset require configured email delivery. |
| Admin authorization | COMPLETE (API) | Admin overview, backup, moderation, processing, taxonomy writes, embeddings, user/role endpoints, and deletion-request review require an authenticated administrator. Audit events currently cover account-deletion request/review only; broader administrator-action coverage remains. |
| Administrator bootstrap | COMPLETE | `ADMIN_EMAIL` and `ADMIN_INITIAL_PASSWORD` seed an administrator only when none exists; a database lock serializes concurrent startup attempts, and subsequent startup never resets the password. Non-local startup also requires a strong `SECRET_KEY`. |
| Upload interface | PARTIAL | Upload initiation requires identity and completion is owner/admin-scoped. Private preview/download routes are implemented; frontend upload remains unavailable. |
| PostgreSQL application/test support | IMPLEMENTED; LIVE VALIDATION PENDING | PostgreSQL is the default and only accepted application/migration/test database. Tests isolate in a dedicated PostgreSQL schema. The full migration chain generates PostgreSQL SQL, but a live PostgreSQL migration/test run is still required. |
| Existing local database migration | NOT DONE; PRESERVED | `dev.db` contains user/session/document records and is intentionally ignored by Git. It has not been copied to PostgreSQL; do not delete until a verified import and file-checksum reconciliation are complete. |
| Private durable file storage | PARTIAL | Local filesystem is development/test only. A private S3-compatible adapter is implemented and non-local startup requires it. Configure a bucket/credentials, backups, and lifecycle/retention operations before deployment. Existing private uploads remain preserved locally. |
| Physics/math source review | PARTIAL | Physics vector/force notation and ambiguous angle strings are flagged for original-source review when a page has visuals; broader diagram/formula accuracy still needs a measured benchmark. |
| Private data authorization | COMPLETE (implemented routes) | Bookmarks, collections, and notifications use the authenticated request user; collection and bookmark access is owner-scoped. Revisit authorization as new routes are added. |
| Environment sample and secret hygiene | PARTIAL | `.env` is ignored and untracked. `.env.example` contains local PostgreSQL placeholders; use a secret manager and rotate any credential previously exposed in tracked files if it was live. |
| Backup and restore | NOT IMPLEMENTED | The administrator backup endpoint returns HTTP 501 rather than generating a misleading SQLite-only archive. Configure and verify PostgreSQL and private-file backups before deployment. |
| Frontend end-to-end tests | MISSING | A one-off integrated-browser smoke run covered search, bookmark add/remove, collection creation, notifications, question detail, and document detail using isolated records. No repeatable Playwright/equivalent suite is configured. |
| Local API integration | COMPLETE | Vite proxies `/api` to the local FastAPI origin, avoiding cross-origin configuration for local development. |
| Backend test-data isolation | IMPLEMENTED; LIVE VALIDATION PENDING | Pytest requires a dedicated PostgreSQL database, creates a uniquely named temporary schema, and drops it after the run. The current environment has no PostgreSQL service to execute this configuration. |
| Non-local API startup safety | COMPLETE | Non-local startup requires a strong secret and an existing or safely bootstrapped administrator. |
| Embedding worker production capacity | BLOCKED | Existing project roadmap blocker; no production worker RAM decision was made. |
| Real-user pilot | BLOCKED | Not run. |
| Legal review | BLOCKED | Terms, privacy, and copyright processes remain subject to legal review. |

## Deployment and functional findings

1. **PostgreSQL and deployment services are not live-validated.** The app defaults to PostgreSQL and rejects SQLite, but no local PostgreSQL service is installed/running here. Production also requires a private S3-compatible bucket.
2. **Production authentication operations need deployment controls.** Rate limiting is process-local and there is no MFA or audit log for sensitive administrator actions. Add distributed limits and operational audit logging before public launch.
3. **Email-based account flows require provider configuration.** Registration and password reset are unavailable while `EMAIL_DEV_MODE=true` or Resend is not configured.
4. **Medium — Collections API is incomplete.** Collection item retrieval and mutation/deletion flows remain unavailable.
5. **Uploaded-file lifecycle still needs operations.** Originals are kept private and outside PostgreSQL; retention/expiration and orphan cleanup are not automatic. Do not set bucket expiration until a retention policy has been decided.
6. **High — Account-deletion retention policy needs legal approval.** Approval currently anonymizes profile identifiers and removes private associations, but retains contribution records and source documents. Define retention and backup-expiry requirements before using this flow with real accounts.

## Release-readiness checklist

- [x] Select and implement a self-hosted authentication/session system.
- [x] Enforce authenticated ownership on bookmarks, collections, notifications, and uploads.
- [x] Enforce administrator authorization on sensitive API routes.
- [x] Add safe idempotent administrator initialization and password recovery.
- [x] Filter keyword/hybrid search, question detail, and document question lists to reliable/published questions; add held-content regression assertions.
- [x] Add permission regression tests for sessions, admin denial, and user isolation.
- [x] Add profile editing, account-deletion requests, admin decisions, anonymization, and deletion audit records.
- [x] Implement authorized private original-document preview/download; files are served through authenticated API routes rather than public or permanent signed URLs.
- [x] Require PostgreSQL and private S3-compatible storage at non-local API/worker startup; render the Alembic chain as PostgreSQL SQL.
- [x] Keep document originals outside PostgreSQL and support local filesystem storage only for development/tests.
- [x] Keep extraction worker runnable as `python -m app.worker`.
- [x] Make PostgreSQL the only application, development, migration, and test database; require a dedicated PostgreSQL test DB with per-run schema isolation.
- [x] Provide a loopback-only PostgreSQL 16 Compose service for local setup.
- [ ] Run migrations and integration tests against a reachable PostgreSQL service.
- [ ] Import and reconcile the preserved legacy `dev.db` records and associated original files.
- [ ] Configure production PostgreSQL, private object bucket/credentials, strong secret, admin bootstrap, and email delivery.
- [ ] Add object orphan detection, retention enforcement, backup/restore verification, and bucket lifecycle rules after retention is decided.
- [ ] Complete collection contents and upload status workflows.
- [ ] Add browser end-to-end tests with isolated test data.
- [ ] Add distributed authentication rate limiting, administrator MFA, and security audit logging.
- [ ] Approve account-deletion, contribution-retention, and backup-expiry policies before processing real requests.
- [ ] Decide production embedding-worker RAM/capacity.
- [ ] Complete restore testing, the real-user pilot, and legal review.

## Local development

From the repository root, install backend dependencies, copy `.env.example` to `.env`, start PostgreSQL, create a separate test database, apply migrations, then start the API:

```powershell
Copy-Item .env.example .env
docker compose up -d postgres
docker compose exec postgres createdb -U recall_atlas recall_atlas_test
$env:PYTHONPATH = "backend"
python -m alembic -c alembic.ini upgrade head
python -m uvicorn app.main:app --reload --app-dir backend
$env:TEST_DATABASE_URL = "postgresql+psycopg2://recall_atlas:local-dev-only@127.0.0.1:5432/recall_atlas_test"
python -m pytest backend/tests -q
```

In another terminal:

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run dev
npm.cmd run lint
npm.cmd run build
```

Set `VITE_API_BASE` only to the API origin. Do not place backend credentials in `VITE_*` variables. Change the local-only PostgreSQL credentials before exposing the database beyond loopback. `TEST_DATABASE_URL` must point to a dedicated disposable PostgreSQL database whose name contains `test`; it must never point to production. Production remains blocked until live PostgreSQL migrations/tests, object storage, scanner operation, and backup/restore checks are complete.
