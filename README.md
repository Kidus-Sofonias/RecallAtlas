# Recall Atlas

Recall Atlas is a searchable archive of academic questions and their original source documents. It preserves source provenance and flags uncertain extraction rather than guessing at formulas, diagrams, or text.

## Project structure

- `frontend/` — React, TypeScript, and Vite application.
- `backend/` — FastAPI API, document processing, and PostgreSQL models.
- `Documentation/` — Product, engineering, security, and operations documentation.
- `docs/PROJECT_STATUS.md` — Implementation status and known release blockers.

## Local development

### Backend

1. Install Python dependencies from `requirements.txt`.
2. Copy `.env.example` to `.env` and set local configuration.
3. Start the local PostgreSQL service:

   ```powershell
   docker compose up -d postgres
   ```

4. Apply migrations and start the API from the repository root:

   ```powershell
   $env:PYTHONPATH = "backend"
   python -m alembic -c alembic.ini upgrade head
   python -m uvicorn app.main:app --reload --app-dir backend
   ```

### Frontend

From `frontend/`:

```powershell
npm install
npm run dev
npm run lint
npm run build
```

## Tests

Backend tests require a separate disposable PostgreSQL database. Set `TEST_DATABASE_URL` to that database; its name must contain `test`. The test harness creates a temporary schema for each run and removes it afterward.

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -q
```

## Deployment status

PostgreSQL is the only supported runtime database. See [the project status](docs/PROJECT_STATUS.md) and [the documentation index](Documentation/INDEX.md) for implemented features and remaining work. Live PostgreSQL validation, migration of the preserved local SQLite data, production object storage, malware-scanner operations, and backup/restore verification remain deployment prerequisites.

Never commit `.env`, local databases, private uploads, credentials, or locally supplied test documents.
