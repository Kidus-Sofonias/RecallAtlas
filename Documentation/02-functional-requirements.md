# Functional Requirements

## 1. Accounts and profiles

- Users can register with email and password.
- Google sign-in is an optional authentication method, subject to the chosen provider and configuration.
- Email verification is required for appropriate account actions.
- Password reset uses expiring, rate-limited links.
- Users can select a school and grade; school affiliation is self-reported initially.
- Users can select grade/subject interests for personalized recommendations and notifications.
- Users can view and edit their own profile and contributions.
- Users can request account deletion.
- Public profiles may show contribution statistics, but not private browsing history or private collections.

## 2. Uploads and resources

Supported initial formats: PDF, common image formats, DOCX Word documents, and PPTX PowerPoint presentations. Legacy binary DOC/PPT files are not currently supported. The default maximum upload size is 10 MB; the backend limit is configurable through `MAX_UPLOAD_SIZE_MB` (1–100 MB), while runtime admin editing is not yet available.

Accepted resource types:
- past exams;
- class tests and quizzes;
- worksheets and assignments;
- practice tests;
- educational articles and study notes;
- other educational PDFs;
- announcements;
- opportunities;
- urgent academic information.

Uploaders must not submit answers or answer keys. The upload flow should state this policy clearly and provide a report path for prohibited material that is discovered after upload.

Every upload triggers an administrator notification. The file is validated, stored privately, scanned for security and policy risks, and then processed asynchronously. Suspicious or uncertain-safety files are quarantined and unpublished pending review.

## 3. Metadata

The system should support:
- title/source name;
- resource type;
- grade;
- subject;
- topic and subtopic;
- academic year;
- curriculum;
- school or source context;
- language;
- contributor;
- upload and processing timestamps;
- source file checksum and storage identifier;
- extraction status and quality indicators.

AI may suggest metadata only when evidence supports it. If the document has no title or the year cannot be established, the value remains unknown or the uploader is asked to supply it. AI must not fabricate metadata to fill blank fields.

## 4. Extraction and question publication

- Digital PDFs should use text extraction first.
- Scanned pages should use OCR and layout analysis.
- Difficult pages may be sent to a vision-capable model where configured and permitted.
- Extracted questions must retain page/source links.
- Diagrams, tables, equations, and answer-choice layouts must be preserved or linked to a source crop where text representation is unreliable.
- Quality checks operate at question level.
- Reliable questions may be published while uncertain questions from the same document are held for review.
- Failed jobs retry with bounded attempts, then become visible in an admin queue.
- Processing runs in the background; users do not need to keep the upload page open.

## 5. Search and browse

One unified search experience has three result tabs:
1. Questions
2. Documents
3. Resources

Search supports keyword and semantic retrieval from launch, with a keyword fallback if semantic search is unavailable. Filters include grade, subject, topic, source/test title, academic year, curriculum, and resource type. Search results must respect access permissions.

## 6. Question and document pages

A question page may show:
- extracted question text and formatting;
- choices where present;
- diagrams or source crops;
- grade, subject, topic, curriculum, and other known metadata;
- original source title and page;
- contributor attribution;
- original document open/download actions, subject to permissions;
- comments, notes, bookmark, share, report, and related content;
- view counts and contribution information where appropriate.

Do not show an answer field in the initial version.

Document pages show the original document and extracted question list, with source page references and processing status when relevant.

## 7. Study tools and resources

- Users can bookmark questions and resources.
- Users can create named private collections.
- Users can see recently viewed items and continue reading.
- Users can save items for later.
- Offline support is limited to saved material and supported reading/search experiences; the whole archive is not downloaded.
- Offline notes/comments are not included initially.
- Topic pages consolidate questions and links to source documents.
- Related content includes same-topic questions, questions from the same test, and relevant resources.

## 8. Community and engagement

- Registered users can comment on questions and resources.
- Comments can be reported; spam controls and moderation tools are required.
- Users can add notes where the feature is defined; distinguish personal notes from public comments.
- Uploaders can edit their own contributions within defined rules.
- Deletion of published contributions requires admin approval; retain versions/audit trail.
- Users can report documents, questions, resources, comments, or accounts.
- Reports enter a queue and are not treated as proof by themselves.
- Contribution metrics include uploads/resources, views, streaks, and achievements.
- Leaderboards should reward quality, approved corrections, and useful engagement rather than raw upload count alone.

## 9. Notifications

Notification examples:
- A new Grade 11 Mathematics resource can notify users interested in that grade and subject.
- A reply to a comment notifies the original commenter.
- An urgent school-wide announcement notifies all relevant users.

Provide in-app notifications and optional email. Important events may be immediate; routine events can be digested. Users can mute routine categories. Security and account-protection notices should not be silently suppressed.

## 10. Administration

The global administrator can:
- search and inspect users and their platform records;
- inspect uploads, extracted questions, resources, comments, reports, and moderation decisions;
- review suspicious uploads and uncertain extractions;
- manage taxonomy and approved corrections;
- manage quotas, file-size limits, and processing controls;
- inspect queue health, storage use, errors, quota warnings, and outages;
- manage announcements and notifications;
- export data and execute recovery procedures;
- inspect audit logs for sensitive actions.

No school-level admin role is required for the first release.

## 11. Account deletion and data retention

When a user requests deletion, delete personal data where appropriate while retaining approved academic contributions in anonymized form if legally and operationally appropriate. Activity logs should be retained for one year and then deleted or aggregated unless a documented legal, security, or moderation reason requires longer retention. Backup expiration and deletion must be documented.
