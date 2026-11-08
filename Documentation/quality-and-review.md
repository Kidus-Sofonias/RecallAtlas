# AI Quality, Human Review, and Corrections

## 1. Quality philosophy

AI outputs are candidates, not unquestionable facts. The product should publish dependable results quickly while preserving uncertain material for review. It should never fill missing information with guesses merely to create a complete-looking record.

## 2. Question-level review

Quality is assessed at question level rather than requiring an entire document to pass or fail. Reliable questions from a safe document can be published while uncertain questions remain held. This decision reduces unnecessary delays without presenting doubtful extractions as correct.

## 3. Confidence dimensions

Use separate signals rather than one opaque “AI confidence” number:
- text extraction quality;
- question-boundary confidence;
- source-page/location confidence;
- choice association confidence;
- diagram/math fidelity;
- question-format classification confidence;
- table/graph structure confidence;
- metadata evidence strength;
- duplicate match confidence;
- language/support status.

A single aggregate score may be used internally only if its meaning is documented and validated.

Confidence must be calibrated against a manually labeled corpus for each supported input category. A high average score must not override a low-confidence critical region such as a negation, numeric value, choice label, equation symbol, or diagram label.

## 4. Question format and fidelity rules

The pipeline should preserve source content as structured reading blocks, not just plain text. Supported recognized formats are true/false, multiple choice, short answer, and fill-in-the-blank; ambiguous or other formats remain `unknown` until reviewed. Preserve question numbering, subparts, paragraph breaks, choice labels/order, blanks, tables, diagrams, graphs, and formulas in their original reading order.

Do not silently correct spelling, normalize away meaningful punctuation, infer missing content, or generate answers. A suspected OCR spelling correction may be proposed for review, but the original recognition and source region must remain available. When text or visual fidelity is uncertain, hold the affected question or mark the uncertain region and provide an access-controlled original page/crop fallback. This fallback supplements extraction; it does not make an unreadable extraction acceptable as verified text.

## 5. Initial evaluation targets

Use the following as minimum pre-release gates on a frozen, manually transcribed corpus. Report each input/layout/question-format category separately; do not hide a failing category with a pooled average. These are engineering targets, not a claim that the current implementation meets them.

| Measure | Minimum target | Failure behavior |
|---|---:|---|
| Question boundary precision and recall | 98% each | Hold affected page/questions when segmentation is uncertain |
| Source page association | 100% | Never publish an item with a known-wrong page; route missing provenance to review |
| Multiple-choice option association and order | 99% exact questions | Hold questions with missing, duplicated, reordered, or misassociated options |
| Question-format classification | 98% macro-F1 across true/false, multiple choice, short answer, and fill-in-the-blank | Keep low-confidence cases as unknown; do not invent a type |
| Printed text character error rate (CER) | <=1% on clean digital/print sources; <=3% on supported scans | Hold a question exceeding its category threshold or with a critical-token mismatch |
| Critical-token exactness | 100% for negation, numbers, units, choice labels, and math operators in published content | Hold the question if any critical token is wrong or uncertain |
| Annotated visual-element detection recall | >=98% for diagrams, graphs, tables, and formulas in the labeled corpus | Hold affected pages if an annotated element is missed |
| Visual-element preservation | 100% of detected elements in published questions have a valid source link and are not rendered misleadingly | Hold if an element is omitted, detached, or rendered misleadingly |
| Original source fallback | 100% of published questions retain a valid document/page reference; crop required when the region is separable and text alone is insufficient | Block publication if neither readable content nor authorized source fallback is available |

CER alone is insufficient: a single changed `not`, minus sign, decimal point, exponent, unit, or answer-choice label can reverse meaning. Evaluate these critical tokens independently. Do not promise zero spelling errors; require measured results, explicit uncertainty, and human/source fallback instead.

## 6. Metadata rules

AI can suggest grade, subject, topic/subtopic, source title, year, and curriculum only when supported by document evidence. Each suggestion should ideally retain its evidence span or reason. If evidence is absent, leave the field unknown or request user input. Admin approval is required for taxonomy changes and taxonomy-level corrections.

## 7. Human review queue

Queue items should include:
- source document and page;
- extracted candidate;
- original crop/page image;
- reason for review;
- confidence indicators;
- prior corrections and duplicate candidates;
- available actions: edit, publish, reject, retry, or escalate.

Reviewers should not need to reconstruct context from scratch. Every decision should be auditable.

## 8. User corrections

Users can correct their own contributions within defined limits. Corrections to public taxonomy, shared metadata, or disputed source information should be routed through an approval process. Preserve version history and contributor attribution. Avoid allowing an uploader to erase evidence of prior abuse or policy violations.

## 9. Duplicate detection

Detect likely duplicates using exact checksums for identical files and text/fingerprint similarity for question candidates. Group duplicates rather than discarding them. Preserve source attribution and let the interface show that a question appears in multiple source documents. Do not merge two questions automatically solely because they share common wording.

## 10. Evaluation set

Build a manually reviewed evaluation corpus that includes:
- clean digital PDFs;
- scanned and low-resolution PDFs;
- multi-column pages;
- math notation and symbols;
- true/false items;
- multiple-choice items with labels, wrapped choices, and options spanning lines/pages;
- short-answer prompts and answer-space cues;
- fill-in-the-blank questions with multiple blanks;
- diagrams, graphs, tables, and answer choices;
- formulas with fractions, superscripts/subscripts, roots, signs, and units;
- faint print, skew, bleed-through, handwriting, and mixed text/image pages;
- question numbering across page breaks;
- English documents;
- Amharic documents with limited-support labeling;
- Word and PowerPoint inputs;
- malformed and unsupported files.

Track extraction completeness, question-boundary accuracy, source-page correctness, diagram preservation, correction rate, and processing latency. Keep representative examples of failures for regression tests.

## 11. Release gates

Before enabling a model or changing pipeline logic:
1. run the evaluation corpus;
2. compare against the current baseline;
3. inspect regressions by document category;
4. verify provenance;
5. check latency and quota implications;
6. review licensing and privacy terms;
7. stage rollout and monitor;
8. preserve rollback capability.

## 12. Avoiding answer leakage

The initial platform excludes uploaded answers and answer keys. The pipeline should not intentionally extract answer keys into a separate public resource. If prohibited answer material is detected, route it according to content policy and moderation controls. Do not silently rewrite an answer key into an apparent question-only document without preserving a transparent moderation record.
