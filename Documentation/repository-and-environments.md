# Repository Structure and Environment Strategy

## 1. Suggested repository layout

```text
recall-atlas/
├── apps/
│   └── web/                     # React + TypeScript PWA
├── services/
│   └── api/                     # FastAPI routes and application services
├── workers/
│   └── document_processor/      # Async extraction and indexing jobs
├── packages/
│   ├── shared-types/            # Shared API contracts where practical
│   └── ui/                      # Reusable UI components, if justified
├── migrations/                  # Database schema migrations
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   └── fixtures/
├── docs/                        # Product and engineering documentation
├── scripts/                     # Admin/maintenance scripts
├── infra/                       # Deployment and environment configuration
├── .env.example
├── README.md
└── CONTRIBUTING.md
```

This is a starting point. A monorepo is useful if the frontend, API, worker, and shared contracts need coordinated changes. Avoid overengineering packages before repeated reuse appears.

## 2. Environment separation

Maintain at least:
- local development;
- test/staging;
- production.

Use separate database and object-storage buckets or prefixes with distinct credentials. Do not use production user documents as casual test fixtures. Use sanitized, permission-cleared samples for extraction tests.

## 3. Configuration

Keep secrets in environment variables or a secret manager. Commit only `.env.example` with placeholder values. Configuration should cover:
- database connection;
- auth provider;
- object-storage endpoint and credentials;
- maximum file size;
- allowed MIME/extensions;
- queue configuration;
- OCR/vision provider settings;
- retry policy;
- notification provider;
- log level;
- retention windows;
- semantic search enablement;
- external AI fallback (off by default).

## 4. Development workflow

1. Create a task branch.
2. Update or add migrations.
3. Implement the smallest vertical slice.
4. Add unit and integration tests.
5. Run lint/type checks and tests.
6. Review security and authorization impacts.
7. Update API and product docs.
8. Deploy to staging.
9. Test using representative sample documents.
10. Promote only after acceptance criteria pass.

## 5. Schema and migration discipline

- Use versioned migrations.
- Test migrations against an empty database and a copy of representative test data.
- Back up before major production migrations.
- Keep rollback or forward-fix plans.
- Avoid manual production schema changes that are not represented in migrations.

## 6. Observability and debugging

Every job should have a stable job ID and document ID. Include correlation IDs across API, worker, database, and notification logs. Never log passwords, tokens, signed URLs, or unrestricted private document contents. Use structured error categories and sanitized context.

## 7. Durable files

Do not store uploaded files in the API service's ephemeral filesystem or as database blobs by default. Keep original files in object storage and record object identifiers/checksums in PostgreSQL. Generate derivatives reproducibly and treat them as derived assets.

The application supports a local filesystem adapter for development/tests and a private S3-compatible adapter for deployment. Set `STORAGE_BACKEND=s3`, `OBJECT_STORAGE_BUCKET`, and `OBJECT_STORAGE_REGION`; configure either workload identity or the object-storage endpoint and credentials using the environment variables in `.env.example`. The same bucket and credentials must be available to the API and every worker. Keep the bucket private with public access blocked; grant only the required object read/write/copy/delete permissions. Original keys are namespaced under `uploads/` and `quarantine/`, and PostgreSQL stores the object key, checksum, size, and document metadata.

PostgreSQL is the only supported application database, including local development and tests. The checked-in `compose.yaml` provides a loopback-only PostgreSQL 16 service; the backend and test suite do not fall back to SQLite. Non-local API startup additionally requires S3-compatible storage so uploads do not disappear with an API instance. Local development may use the private filesystem adapter. The current download and preview routes read files through the API and apply document authorization; do not make a bucket public or expose raw storage keys as URLs. Plan private, short-lived signed delivery only if file size or traffic makes API proxying a measured bottleneck.

Enable provider-side encryption and versioning where available. Back up the database and originals independently and verify object checksums during restore. Do not configure automatic expiration for uploaded originals until the retention policy is explicitly decided; orphan detection/cleanup and retention enforcement remain operational follow-up work.

For local development, start PostgreSQL with `docker compose up -d postgres`. Create a dedicated test database once with `docker compose exec postgres createdb -U recall_atlas recall_atlas_test`; set both `DATABASE_URL` and `TEST_DATABASE_URL` from `.env.example`. The backend and tests reject SQLite. Run schema migrations as a release step, before starting API/worker processes: from the repository root set `PYTHONPATH=backend` and `DATABASE_URL` to the PostgreSQL DSN, then run `python -m alembic -c alembic.ini upgrade head`. Pytest requires `TEST_DATABASE_URL` to a separate disposable PostgreSQL database whose name contains `test`; it creates and drops a unique schema per run. Run the API with `uvicorn app.main:app` and the separate processor with `python -m app.worker` from the backend working directory. Both processes must receive the same environment, database, and object-storage configuration.

The former `dev.db` is a legacy SQLite database, not an active application database. It contains user/session/document records and must not be deleted or treated as migrated. Import its data into PostgreSQL only through a separately verified migration procedure with a backup and row/checksum reconciliation; the application does not automatically copy SQLite records.
