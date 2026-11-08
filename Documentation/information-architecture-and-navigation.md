# Information Architecture and Navigation

## 1. Product structure

Recommended top-level navigation:
- Home
- Search
- Browse
- Collections
- Resources
- Notifications
- Profile

Administrator-only navigation:
- Overview
- Uploads and processing
- Review queue
- Reports and moderation
- Users
- Taxonomy
- Resources and announcements
- System health
- Backups and exports
- Audit log
- Settings

Navigation should adapt to mobile screen width without hiding core search or upload actions.

## 2. Unified search

Use one search page with tabs for Questions, Documents, and Resources. This avoids separate competing systems for exams and questions while letting users narrow result types.

Search filters:
- grade;
- subject;
- topic/subtopic;
- source test/document title;
- academic year;
- curriculum;
- resource type;
- language where supported;
- school/audience when relevant and authorized.

Show active filters clearly and make clearing filters easy. Search results must preserve permission boundaries.

## 3. Home page

The homepage is search-first. The primary task is finding a question or resource. Secondary sections may include:
- continue studying / recently viewed;
- recently added questions;
- browse by grade and subject;
- recommendations based on the grade selected during onboarding;
- notes and articles;
- announcements and opportunities;
- personal collections and bookmarks;
- contribution count and streak.

Do not fill the homepage with leaderboard gamification at the expense of search.

The initial mobile view keeps search prominent, shows log-in/sign-up actions in the header, and uses a four-item bottom bar for Home, Search, Upload, and Profile. Question cards use the source test title, grade/year when known, a short question excerpt, contributor attribution, and posting date. Unknown metadata stays unlabelled rather than being inferred.

## 4. Question detail

A question page should put the question content first, followed by source provenance, metadata, related items, and community interactions. The original document must be one clear action away when the user has permission.

For diagrams or complex math, show the source crop or page image alongside extracted text. Do not force a lossy text-only rendering where the original layout is important.

## 5. Document detail

Display:
- title and known metadata;
- contributor and upload date;
- processing state where relevant;
- original document viewer;
- extracted question list;
- question-to-page mapping;
- download/open action;
- report and share controls;
- comments or notes if supported for this resource type.

## 6. Upload experience

Use a guided flow:
1. Select file.
2. Validate file type and size client-side for convenience.
3. Upload securely.
4. Enter or confirm title and known metadata.
5. Select resource type and audience.
6. Confirm policy (including no answers/answer keys).
7. Submit and show asynchronous processing status.
8. Notify user when processing completes or review is needed.

Client-side validation is not a security boundary; the server must repeat checks.

## 7. Status language

Use explicit states such as:
- Uploading
- Security check
- Processing
- Partially published
- Needs review
- Published
- Failed — retrying
- Failed — administrator review
- Quarantined

Do not display “published” for a document that is still in quarantine or awaiting a required safety decision.

## 8. Accessibility

- Keyboard navigation for core workflows.
- Visible focus indicators.
- Proper labels for inputs and controls.
- Sufficient contrast and readable type.
- Meaningful alt text for diagrams when available.
- Do not communicate status through color alone.
- Preserve math notation and document page context where possible.

## 9. Responsive and offline behavior

The app is mobile-first, responsive on desktop, and installable as a PWA. Offline reading/search is limited to saved items and cached resources that are safe to cache. Do not cache private files without a deliberate device-storage policy. Offline comments and notes are excluded from the initial scope.
