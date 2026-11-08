# API Contracts — Planning Outline

This document includes both implemented routes and planned routes. Items explicitly labeled "implemented" reflect the current backend; other routes remain conceptual until an OpenAPI contract and implementation are added.

## 1. API conventions

- Version routes, e.g. `/api/v1`.
- Use stable opaque identifiers.
- Validate request bodies and file metadata.
- Return structured error codes and safe human-readable messages.
- Paginate list endpoints.
- Apply authorization to every protected resource.
- Use idempotency keys for uploads and retry-sensitive mutations.
- Never return storage credentials or permanent private object URLs.
- Keep long-running work asynchronous.

## 2. Authentication/profile

- `GET /api/v1/me`
- `PATCH /api/v1/me`
- `GET /api/v1/me/preferences`
- `PATCH /api/v1/me/preferences`
- `POST /api/v1/me/deletion-request`

The implemented application uses self-hosted email/password sessions. Managed authentication is not the active integration.

The implemented onboarding request accepts an optional `preferred_grade` (9–12), returned in the authenticated user payload for the grade-matched home feed.
`PATCH /api/v1/auth/preferences` lets an authenticated user update or clear grade preference and subject interests. `GET /api/v1/auth/me` returns the current profile and preference IDs.
`GET /api/v1/me` and `PATCH /api/v1/me` expose and update the signed-in user's display name and self-reported school. `POST /api/v1/me/deletion-request` requires `{ "confirm": true }`, records a request timestamp, and revokes active sessions. Admin review/approval anonymizes account identifiers and removes private associations while retaining academic contributions; legal retention rules and backup cleanup remain open.

The ClamAV adapter and quarantine review endpoints exist, but the scanner is intentionally deferred and must be operated/configured before uploads can be processed in deployment. With no reachable scanner, uploads remain quarantined. Admin endpoints `GET /api/v1/admin/security-quarantine`, `POST /api/v1/admin/documents/{document_id}/security-rescan`, and `POST /api/v1/admin/documents/{document_id}/security-reject` provide the review workflow. A rejection requires a rationale; release is possible only by a successful rescan.

## 3. Uploads/documents

Implemented routes:
- `POST /api/v1/uploads/initiate`
- `POST /api/v1/uploads/{document_id}/complete`
- `GET /api/v1/documents/{document_id}`
- `GET /api/v1/documents/{document_id}/questions`
- `GET /api/v1/documents/{document_id}/source`
- `GET /api/v1/documents/{document_id}/preview`
- `GET /api/v1/documents/{document_id}/pages/{page_number}`
- `POST /api/v1/documents/{document_id}/process` (admin only)

Document patching, presigned upload flows, view/download-link issuance, and document reporting are not implemented as routes.

The server must validate actual bytes after upload. A presigned upload URL is not proof that the file is safe.

Upload initiation also accepts optional `grade` (9–12) and `academic_year` (1900–2100) metadata for discovery cards and filters.

## 4. Questions and search

- `GET /api/v1/search?q=...&type=...`
- `GET /api/v1/questions/{question_id}`
- `GET /api/v1/questions/{question_id}/related`
- `PATCH /api/v1/questions/{question_id}` for authorized correction workflows
- `POST /api/v1/questions/{question_id}/bookmark`
- `POST /api/v1/questions/{question_id}/report`

Search response should include result type, known metadata, source provenance, access-safe snippets, and pagination. Never return held/quarantined items to ordinary users.

Implemented discovery and search routes:
- `GET /api/v1/discovery?grade=9..12` returns recently added reviewed questions and, when a grade is supplied, matching recommendations.
- `GET /api/v1/search?q=...&grade=9..12&subject_id=...` searches reviewed questions and optionally filters by grade or subject.
- `GET /api/v1/search/suggestions?q=...` returns up to 12 question, paper, and article suggestions.
- `GET /api/v1/search/explore?q=...&grade=...&subject_id=...` returns `questions`, `papers`, and `articles` groups.

Question search omits held questions and questions whose source document is not completed. Paper search requires at least one reliable question. Suggestions require a two-character query. Explore can also return recent content when called without a query or filters. Results are limited, but cursor pagination is not implemented.

## 5. Resources and comments

- `GET /api/v1/resources` lists published articles.
- `POST /api/v1/resources` creates and publishes an article (administrator only).
- `GET /api/v1/resources/{resource_id}`
- `POST /api/v1/resources/{resource_id}/comments`
- `POST /api/v1/questions/{question_id}/comments`
- `POST /api/v1/comments/{comment_id}/replies`
- `POST /api/v1/comments/{comment_id}/report`

Use rate limits and spam controls. Comments should be stored as plain text or sanitized content; do not render untrusted HTML.

## 6. Collections and bookmarks

- `GET /api/v1/collections`
- `POST /api/v1/collections`
- `PATCH /api/v1/collections/{collection_id}`
- `DELETE /api/v1/collections/{collection_id}` (private collection only; content itself remains)
- `POST /api/v1/collections/{collection_id}/items`
- `DELETE /api/v1/collections/{collection_id}/items/{item_id}`

Enforce collection ownership on every request.

## 7. Reports and moderation

User-facing:
- `POST /api/v1/reports`
- `GET /api/v1/me/reports` (only if product decides users can track their reports)

Admin:
- `GET /api/v1/admin/reports`
- `POST /api/v1/admin/reports/{report_id}/decision`
- `GET /api/v1/admin/review-queue`
- `POST /api/v1/admin/questions/{question_id}/review-decision`
- `POST /api/v1/admin/documents/{document_id}/retry`

Every admin endpoint requires strong authorization and an audit event.

## 8. Processing status

- `GET /api/v1/documents/{document_id}/status`
- `GET /api/v1/admin/jobs`
- `GET /api/v1/admin/jobs/{job_id}`
- `POST /api/v1/admin/jobs/{job_id}/retry`

Do not expose internal stack traces to normal users.

The implemented admin job list is `GET /api/v1/admin/jobs` (optional `status`, bounded `limit`) and manual retry is `POST /api/v1/admin/jobs/{job_id}/retry`. API requests enqueue extraction into the database; a separately supervised `python -m app.worker` process claims and executes jobs. The worker applies bounded retries, exponential backoff, renewable leases, and stale-lease recovery.

## 9. Error categories

Suggested stable categories:
- `AUTH_REQUIRED`
- `FORBIDDEN`
- `NOT_FOUND`
- `INVALID_FILE`
- `FILE_TOO_LARGE`
- `UNSUPPORTED_FORMAT`
- `UPLOAD_INCOMPLETE`
- `QUARANTINED`
- `PROCESSING_PENDING`
- `PROCESSING_FAILED`
- `RATE_LIMITED`
- `SEARCH_DEGRADED`
- `VALIDATION_ERROR`
- `INTERNAL_ERROR`

## 10. Contract tests

Test schema validation, permission failures, pagination, duplicate submissions, retry idempotency, upload completion races, expired signed links, and status transitions. Generate or maintain OpenAPI documentation from the actual implementation so the docs do not drift.
