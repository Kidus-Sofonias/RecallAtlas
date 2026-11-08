# Recall Atlas — Project Documentation Pack

**Tagline:** *Find it. Understand it. Remember it.*  
**Document set:** Product, architecture, implementation, operations, and governance  
**Status:** Product/engineering specification. The active codebase and completed items are tracked in [docs/PROJECT_STATUS.md](../docs/PROJECT_STATUS.md).

## What Recall Atlas is

Recall Atlas is a multi-school academic resource platform centered on a searchable archive of past questions and their original source documents. Students and educators can contribute tests and learning materials, while document-processing services extract individual questions, preserve provenance, and make the collection searchable. The platform also supports study notes, educational articles, announcements, opportunities, comments, bookmarks, collections, notifications, and a moderation/admin console.

## How to use this pack

Read [01-product-vision-and-scope.md](./01-product-vision-and-scope.md) first, then [02-functional-requirements.md](./02-functional-requirements.md). The engineering sequence is in [implementation-roadmap.md](./implementation-roadmap.md).

Documents are stored flat in this directory; see [INDEX.md](./INDEX.md) for the complete map.

## Core product principles

1. **Source truth:** retain the original upload and trace extracted questions to source page/document/position.
2. **No answer keys in the initial version:** users must not upload answers or answer keys; the initial platform does not generate or publish answers.
3. **Quality over completeness:** publish questions that pass quality checks; hold uncertain questions for review instead of silently guessing.
4. **Private by default at the storage layer:** original files are private objects; access is authorized and time-limited.
5. **Human governance:** AI can suggest metadata and flag uncertainty, but administrators govern taxonomy changes and risky-content decisions.
6. **Free-first with explicit limits:** prefer free tiers where practical, but never assume a free service is permanent or suitable for durable production without validation.
7. **Small end-to-end MVP first:** make upload → secure storage → extraction → provenance → search work reliably before adding broad social features.
8. **Explain uncertainty:** unknown metadata remains unknown; the system must not fabricate missing title, year, curriculum, or source.
9. **Respect privacy:** admins have necessary operational visibility with audit logs; ordinary users cannot inspect another user's private activity.
10. **Multi-school foundation:** support multiple schools from the data model onward, while recognizing that initial school membership is self-reported and not verified.

## Decisions vs. open questions

PostgreSQL is the required database in development, tests, and deployment. The hosting provider, private object-storage provider, OCR/vision models, legal/copyright language, mandatory MFA policy, future school verification, recovery objectives, and long-term backup capacity remain open.

## Suggested starting point

The current implementation is beyond the initial foundation but is not production-ready. Review [docs/PROJECT_STATUS.md](../docs/PROJECT_STATUS.md) for completed work and remaining release blockers before choosing the next roadmap item.
