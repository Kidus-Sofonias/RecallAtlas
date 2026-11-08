# Recall Atlas frontend

React, TypeScript, Vite, and React Router provide the responsive archive interface. The frontend uses the existing API routes and deliberately omits workflows for which the backend has no supported contract.

## Local development

From the repository root, copy `.env.example` to `.env`. Set `APP_ENV=development`. To create a local administrator, set both `ADMIN_EMAIL` and `ADMIN_INITIAL_PASSWORD` in `.env`; startup bootstraps that account once. Apply database migrations, then start FastAPI:

```powershell
$env:PYTHONPATH = "backend"
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --app-dir backend
```

Then run the frontend:

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run dev
```

During development, Vite proxies `/api` requests to `http://127.0.0.1:8000`. The API's cookie-based session and CSRF protection expect same-site frontend/API hosting; use a same-origin reverse proxy in deployment. `VITE_API_BASE` may be used only when the browser can send credentials and read the CSRF cookie under the configured origin policy. Frontend environment variables are public build-time values; never put credentials or other backend secrets in a `VITE_*` variable.

In development, users can register and are signed in immediately without email delivery. Admin accounts are created only from the backend `.env` bootstrap settings; public signup cannot create an admin. For production email verification and password reset, configure Resend and set `EMAIL_DEV_MODE=false`. See [Authentication and Administrator Security](../Documentation/authentication-and-admin-security.md) for bootstrap and deployment requirements.

## Checks

```powershell
npm.cmd run lint
npm.cmd run build
```

## Current API-backed pages

- Home discovery feed: `GET /api/v1/discovery`, optionally matched to the user's onboarding grade
- Indexed Explore search with question, paper, and article results: `GET /api/v1/search/explore?q=...&grade=...&subject_id=...`
- Keyboard-accessible autocomplete: `GET /api/v1/search/suggestions?q=...`
- Grade and subject recommendations: `GET/PATCH /api/v1/auth/preferences`
- Published article reading and admin-authoring: `GET/POST /api/v1/resources` and `GET /api/v1/resources/{resource_id}`
- Upload and automatic extraction: `POST /api/v1/uploads/initiate` and `POST /api/v1/uploads/{document_id}/complete`
- Question detail: `GET /api/v1/questions/{question_id}`
- Document metadata and extracted questions: `GET /api/v1/documents/{document_id}` and `GET /api/v1/documents/{document_id}/questions`
- Collection list/create: `GET /api/v1/collections` and `POST /api/v1/collections`
- Bookmark list/add/remove: `GET`, `POST`, and `DELETE /api/v1/bookmarks`
- Notification list: `GET /api/v1/notifications`
- Administrator question review: `GET /api/v1/admin/question-review-queue` and `POST /api/v1/questions/{question_id}/review`

The API provides self-hosted email/password sign-in, registration, verification, reset, and logout. Original-file downloads and PDF/image page previews require uploader or administrator access. Notification read mutations and collection item listing are not yet available.

Document uploads accept PDF, DOCX, PPTX, and supported raster images (PNG, JPEG, TIFF, BMP, and WebP), with grade and exam-year metadata. Completion automatically queues local extraction/OCR. Extracted questions remain held until reviewed. Original downloads and PDF/image page previews are restricted to the uploader and administrators; public discovery lists only reviewed questions from completed documents. A signed-in user's selected grade powers the matching home section and can be changed from Account.

Explore uses the indexed lexical backend, debounces suggestions, and personalizes matching results with the selected grade (plus one grade below) and subject interests. Article authoring is available through the administrator-protected API; there is not yet a frontend admin article editor.

## Security status

The backend enforces authenticated request identity, cookie/CSRF checks, and administrator/ownership guards. Non-local startup requires a strong `SECRET_KEY` and a bootstrapped administrator. MFA, distributed rate limiting, audit logging, and private original-file access remain release blockers; review the linked authentication guide before deployment.
