# Key User Journeys

## Journey A: Find a question

1. User opens Recall Atlas and searches by phrase, topic, or source.
2. Results appear in Questions, Documents, and Resources tabs.
3. User narrows by grade, subject, topic, year, or curriculum.
4. User opens a question.
5. The page shows extracted text, known metadata, and source page.
6. User opens the original document or saves the question to a collection.
7. Related questions and source-document questions help the user continue discovery.

Acceptance criteria:
- Results respect authorization.
- Source provenance is visible when known.
- Unknown metadata is not invented.
- Search remains useful through keyword fallback if semantic retrieval is down.

## Journey B: Upload a past test

1. Registered user chooses Upload.
2. User selects a PDF, image, Word file, or PowerPoint within the configured limit.
3. Server validates actual file type and size.
4. The file is stored privately and security/policy checks run.
5. If suspicious or safety is uncertain, the file is quarantined and unpublished.
6. If safe, background extraction begins.
7. AI suggests question boundaries and metadata.
8. Quality gates publish reliable questions and hold uncertain questions for review.
9. The user can see status and return later.
10. The administrator receives the required upload notification and sees failures or review cases.

Acceptance criteria:
- No request waits synchronously for OCR/vision processing.
- Retries are bounded.
- Original file and checksum remain linked to extracted items.
- Failed jobs are visible in the admin queue.

## Journey C: Open a source document from a question

1. User opens a question result.
2. The page displays the source title and page/position when available.
3. User selects “View original.”
4. Server checks access and issues a short-lived signed URL or streams the file.
5. The viewer opens at the relevant page if supported.
6. User can download only if the document's sharing policy permits it.

Acceptance criteria:
- Guessing object IDs cannot bypass permissions.
- Signed links expire.
- Source link errors are logged and surfaced clearly.

## Journey D: Report a problem

1. User reports a question, document, resource, comment, or account.
2. User chooses a reason and may provide context.
3. The system creates a report and notifies moderators/admin.
4. The report is queued; content is not automatically removed solely because a report exists.
5. High-risk or policy-defined cases may be restricted pending review.
6. Admin reviews the content and report evidence.
7. Decision and rationale are recorded; relevant users are notified where appropriate.

## Journey E: Reply to a comment

1. User posts a comment.
2. Spam/rate controls apply.
3. Another user replies.
4. The original commenter receives an in-app notification and optional email according to preferences.
5. Users can report inappropriate comments.

## Journey F: Urgent announcement

1. Admin creates an announcement and marks its audience and urgency.
2. System validates permissions and logs the publication.
3. Notifications go to the intended audience; urgent school-wide notices can reach all relevant users.
4. Users can view the announcement in the resource feed.
5. Admin can inspect delivery/processing status where supported.

## Journey G: Administrator resolves a processing failure

1. Admin opens System Health or Processing Queue.
2. Failed jobs are grouped by status and error category.
3. Admin inspects safe diagnostic details and source references.
4. Admin retries, flags, or closes the job according to policy.
5. The action is audited.
6. Monitoring metrics reflect the final outcome.
