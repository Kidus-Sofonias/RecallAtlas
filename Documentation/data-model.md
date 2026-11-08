# Data Model — Initial Logical Schema

This is a logical model for implementation planning, not a final migration file. Field types, constraints, indexes, and deletion behavior must be finalized during schema design.

## 1. Core entities

### `users`
- `id`
- `auth_subject`
- `email` (private)
- `display_name`
- `created_at`, `updated_at`
- `status`
- `deletion_requested_at`
- profile preferences

### `schools`
- `id`
- `name`
- `region_or_city` (optional)
- `verification_status` (initially unverified/self-reported)
- timestamps

### `user_school_memberships`
- `user_id`
- `school_id`
- `grade`
- `membership_status`
- `is_verified` (false initially unless verified by a future process)

### `documents`
- `id`
- `uploader_id`
- `school_id` (nullable depending on audience/source)
- `title`
- `resource_type`
- `language`
- `academic_year`
- `curriculum`
- `subject_id`
- `grade`
- `audience_policy`
- `storage_object_key`
- `checksum`
- `mime_type`
- `file_size`
- `page_count`
- `security_status`
- `processing_status`
- `publication_status`
- timestamps and version

### `questions`
- `id`
- `document_id`
- `source_page_start`, `source_page_end`
- `source_location` or bounding box/crop reference
- `question_number_as_printed` (optional)
- `extracted_text`
- `rendering_data` or structured blocks
- `quality_status`
- `extraction_method`
- `extraction_version`
- `quality_signals`
- `published_at`
- timestamps

### `subjects`, `topics`, `topic_aliases`
Controlled taxonomy, with admin approval for shared changes.

### `question_topics`
Many-to-many mapping from questions to topics.

### `resources`
For articles, notes, announcements, opportunities, and other non-question resources. May share document attachment infrastructure.

### `comments`
- `id`
- `author_id`
- `target_type`
- `target_id`
- `parent_comment_id` for replies
- `body`
- moderation status
- timestamps

### `reports`
- `id`
- `reporter_id`
- `target_type`
- `target_id`
- `reason`
- `details`
- `status`
- reviewer and decision metadata
- timestamps

### `collections`, `collection_items`
Named private user collections and ordered saved items.

### `bookmarks`
User-to-content relationships where a separate collection is not required.

### `notifications`, `notification_preferences`
Durable in-app notifications, delivery status, category, urgency, audience, and user preferences.

### `processing_jobs`
- `id`
- `document_id`
- `job_type`
- `status`
- `attempt_count`
- `next_attempt_at`
- `started_at`, `finished_at`
- `error_category`
- `idempotency_key`
- `worker_version`

### `audit_events`
Actor, action, target, timestamp, outcome, and safe metadata. Avoid storing secrets or unnecessary personal content.

### `document_versions`
Versioned metadata/file references and history needed for edit/review/audit.

### `outbox_events` (recommended pattern)
Optional transactional outbox to reliably deliver queue/notification events after database commits.

## 2. Relationships

- A user can upload many documents.
- A document can produce many questions.
- A question belongs to one source document version and may have multiple topic labels.
- A document can have multiple versions.
- A user can have multiple collections; each collection contains multiple items.
- Comments can target questions, documents, resources, or parent comments.
- Reports can target multiple content types.
- Processing jobs are associated with documents and can create many question candidates.
- Audit events reference actor and target identifiers without relying on hard deletes.

## 3. Key constraints

- Unique object key per stored object.
- Checksum and size recorded for every accepted original file.
- Published questions require a valid source document reference.
- Question source pages must be valid for the document version when page count is known.
- Only permitted statuses can transition to `published`.
- No answer-key entity or public answer field in the initial schema.
- User collection membership must enforce ownership.
- Taxonomy identifiers must be stable; display names can change through audited admin action.
- Job idempotency must prevent duplicate writes on retries.

## 4. Indexes to consider

- Foreign keys and common ownership filters.
- Document status and created timestamp.
- Questions by document and source page.
- Grade/subject/topic/year/curriculum filters.
- Full-text search vectors for published question text and resource text.
- Vector index for approved embeddings if pgvector is selected.
- Notifications by recipient and unread state.
- Reports by status and created timestamp.
- Jobs by status, next attempt, and priority.
- Audit events by actor, target, and time.

## 5. Deletion and anonymization

Use explicit retention and deletion rules. Account deletion may anonymize approved academic contributions rather than deleting the archive, where appropriate. Remove or anonymize personal profile information, invalidate sessions, and record a minimal audit event. Backups have separate expiration policies; deleting live data does not instantly remove every backup copy.

## 6. Privacy considerations

Avoid storing private browsing events indefinitely. Activity tracking should be purpose-limited. Admin dashboards can provide detailed operational records, but access should be audited and regular users must not be able to query another user's private activity.

## 7. Implemented search and preferences

The current schema adds `documents.subject_id`, a `user_subject_preferences` join table, and `resources` for admin-authored articles. User profiles also store `preferred_grade`. The migration `f8b26d3c9e40` creates PostgreSQL GIN full-text indexes for questions, documents, subjects, and resources. SQLite FTS5 is not supported. Only reliable questions from completed documents and published articles are indexed for normal search. Embeddings remain a separate capability and are not combined with the Explore ranking.
