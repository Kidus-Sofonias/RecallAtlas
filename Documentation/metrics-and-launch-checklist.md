# Metrics and Launch Checklist

Checklist status was reviewed against the implementation on 2026-11-07. `[x]` means implemented/tested; it does not mean production infrastructure is provisioned. The live PostgreSQL integration, ClamAV operation, legal review, and restore/pilot gates are still open.

## 1. Product success metrics

### Archive usefulness
- Number of searchable published questions.
- Number of source documents.
- Percentage of published questions with valid source provenance.
- Search-to-open rate.
- Search reformulation and zero-result rate.
- Repeat use and saved-item engagement.

### Processing quality
- Upload processing success rate.
- Extraction completeness.
- Question-boundary accuracy.
- Source-page correctness.
- Diagram/math fidelity.
- Metadata correction rate.
- Duplicate grouping accuracy.
- Median and p95 processing duration.
- Retry and terminal failure rate.

### Operations
- Queue length and oldest job age.
- Storage growth and quota use.
- API/database/search latency.
- Error rate and outage duration.
- Backup success and restore test success.
- Notification delivery failures.
- Cost estimate and free-tier headroom.

### Moderation and governance
- Reports received/resolved.
- Queue age for uncertain extractions and suspicious files.
- Repeated policy violations.
- False-positive quarantine rate.
- Admin actions with complete audit records.

## 2. Pre-pilot checklist

### Product
- [ ] Upload flow explains supported formats, size limit, and no-answer policy. (Backend requires no-answer confirmation; frontend upload flow is not implemented.)
- [x] Search includes Questions, Documents, and Resources tabs.
- [x] Question pages show source provenance.
- [x] Uncertain questions are held for review.
- [ ] User-facing processing states are understandable.

### Security
- [x] Actual file type and size are validated server-side.
- [x] Original files are private.
- [x] Source preview/download routes authenticate and authorize access; files stream through the API. Signed URLs are not used.
- [x] Admin endpoints are protected.
- [ ] Rate limits are configured.
- [x] `.env` files are excluded from Git; perform a production log/secrets review before launch.
- [x] Quarantine path is covered by backend tests; production ClamAV operation is still required before accepting uploads.
- [x] Backend security and permission tests pass in the available local test run; live PostgreSQL tests remain pending.

### Data and recovery
- [x] Database migrations are versioned.
- [ ] Daily backup process is configured.
- [x] Original-file backup strategy is documented.
- [ ] Complete local export is possible.
- [ ] Restore has been tested.
- [ ] Checksums and source links remain correct after restore.

### AI/search
- [ ] Evaluation corpus includes scans, math, diagrams, and multilingual samples.
- [x] Extraction method/version is recorded.
- [x] Question-level review gates are tested.
- [x] Retry logic is bounded and covered by tests.
- [x] Keyword search works without semantic search.
- [x] Search filters held/private content; backend permission tests cover relevant routes.

### Operations
- [ ] Admin receives upload and failure notifications.
- [ ] Queue and quota dashboard is visible.
- [ ] Alerts are deduplicated.
- [x] Incident and outage guidance is documented in [backup-recovery-and-outages.md](./backup-recovery-and-outages.md); operational exercises remain pending.
- [ ] Admin security/MFA decision is resolved.

### Governance
- [ ] Terms of use and privacy policy reviewed.
- [ ] Copyright complaint/takedown process documented.
- [ ] Data retention and account deletion process documented.
- [x] No-answer policy is explicit in the upload API and product requirements.
- [ ] School affiliation is labeled self-reported until verified.

## 3. Pilot review

After the pilot, review:
- where users fail to find questions;
- which document types produce poor extraction;
- how often source pages are wrong;
- whether the review queue is manageable;
- which resource categories are actually used;
- how quickly users understand upload status;
- whether the service fits quota and cost constraints;
- whether users understand visibility and sharing settings.

Use observed results to prioritize work rather than adding features based only on enthusiasm.
