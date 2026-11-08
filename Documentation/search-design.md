# Search and Discovery Design

## 1. Search goals

Search helps users discover reviewed individual questions, their source papers, and published articles. The current implementation is indexed lexical search; vector retrieval is a separate endpoint and is not currently blended into these Explore results.

## 2. Search result types

### Questions
Question text, known metadata, source title/page, topic, contributor, and permitted engagement indicators.

### Documents
Original source files with title, resource type, grade/subject, year, processing status where appropriate, and extracted question count when reliable.

### Articles
Admin-published articles with title, summary, body, and optional subject taxonomy.

## 3. Ranking approach

The indexed lexical search uses PostgreSQL full-text search with the `simple` configuration. It weights title matches above subject and question/body matches; academic-year matches receive a smaller boost. Search terms are tokenized and capped before being passed to the database.

Question results must be reliable and come from completed documents. Papers appear only when they have at least one reliable question. Articles must be published. Search results then receive small personalization boosts: +1.6 for the selected grade, +0.8 for one grade below, and +1.8 for a selected subject. Personalization only reorders lexical matches; it does not make unrelated results appear.

Do not let view count alone dominate relevance. Exclude quarantined, held, deleted, or unauthorized content from normal search.

## 4. Filters and facets

The implemented filters are grade (9–12) and subject. Facets are populated from the subject catalog; do not fabricate categories. Topic, source, curriculum, and language filters remain future work.

## 5. Keyword fallback

The Explore endpoints use lexical search and do not depend on embeddings. The separate hybrid-vector endpoint is not part of this ranking path.

## 6. Semantic index

PostgreSQL uses GIN full-text indexes for question, document, and resource text. Migrations and query code target PostgreSQL only. A PostgreSQL offline migration render has been verified; live PostgreSQL migration and integration tests remain pending.

## 7. Search performance

Track latency at median and p95, zero-result rate, click-through to useful content, query reformulation, and index freshness. No latency target or benchmark has been established.

## 8. Implemented API and client behavior

- `GET /api/v1/search?q=...` returns reviewed question results; it also accepts `grade`, `subject_id`, and optional personalization parameters.
- `GET /api/v1/search/suggestions?q=...` returns up to 12 question, paper, and article suggestions for two-or-more-character prefixes.
- `GET /api/v1/search/explore` returns separate `questions`, `papers`, and `articles` groups. With no query it shows recent content; filters and query are optional.
- `GET/PATCH /api/v1/auth/preferences` reads or updates grade and subject interests for the signed-in user.
- `GET/POST /api/v1/resources` and `GET /api/v1/resources/{id}` list, publish (admin only), and read articles.

The client debounces suggestions and supports keyboard selection. Results are limited per group; cursor pagination is not implemented yet.

## 9. Related content

Support:
- questions from the same source test;
- questions with the same topic/subtopic;
- semantically related questions;
- relevant study notes/articles;
- related documents.

Related content should respect permissions and should explain the relationship when useful, such as “same source document” or “same topic.”

## 10. Privacy and access

Apply authorization before returning search results. Snippets, counts, facets, semantic results, and related-item panels can leak private metadata and must follow the same access rules as direct content pages.
