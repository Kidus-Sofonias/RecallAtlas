# System Architecture

## 1. Architecture goals

- Reliable end-to-end archive workflows.
- Clear separation between interactive API requests and long-running extraction jobs.
- Durable original-file storage outside the relational database.
- Multi-school data model.
- Replaceable AI/OCR providers.
- Observable queue, quota, and failure behavior.
- A free-first deployment plan with explicit limitations and migration paths.

## 2. Logical components

### Frontend
React + TypeScript responsive web app, installable PWA. Owns navigation, upload guidance, search UI, study tools, notifications, and admin console presentation. It does not enforce security by itself.

### API service
FastAPI/Python implementation. Handles authentication, authorization, metadata, uploads, search orchestration, comments, collections, reports, notifications, and admin endpoints. It returns quickly and enqueues long-running work.

### Relational database
PostgreSQL is the required database for local development, tests, and deployment. Alembic owns schema changes. The test suite requires a separate PostgreSQL database and isolates each run in a disposable schema.

### Private object storage
Original uploads use a local private filesystem adapter in development and a private S3-compatible bucket in deployment. The provider is configurable; Cloudflare R2, AWS S3, or compatible services may be selected after quota, backup, access-control, and cost validation. Use stable object identifiers, checksums, and lifecycle rules only after retention decisions.

### Background worker
The API persists extraction jobs in the relational database. One or more separately supervised `python -m app.worker` processes claim jobs with renewable leases, bounded exponential retry, and stale-lease recovery. Workers process document parsing, OCR, question segmentation, and quality checks. Do not rely on API request-process background tasks for durable work.

### Search
PostgreSQL full-text search powers keyword discovery. A separate semantic route can use embeddings with a keyword fallback; pgvector is not currently enabled as the active embedding store.

### Notifications
Database-backed notification records with optional email delivery. Email failures must not invalidate core uploads or comments.

### Monitoring and administration
Structured logs, metrics, queue status, quota warnings, errors, backup status, and admin audit views.

## 3. Suggested deployment shape

- Static frontend hosting or a suitable edge/static platform.
- API service with secrets managed outside source control.
- PostgreSQL managed service or durable self-managed database.
- Private object storage for original files.
- Separate worker process with the database-backed durable job queue.
- Scheduled backup and health-check tasks.
- Optional email provider for transactional notifications.

Do not assume one provider is permanently free or that a sleeping web service is suitable for a durable worker. Verify current quotas and terms before launch.

## 4. Request path vs. processing path

Upload request:
1. authenticate;
2. authorize upload;
3. validate request and declared metadata;
4. create document/job records;
5. transfer or finalize private object storage;
6. return status.

Background path:
1. separately deployed worker claims a queued job with a renewable lease;
2. verify stored object and checksum;
3. security/policy screen;
4. extract pages/text;
5. OCR/vision as needed;
6. segment questions;
7. apply quality checks;
8. write results idempotently;
9. index approved records;
10. update statuses and notify;
11. emit metrics and audit events.

## 5. Reliability boundaries

- Database is authoritative for application metadata and job state.
- Object storage is authoritative for original file bytes.
- Search indexes are derived and rebuildable.
- Embeddings are derived and versioned.
- Notifications are durable records; email is a delivery channel.
- Admin exports and backups must document how to restore database/object relationships.

## 6. Scalability principles

Start simple, but keep boundaries clear. Do not introduce microservices merely for fashion. A modular API plus separate worker is a reasonable initial structure. Separate components only when operational needs justify it.

## 7. Implemented stack and open choices

- React + TypeScript + PWA
- FastAPI + Python
- PostgreSQL (required)
- Private S3-compatible object storage in deployment; provider not finalized
- PostgreSQL full-text search; pgvector remains unimplemented
- Database-backed durable processing queue for the initial implementation; replace or extend it only if measured throughput requires a dedicated broker.
- Self-hosted email/password sessions
- OCR candidate: PaddleOCR
- Vision model: choose after benchmark

The final choices must be validated against current free-tier limits, supported features, latency, data handling, licensing, and recovery requirements.
