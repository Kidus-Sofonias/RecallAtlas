# Document Processing Pipeline

## 1. Design objective

Turn academic source documents into individually searchable questions without losing the source of truth. The pipeline is asynchronous, auditable, retryable, and designed to isolate uncertainty.

## 2. High-level stages

1. Receive upload and create document record.
2. Validate declared and actual file type, size, and structural validity.
3. Store original privately and compute checksum.
4. Run malware/security and policy screening.
5. Quarantine suspicious or uncertain-safety files.
6. Detect document type and page characteristics.
7. Extract digital text where possible.
8. Run OCR and layout analysis for scans.
9. Use vision-assisted processing for difficult pages where approved.
10. Normalize text, layout blocks, images, tables, and math without discarding their page relationships.
11. Segment the document into question candidates and supporting elements.
12. Classify question format only when supported by the source.
13. Attach source document, page, and location provenance.
14. Suggest metadata with evidence and confidence.
15. Run quality gates.
16. Publish reliable question records.
17. Hold uncertain questions for review.
18. Index approved content for keyword search and semantic retrieval.
19. Update status, notify relevant users/admin, and emit metrics.

## 3. Prefer the least expensive reliable method

- Digital PDF text extraction should be attempted before OCR.
- OCR should be applied only to pages that require it when possible.
- Vision models should be reserved for pages where text/layout extraction is insufficient.
- Preserve original page images or crops when equation/diagram fidelity is uncertain.
- Keep provider-specific logic behind an abstraction so a model can be replaced without rewriting the product.

## 4. Question representation and reading fidelity

The reader should present a simple, scrollable, document-like rendering. Extraction must preserve enough structure for that rendering to match the source, rather than flattening every question into an undifferentiated text string.

Represent, where present:
- question prompt and paragraph/line breaks;
- question number and sub-question hierarchy;
- format: true/false, multiple choice, short answer, fill-in-the-blank, or unknown/other;
- choices as ordered, separately associated items, including labels;
- blanks and answer-space cues as blanks, not inferred answers;
- tables, diagrams, graphs, and image/crop references in their source order;
- equations and mathematical symbols in a renderer-safe representation plus a link to the source region;
- page and optional bounding-box provenance for each block.

Do not add an answer field to the learner-facing record. Do not infer omitted choices, fill blanks, solve questions, silently autocorrect uncertain text, or redraw a diagram as if it were the source. When structure or content is ambiguous, mark the candidate for review and retain an authorized path to the exact original page or crop. Keep original files private and enforce the same access checks on previews and downloads as on the document.

The implementation provides an extraction path for text PDFs, scanned PDFs/images (RapidOCR), DOCX paragraphs/tables, and PPTX text, tables, and embedded images. It stores ordered text/choice blocks, heuristic format labels, OCR confidence and normalized OCR-region hints where available, page context, source-review reasons, and an extraction version. Physics vector/force notation and ambiguous direction-angle strings on visual pages, along with formula/diagram cues, are held for original-source review rather than silently interpreted. Extracted questions remain held pending an administrator decision; the admin queue supports source comparison, approval, or rejection. OCR/runtime dependencies are declared but require installation before OCR works. This is not a validated production OCR pipeline: OCR-region hints are not a complete layout reconstruction, and formulas/graphs are not symbolically transcribed or verified. Office-page previews are not implemented. Authorized source-download and PDF/image page-preview routes are available to the uploader/admin or registered readers when the document has published questions.

Extraction jobs are persisted in `processing_jobs`, claimed by a separate worker (`python -m app.worker`) using row locks where supported and conditional state updates. Jobs have leases, heartbeats, bounded exponential retry, stale-lease recovery, and a terminal failure state after the configured attempt limit. API processes only enqueue jobs; they do not depend on request-process background execution. Run one or more worker processes against the same database and private storage. Monitor `GET /api/v1/admin/jobs`; admins can retry terminal failures at `POST /api/v1/admin/jobs/{job_id}/retry`. Configure polling, retry, and lease values using `PROCESSING_WORKER_POLL_SECONDS`, `PROCESSING_MAX_ATTEMPTS`, `PROCESSING_RETRY_BASE_SECONDS`, and `PROCESSING_LEASE_SECONDS`. The default lease is 30 minutes and is renewed during extraction. Durable execution still depends on operating the worker as a supervised service and using shared durable database/storage in multi-host deployments.

## 5. Document and question status

Suggested document states:
- `received`
- `validating`
- `security_check`
- `quarantined`
- `queued`
- `processing`
- `partially_published`
- `published`
- `needs_review`
- `failed_retryable`
- `failed_terminal`

Suggested question states:
- `candidate`
- `quality_check`
- `published`
- `needs_review`
- `rejected`
- `superseded`

A document can contain both published and held questions. Document status should reflect that mixed state rather than forcing every question into one decision.

## 6. Source provenance

Every extracted question should link to:
- stable source document ID;
- source file version;
- page number or page range;
- bounding box/crop coordinates when available, especially for non-text content;
- extraction method and version;
- creation timestamp;
- confidence/quality signals;
- reviewer/correction history where applicable.

Do not treat extracted text as an independent source if its provenance is lost.

## 7. Failure handling

- Use bounded retries with backoff for transient errors.
- Avoid infinite retry loops.
- After retry exhaustion, flag the job for admin inspection.
- Preserve original upload and partial safe results.
- Record safe diagnostic categories without exposing secrets or full private document text in logs.
- Use idempotency keys so retrying a job does not create duplicate questions.
- Make job status and error category visible to authorized admins.

## 8. Fair processing and quotas

The system is free-first and can accept slower processing. Use bounded concurrency, per-user limits, and fair scheduling so one user cannot dominate the queue. If provider quota is nearly exhausted, pause nonessential work, show status, and alert the admin. Do not silently downgrade to a low-quality extraction method.

## 9. Extraction quality checks

Check:
- empty or implausibly short extraction;
- duplicate question candidates;
- page-reference validity;
- text continuity and question numbering;
- question-type classification evidence;
- choice labels, order, and association with the correct question;
- blank locations and sub-question hierarchy;
- equation, diagram, graph, and table presence and source-region association;
- OCR character/word confidence and suspicious substitutions;
- likely missing page boundaries;
- page-level layout quality;
- mismatch between document page count and processed pages;
- unsupported language or layout.

Quality gates should be benchmarked on representative documents, not selected only from clean digital PDFs. A missing or unreadable visual element, uncertain symbol, or questionable spelling must cause a review/source-fallback outcome, not a confident-looking but lossy publication.

## 10. Model and tool selection

Candidate technologies mentioned in planning include PaddleOCR and a suitable vision-capable open-weight model, but no final model is selected. Benchmark tools against a representative test set of digital PDFs, scans, math-heavy pages, diagrams, English, and Amharic documents. Score extraction completeness, source-page correctness, formatting fidelity, latency, resource requirements, licensing, privacy, and cost.

External AI fallback is disabled by default for private school documents unless provider terms, data handling, cost, and quota are reviewed and explicitly approved.
