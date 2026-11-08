# PostgreSQL Setup

PostgreSQL is the required database for local development, tests, and deployment. The repository does not enable pgvector; keyword search uses PostgreSQL full-text search, while the separate semantic route may use the configured embedding service and falls back to keyword search.

## Local development

1. Copy `.env.example` to `.env`.
2. Start the loopback-bound PostgreSQL service: `docker compose up -d postgres`.
3. Create the separate disposable test database once: `docker compose exec postgres createdb -U recall_atlas recall_atlas_test`.
4. Apply migrations from the repository root:

   ```powershell
   $env:PYTHONPATH = "backend"
   python -m alembic -c alembic.ini upgrade head
   ```

5. Run tests with `TEST_DATABASE_URL` pointed at `recall_atlas_test`. Pytest creates an isolated schema and drops it when the run finishes.
6. Start the API with `python -m uvicorn app.main:app --reload --app-dir backend`.

The Compose password is a local-development placeholder and the service binds only to `127.0.0.1`. Do not reuse it outside local development.

## Managed PostgreSQL

Provision PostgreSQL at the provider of choice, create the application database, and set `DATABASE_URL` from the provider's secret manager. Use TLS/provider-required connection options. Run Alembic migrations as a release step before starting API or worker processes. Configure a separate disposable PostgreSQL database for CI via `TEST_DATABASE_URL`; never point tests at production.

The historical `dev.db` is a nonempty SQLite database and has not been imported. Preserve it until a separate migration has copied and reconciled its rows and associated private files. Do not use SQLAlchemy `metadata.create_all` as a production schema-management substitute; Alembic is authoritative.

## Current deployment status

- PostgreSQL driver and versioned migrations are present.
- Offline Alembic generation against the PostgreSQL dialect has been verified.
- A live local PostgreSQL service was not available during the latest validation; run the full migration and test suite against PostgreSQL before deployment.
- pgvector and production embedding capacity remain unconfigured.
