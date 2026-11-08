# Recall Atlas — Phased Implementation Roadmap

Implementation snapshot: 2026-11-07. The codebase is a partial implementation of the roadmap, not a blank project. Verified completion and active blockers are recorded in [PROJECT_STATUS.md](../docs/PROJECT_STATUS.md).

| Phase | Current status | Completed evidence | Still open |
|---|---|---|---|
| 0 — Foundation | PARTIAL | FastAPI/React application, PostgreSQL migrations, auth, local Compose database, environment example, and backend tests exist. | Run tests/migrations against live PostgreSQL; CI, repeatable browser tests, and production environment remain. |
| 1 — Archive MVP | PARTIAL | Upload API, private storage adapters, durable worker, extraction/review, authorized source preview/download, and keyword search exist. | Frontend upload, configured object bucket/ClamAV, live PostgreSQL, backups/restore, and end-to-end release flow remain. |
| 2 — Quality and corrections | PARTIAL | Admin extraction review, OCR provenance, and source-review cues exist. | Benchmark corpus/ground truth, correction/versioning, duplicate workflow, full math/diagram fidelity, and quality dashboards remain. |
| 3 — Security and operations | PARTIAL / BLOCKED | Auth/ownership checks, fail-closed scan path, admin moderation routes, and operational documentation exist. | ClamAV operation is deferred; live backup/restore, distributed rate limits, MFA decision, privacy/legal review, and pilot remain. |
| 4 — Search and study tools | PARTIAL | Keyword search, semantic endpoint, bookmarks, and basic collections exist. | Production embedding capacity, collection completeness, related content, and offline experience remain. |
| 5 — Community | PARTIAL | Comments, replies, reports, and notifications have backend/frontend implementation. | Moderation/abuse operations, notification preferences, and complete admin/audit workflows remain. |
| 6 — Rollout | NOT STARTED | None claimed. | Pilot, capacity evidence, accessibility validation, and rollout decisions remain. |

## Guiding rule

Build the smallest reliable end-to-end archive first. Every phase should produce a testable increment. Do not begin with leaderboards, broad social features, or sophisticated recommendation systems while upload, provenance, security, and search remain unproven.

## Phase 0 — Foundation

### Goals
Create a reproducible project skeleton and secure development workflow.

### Work
- Initialize repository and folder structure.
- Add environment configuration and `.env.example`.
- Configure linting, formatting, type checks, and test runner.
- Select initial database and migration tool.
- Define initial auth integration and user model.
- Establish staging and production separation.
- Add CI for tests and static checks.
- Document local setup and secret handling.
- Create basic logging conventions and request/job IDs.

### Exit criteria
A developer can run the app locally, apply migrations, sign in, and run automated tests without using production secrets.

## Phase 1 — End-to-end archive MVP

### Goals
Deliver upload → private storage → safe processing → question extraction → source view → keyword search.

### Work
- Upload API and guided frontend.
- Server-side file validation.
- Private object storage integration.
- Document metadata/status records.
- Security/policy screening and quarantine state.
- Async queue and worker.
- Digital PDF text extraction.
- OCR path for scans.
- Basic question segmentation.
- Source page mapping.
- Question-level quality gate.
- Publish reliable questions; hold uncertain questions.
- Original document viewer/download with authorization.
- Unified search page with Questions/Documents/Resources tabs.
- Keyword search and core metadata filters.
- Admin upload/processing queue and notifications.
- Bounded retries, idempotency, and job logs.
- Basic backups and restore test.

### Exit criteria
A representative test document can be uploaded and searched end to end. Source provenance is intact, unsafe files are held, and failed jobs are recoverable.

## Phase 2 — Quality, metadata, duplicates, and corrections

### Work
- AI metadata suggestions with evidence/unknown handling.
- Admin-controlled taxonomy.
- Question-level review interface with source crops.
- User correction workflow.
- Duplicate grouping for documents/questions.
- Version history.
- Expanded document format support and regression corpus.
- Better math/diagram preservation.
- Quality dashboards and extraction benchmark reports.

### Exit criteria
Reviewers can fix common extraction problems, changes are auditable, and quality metrics are visible.

## Phase 3 — Security, recovery, pilot, and operations

### Work
- Complete permission audit.
- Signed-link expiration tests.
- Rate limiting and abuse prevention.
- Admin MFA decision and implementation as selected.
- Backup exports and independent file backup.
- Quarterly restore procedure.
- Incident and outage runbooks.
- Moderation/report queue.
- Privacy/retention controls.
- Pilot with a limited set of users and representative school documents.

### Exit criteria
A pilot can run with monitored failures, controlled access, and demonstrated recovery.

## Phase 4 — Semantic search and study experience

### Work
- Embedding generation and versioned semantic index.
- Keyword fallback and degraded-mode UX.
- Related questions/resources.
- Bookmarks and named private collections.
- Recently viewed and continue reading.
- Topic pages and document-to-question navigation.
- Installable PWA and saved-item offline reading.

### Exit criteria
Users can discover relevant content beyond exact keyword matches and organize their study material.

## Phase 5 — Community features

### Work
- Comments and replies.
- Spam/rate controls.
- Reports for content/comments/accounts.
- Notifications and preferences.
- Contribution statistics and streaks.
- Quality-weighted achievements/leaderboard.
- Articles, notes, opportunities, and announcements.
- Optional email notification delivery.

### Exit criteria
Community features have moderation, privacy, and notification behavior that has been tested.

## Phase 6 — Broader school rollout and improvement

### Work
- Expand the pilot gradually.
- Measure extraction quality by document type and language.
- Improve taxonomy and search ranking.
- Add school verification only if needed and operationally feasible.
- Reassess hosting capacity and cost.
- Review legal/content policy and user feedback.
- Improve accessibility and mobile experience.

### Exit criteria
Rollout is supported by evidence on reliability, usefulness, moderation capacity, and cost.

## Priority order

1. Reliable archive and source traceability.
2. Security and permissions.
3. Extraction quality and review.
4. Search.
5. Recovery and operations.
6. Study organization.
7. Community and growth features.
