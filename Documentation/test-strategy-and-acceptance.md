# Test Strategy and Acceptance Criteria

## 1. Testing layers

### Unit tests
Validate parsing utilities, metadata rules, state transitions, permission functions, queue policies, and search ranking helpers.

### Integration tests
Test database persistence, object storage, auth integration, background queue, notifications, indexing, and API flows.

### End-to-end tests
Test the full upload-to-search path, user journeys, admin review, and recovery behavior.

### Security tests
Test authorization, upload validation, signed links, rate limiting, secrets handling, admin endpoints, and exports.

### Document corpus evaluation
Run representative PDFs and Office files through extraction and compare results with manually reviewed ground truth.

## 2. Core MVP acceptance criteria

1. A registered user can upload a supported file within the configured size limit.
2. The server verifies actual file type and stores the original privately.
3. Each accepted file receives a stable ID and checksum.
4. Unsafe or uncertain-safety files are quarantined and unpublished.
5. Extraction runs asynchronously.
6. Reliable questions are published with source document/page references.
7. Uncertain questions are held for review without blocking reliable questions from the same document.
8. The original document can be opened by an authorized user.
9. Published questions are searchable by keyword and metadata filters.
10. Search never exposes held, quarantined, or unauthorized content.
11. Failed jobs retry a bounded number of times and then appear in the admin queue.
12. Admin receives required notifications and can inspect processing state.
13. Retrying a job does not create duplicate question records.
14. A backup can be restored and provenance remains intact.
15. Published questions preserve their source reading order, question type when known, choice labels/order, blanks, subparts, and references to diagrams, graphs, tables, and formulas.
16. The learner-facing question record contains no generated answer field.
17. Suspected transcription errors or uncertain critical symbols are held or explicitly flagged and retain an authorized original-page/crop fallback; they are not silently autocorrected or presented as verified.

## 3. Quality metrics

Track:
- upload validation success rate;
- processing success rate;
- extraction completeness;
- question-boundary accuracy;
- source-page correctness;
- diagram/equation preservation;
- metadata correction rate;
- duplicate grouping accuracy;
- median and p95 processing time;
- job retry and failure rate;
- search latency and index freshness;
- unresolved moderation queue age;
- quota use;
- backup and restore success.

Use the pre-release targets in [AI Quality, Human Review, and Corrections](./quality-and-review.md) as initial gates. Measure and report results separately for each input, layout, and question-format category. A baseline can justify changing a target only through a documented product/release decision; do not lower a target silently to make a model pass. No aggregate score may conceal failure on critical tokens, source provenance, choices, or visual elements.

For text, store ground-truth transcriptions and compare normalized text with character error rate (CER), while separately exact-matching meaning-critical tokens such as negation, values, units, signs, labels, and operators. For structured layout, compare question boundaries, type, subparts, blank locations, option labels/order, and visual references against annotations. Inspect disagreements manually and retain the failing page as a regression fixture.

## 4. Representative test fixtures

Create sanitized fixtures for:
- text-based PDF;
- scanned PDF;
- low-resolution scan;
- two-column document;
- true/false question;
- multiple-choice question with labels, wrapped options, and options spanning a page break;
- short-answer prompt with answer-space cues;
- fill-in-the-blank question with multiple blanks;
- math-heavy question with fractions, superscripts/subscripts, roots, signs, and units;
- question with diagram, labeled graph, or image-dependent prompt;
- table-based question and mixed table/text page;
- questions spanning pages;
- Word worksheet;
- PowerPoint educational material;
- Amharic document;
- faint print, skew, bleed-through, handwriting, and mixed text/image page;
- corrupted/malformed file;
- unsupported file disguised with an allowed extension;
- duplicate document and near-duplicate questions.

For each supported fixture, retain a human-verified reference for exact page, question boundaries, content order, format, choices, blank positions, critical tokens, visual elements, and source crop/location. Include adversarial near-misses (for example `not` vs. no negation, `-` vs. `+`, `0` vs. `O`, and similarly shaped option labels) and verify that uncertain cases are flagged rather than silently changed.

## 5. Regression process

Every change to OCR, vision model, segmentation, format classification, rendering representation, metadata inference, or indexing should run the benchmark corpus. Review regressions by category, not only aggregate average. Store the model version, OCR/extractor version, and pipeline version for each extraction so the team can identify which version produced an error. Add every confirmed production extraction error to the sanitized regression corpus when licensing and privacy allow.

## 6. Accessibility and usability tests

Test mobile and desktop layouts, keyboard access, focus indicators, screen-reader labels, contrast, upload progress, error recovery, and comprehension of processing states.

## 7. Launch gates

Do not launch broadly until:
- upload/security path is tested;
- permissions and signed URLs pass tests;
- backup and restore are demonstrated;
- extraction is benchmarked on representative documents;
- admin queues and alerts work;
- terms, privacy, and copyright processes are reviewed;
- critical error and outage behavior is understood;
- MFA decision is resolved for admin access.
