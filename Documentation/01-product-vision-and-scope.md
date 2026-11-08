# Product Vision and Scope

## 1. Product overview

Recall Atlas is a multi-school academic resource platform whose foundation is a reliable, searchable question archive. It accepts past exams, class tests, quizzes, worksheets, practice tests, study notes, educational articles, and relevant academic announcements or opportunities. Its defining capability is to turn source documents into individually discoverable questions while retaining links to the original source.

The platform is not merely a file drive. It provides extraction, structured metadata, source traceability, unified search, study organization, contribution signals, community discussion, and global administration.

## 2. Problem statement

Academic questions and learning resources are often scattered across personal devices, messaging groups, folders, and printed papers. Students may know that a useful question exists but cannot find it, identify its topic, or recover its source document. A file archive alone does not solve this because it searches only at document level and often loses the structure of individual questions.

Recall Atlas addresses this by:
- centralizing resources from participating school communities;
- extracting question-level content from documents;
- organizing content by grade, subject, topic, source, year, and curriculum when known;
- preserving source provenance and original documents;
- offering keyword and semantic discovery;
- enabling users to save, discuss, and report resources;
- giving administrators tools to manage quality, safety, and platform operations.

## 3. Primary users

### Students
Search questions and resources, browse topics, save material, follow interests, comment, download allowed documents, and contribute materials they are permitted to share.

### Teachers and educators
Find prior tests and worksheets, contribute resources, correct metadata or extracted text, and help improve the archive. The initial role model does not introduce school-level administrator roles.

### Contributors
Any registered user may upload, subject to validation, safety screening, platform policies, and moderation. School affiliation is self-reported initially and should not be presented as verified.

### Global system administrator
Oversees all schools, users, uploads, extracted questions, resources, reports, comments, security alerts, processing queues, system settings, and audit records.

## 4. Product goals

1. Make past questions searchable at question level.
2. Preserve reliable links between extracted questions and original source documents.
3. Make the upload and extraction pipeline robust, asynchronous, and observable.
4. Avoid publishing low-confidence extractions as if they were correct.
5. Support multiple schools without requiring separate deployments.
6. Build a useful archive before expanding into social and study features.
7. Operate with a free-first budget while controlling quotas and avoiding fragile storage assumptions.
8. Give administrators clear oversight without exposing private user activity to other users.

## 5. Non-goals for the initial release

- Uploading, publishing, or generating answer keys.
- Requiring teachers or school clubs to approve every upload as a school-level admin.
- Training a proprietary OCR or vision model from scratch.
- Full offline access to the entire archive.
- Offline commenting and notes.
- Claiming formal verification of school membership.
- Guaranteeing support for all Amharic, mathematical, or diagram extraction cases before benchmark results exist.
- Building every planned social feature before the core archive works.

## 6. Success definition

The first meaningful success is a user can upload a representative academic document, the system safely stores it, extracts reliable questions with source locations, holds uncertain items for review, and makes published questions discoverable through search. A second user can find a question, inspect its context, and open or download the original document if authorized.

## 7. Product principles

- Preserve original source material.
- Never invent missing metadata.
- Publish reliable question-level results; isolate uncertain items.
- Keep user permissions explicit and server-enforced.
- Use AI to assist, not to obscure uncertainty.
- Make background processing understandable.
- Monitor costs and quotas.
- Design for mobile first and installable PWA use.
- Separate user-facing content from operational audit data.
- Build incrementally and test recovery, not only happy paths.
