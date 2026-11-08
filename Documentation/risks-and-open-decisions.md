# Risks, Assumptions, and Open Decisions

## 1. Open decisions register

| Decision | Current position | Required next action |
|---|---|---|
| Frontend/API hosting | Candidates discussed, not finalized | Compare current limits, sleep behavior, reliability, and migration path |
| Authentication provider | Self-hosted email/password sessions implemented | Google sign-in remains out of scope; review operational email deliverability and administrator MFA before launch |
| Durable queue | Not finalized | Choose a queue compatible with worker runtime and hosting |
| Object storage | S3-compatible private bucket required for non-local deployment; provider open | Select provider and validate current quotas, access controls, egress, backups, and costs |
| OCR engine | PaddleOCR candidate | Benchmark on representative school documents |
| Vision model | Not selected | Benchmark quality, memory, licensing, privacy, and cost |
| Semantic index | PostgreSQL full text + pgvector candidate | Validate hosting support and scale |
| External AI fallback | Disabled by default | Review terms/data handling/cost before enabling |
| Legal/copyright policy | Needs review | Draft terms, takedown, school materials, and privacy policy |
| Admin MFA | Strong password selected; MFA recommended | Decide mandatory policy before public launch |
| School verification | Self-reported initially | Decide whether/when verification is necessary |
| RPO/RTO | Not selected | Set realistic recovery targets |
| Backup capacity | Limited by budget/free tiers | Validate storage and independent backup strategy |
| Amharic extraction | Allowed, limited-support label | Evaluate representative corpus and communicate limits |
| User audience controls | Whole-school/selected users planned | Finalize exact sharing model and authorization tests |

## 2. Major risks

### Extraction quality
Math, diagrams, scans, and complex layouts can produce incomplete or incorrect text. Mitigation: source crops, question-level review, benchmark corpus, explicit uncertainty, and versioned pipeline.

### Security of uploads
Malicious or malformed files can target parsers and storage. Mitigation: actual type validation, malware checks, quarantine, constrained workers, least privilege, and tests.

### Privacy leakage
Private documents can leak through object URLs, search snippets, exports, or admin mistakes. Mitigation: private storage, server-side authorization, short-lived signed URLs, audited exports, and permission tests.

### Free-tier dependency
Provider changes can interrupt service or force migration. Mitigation: quota monitoring, backups, provider abstraction, and documented export/migration procedures.

### Queue domination
One contributor can consume available compute. Mitigation: fair scheduling, bounded concurrency, per-user quotas, and backpressure.

### Copyright and unauthorized sharing
Users may upload material they cannot redistribute. Mitigation: clear terms, reporting/takedown process, moderation, and legal review.

### False metadata
AI can infer incorrect year, curriculum, or topic. Mitigation: evidence-backed suggestions, unknown values, review, and correction tracking.

### Admin overload
Every upload and failure can create notifications. Mitigation: grouped/deduplicated alerts, filters, priorities, and operational dashboards.

### Scope creep
A broad platform can delay the core archive. Mitigation: phased roadmap and explicit exit criteria.

## 3. Assumptions

- Initial UI language is English.
- Amharic uploads are permitted, with limited extraction support clearly labeled.
- No answer keys are accepted or generated in the initial release.
- All registered users may upload subject to controls.
- Only global system admin is needed initially.
- Default content visibility is all registered users, subject to configured audience permissions.
- PWA is preferred to separate native mobile apps at launch.
- The original document remains the source of truth.
- Reliable questions may publish while uncertain questions are held.
- Slower free-first processing is acceptable.

## 4. Decision governance

When a decision changes:
1. record the date and reason;
2. update the relevant product and technical docs;
3. identify affected schema/API/security tests;
4. plan migration and rollback;
5. communicate user-facing changes where necessary.

Do not let an old planning note silently override a later explicit decision.
