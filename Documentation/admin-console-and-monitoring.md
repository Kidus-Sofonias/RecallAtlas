# Admin Console and Monitoring

## 1. Design objective

The admin dashboard should expose everything needed to operate the platform without making the interface confusing. Present an overview first, then allow drill-down into users, documents, individual questions, reports, and job details.

## 2. Overview dashboard

Show:
- new uploads;
- processing queue length and oldest job;
- published questions/resources;
- questions awaiting review;
- quarantined files;
- failed jobs;
- open reports;
- storage usage and growth;
- estimated quota/cost use;
- recent security events;
- backup status;
- search/API/database health.

## 3. User record view

Authorized administrators should be able to inspect:
- account/profile details needed for operations;
- school and grade selection (marked self-reported unless verified);
- uploads and contribution history;
- relevant edits and review decisions;
- comments and reports involving the user;
- account status and security-related events;
- deletion request state.

The dashboard should not encourage unnecessary surveillance. Make the purpose of activity data clear, limit retention, and log sensitive access.

## 4. Upload and extraction queue

Useful filters:
- status;
- uploader;
- resource type;
- date;
- safety status;
- failure category;
- number of questions held;
- retry count;
- source language.

Actions:
- inspect source safely;
- review uncertain question;
- retry processing;
- release from quarantine only after required checks;
- reject/retain/delete according to policy;
- inspect job history;
- view source-page mapping;
- see whether indexing is complete.

The initial implementation exposes recent persisted jobs at `GET /api/v1/admin/jobs`, job details at `GET /api/v1/admin/jobs/{job_id}`, and retries at `POST /api/v1/admin/jobs/{job_id}/retry`. The dashboard includes job status, attempts, safe error categories, and retry controls. A separately supervised `python -m app.worker` process is required; run multiple workers only when they share the same database and durable private storage.

## 5. Alerts

Required alerts include:
- every new upload;
- suspicious/quarantined file;
- processing failure or repeated retry;
- items awaiting review;
- quota warning;
- service outage;
- backup failure;
- security incident;
- unusual rate or volume spikes.

Notifications must be deduplicated and grouped to avoid overwhelming the admin. Critical alerts should remain visible until acknowledged or resolved.

## 6. Logs and metrics

Use structured logs with timestamps, request/job IDs, component, severity, and sanitized error category. Avoid logging passwords, tokens, signed URLs, or full private document content.

Metrics:
- upload validation success/failure;
- security quarantine rate;
- extraction success;
- question publication and review rates;
- source-page correctness;
- median/p95 job duration;
- retries and terminal failures;
- search latency;
- indexing lag;
- report resolution time;
- storage and quota use;
- backup/restore status.

## 7. Audit log

Record privileged actions such as:
- role and permission changes;
- release/rejection of quarantined files;
- publication/rejection decisions;
- taxonomy changes;
- account suspension/deletion;
- exports and backup downloads;
- manual retries and processing overrides;
- security setting changes.

Include actor, action, target, timestamp, outcome, and safe rationale. Audit records should be append-only or protected from routine alteration.

## 8. Operational runbooks

Create concise runbooks for:
- stuck queue;
- repeated extraction failure;
- quota exhaustion;
- storage outage;
- database restore;
- compromised admin account;
- malware incident;
- unexpected public exposure;
- email notification failure;
- semantic search degradation.
