# File Security and Moderation

## 1. Security posture

Uploaded documents are untrusted input. Extension and browser-reported MIME type are not sufficient. Validate the actual file content, size, structure, and policy status before publication.

## 2. Upload validation

- Allow only explicitly supported formats.
- Enforce configured maximum size on both client and server.
- Require uploaders to confirm they have permission to share the material and that it contains no answers or answer key.
- Check extension, declared MIME type, and detected content type.
- Parse files in constrained worker environments where possible.
- Reject malformed files that cannot be safely inspected.
- Compute a cryptographic checksum.
- Use generated storage keys rather than trusting user-supplied filenames.
- Sanitize filenames for display.
- Keep originals private.
- Rate-limit upload initiation and completion.
- Prevent path traversal and archive/decompression bombs if archive formats are ever added.

## 3. Malware and suspicious content

Upload completion streams the file to the configured ClamAV daemon using its INSTREAM protocol. Configure `CLAMD_HOST`, `CLAMD_PORT` (default `3310`), and `CLAMD_TIMEOUT_SECONDS` (default `5`). A clean response is required before the file moves from private quarantine storage to the extraction path. A detected threat or unavailable/malformed scanner response leaves the original in quarantine, marks the document held, and prevents extraction and ordinary-user source access. The administrator can inspect quarantined originals, retry scanning after restoring the scanner, or reject an upload with a recorded rationale. There is deliberately no manual “mark clean” bypass.

The scanner is fail-closed but is not a replacement for parser sandboxing, policy/copyright screening, or a formally operated malware service. Production must operate and monitor ClamAV, keep signatures current, and verify scanner connectivity before accepting uploads. AI policy screening is supplementary and is not a substitute for actual file-security checks.

## 4. Policy screening

Screen for:
- prohibited answer keys/material contrary to the platform's initial policy;
- abusive or illegal content;
- personal information accidentally included in documents;
- copyrighted or unauthorized content concerns;
- irrelevant or spam uploads;
- content that should be restricted to a particular audience.

The platform should provide a clear policy and reporting mechanism. Legal policy wording requires review before public launch.

## 5. Extraction sandbox

Treat OCR, document parsing, and conversion libraries as attack surfaces. Use least-privilege worker credentials, bounded CPU/memory/time, patched dependencies, temporary-file cleanup, and no unnecessary network access. Do not execute embedded macros or active content in uploaded Office documents.

## 6. Quarantine lifecycle

- Create a quarantine record and reason category.
- Keep the file unpublished.
- Notify the administrator.
- Permit only authorized review tools to access it.
- Record the review decision and rationale.
- If released, rerun required processing checks.
- If rejected, follow documented retention/deletion policy.
- Alert on quarantine volume spikes or repeated malicious patterns.

## 7. Reporting

Users can report documents, questions, resources, comments, and accounts. A report is a signal, not proof. The normal policy is to preserve access while a report is reviewed unless the risk category requires immediate restriction. Reports must have a clear status and audit trail.

## 8. Rate limiting and abuse prevention

Apply rate limits to authentication attempts, uploads, comments, reports, search abuse, signed-link issuance, and admin actions. Use per-user and system-level limits. Keep fair upload-processing quotas so one user cannot monopolize resources.

## 9. Security tests

Test:
- MIME spoofing and extension mismatch;
- oversized files;
- malformed PDFs and Office files;
- path traversal and unsafe filenames;
- malware/quarantine behavior;
- ClamAV clean, infected, unavailable, malformed-response, and timeout behavior;
- guessed object keys and signed URL expiry;
- unauthorized admin endpoints;
- excessive uploads/comments/reports;
- job retry duplication;
- secrets in logs;
- permission changes while links are active;
- backups and exports containing private data.

## 10. Incident response

Document who can restrict uploads, revoke sessions/credentials, disable a vulnerable parser, pause processing, rotate secrets, preserve logs, notify affected users if required, and restore service. Admin alerts should cover security incidents and unusual upload patterns.
