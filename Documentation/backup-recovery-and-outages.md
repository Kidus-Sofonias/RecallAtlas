# Backup, Recovery, and Outage Plan

## 1. Backup objectives

The platform must recover from accidental deletion, database corruption, provider failure, bad migrations, compromised credentials, and application bugs. Backups must be tested; a successful backup job is not proof that restore works.

The current administrator export endpoint is intentionally disabled (HTTP 501): it does not yet create a PostgreSQL dump or a complete private-file archive. Configure and verify both backup layers before deployment.

## 2. Required backup layers

### Database
- Daily database backups.
- Backup before major migrations or risky releases.
- Keep backups protected and independent from the primary database where possible.
- Verify backup completion and alert on failure.

### Original files
- Back up original files independently of the database.
- Preserve object keys, checksums, sizes, and metadata.
- Keep a copy in a separate location/provider within available free capacity where practical.

### Application metadata and derivatives
Include extracted questions, metadata, taxonomy, user records, comments, reports, collections, notification records, configuration, and a manifest that links files to database records.

### Local administrator export
The administrator must be able to save a complete export locally containing:
- database dump;
- original files;
- extracted questions and metadata;
- comments and other necessary records;
- configuration inventory (not exposed secrets);
- manifest and checksums;
- restore instructions.

The export must be protected and should not be served through a public link.

## 3. Backup security

- Encrypt sensitive backups where supported.
- Restrict access to named administrators.
- Keep secrets separate from backups or encrypt them under a separate process.
- Log export creation and download.
- Define retention and secure deletion.
- Avoid placing backup archives in public web directories.

## 4. Restore testing

- Test restoration quarterly.
- Test again after major infrastructure changes.
- Restore into an isolated environment.
- Verify record counts and checksums.
- Verify document-to-question provenance.
- Test authentication, search, permissions, and signed file access.
- Record duration, issues, and remediation.

## 5. Recovery objectives

Recovery Point Objective (RPO) and Recovery Time Objective (RTO) have not yet been selected. Choose targets based on realistic budget and service requirements. Do not promise zero data loss or instant recovery without a tested architecture.

## 6. Outage behavior

When a component is unavailable:
- keep search/read available where possible;
- disable only affected upload or processing paths;
- show a clear status message;
- preserve queued jobs and their state;
- do not drop uploads silently;
- alert the administrator;
- resume/retry safely after recovery;
- avoid duplicate questions when jobs are replayed.

## 7. Provider outage examples

### OCR/vision provider unavailable
Keep uploads queued or use a safe fallback only if its quality and privacy have been approved. Do not silently publish lower-quality output.

### Semantic search unavailable
Continue keyword search and show a brief degraded-status message.

### Email provider unavailable
Persist in-app notifications and retry email delivery separately.

### Object storage unavailable
Pause new file finalization and file downloads as necessary. Do not mark uploads complete until durable storage is confirmed.

### Database unavailable
Return controlled errors; do not pretend writes succeeded. Restore from backups and reconcile queued work before reopening uploads.

## 8. Recovery checklist

1. Declare incident and identify affected components.
2. Pause risky writes or processing.
3. Preserve logs and current state.
4. Restore credentials/infra safely.
5. Restore database and object relationships.
6. verify checksums and provenance.
7. replay idempotent jobs.
8. run security and permission smoke tests.
9. re-enable uploads gradually.
10. document root cause and preventive changes.
