# User Roles, Permissions, and Access Rules

## 1. Role model

### Anonymous visitor
May access only explicitly public landing pages and public product information. The initial archive is intended for registered users; do not expose restricted source files through anonymous routes.

### Registered user
Can search and read content they are authorized to access; upload permitted academic resources; edit their own contributions; comment; bookmark; create private collections; report content; manage preferences; and request account deletion.

### Global administrator
Can manage the entire platform, including users, content, moderation, taxonomy, system configuration, processing queues, security alerts, backups, and audit records. Administrative actions must be logged.

No school-level administrator role is planned for the initial release.

## 2. Access-control principles

- Enforce permissions on the server for every protected resource and action.
- Do not rely on hiding UI buttons as access control.
- Use private object storage for original files.
- Serve private source files through authorized API routes, or issue short-lived signed URLs only after an authorization check.
- Never use predictable public URLs as the sole protection for private files.
- Apply the same permission logic to search results, API responses, thumbnails, previews, exports, and downloads.
- Re-check access on each API-streamed source request; if signed URLs are added later, keep their expiry short.
- Log privileged actions and relevant access-control changes.

## 3. School and audience model

Users select a school during onboarding, but affiliation is self-reported initially. Do not label a school as verified unless a future verification process exists.

Default visibility is all registered users, subject to platform access rules. Uploaders may choose among supported audiences such as whole-school or selected users where permissions and sharing rules permit it. The authorization model must be explicit rather than inferred from a frontend filter.

## 4. User privacy

Regular users must not see other users' private browsing history, private collections, or full activity timelines. Public profile statistics can include permitted aggregate metrics such as contributions and views.

The administrator can access detailed records needed for moderation, support, security, and platform operations. This access should be limited to legitimate operational use, logged, and governed by a clear privacy policy.

## 5. Content ownership and contribution edits

- Users may edit their own contributions subject to versioning and moderation rules.
- Deletion of published contributions requires admin approval.
- Preserve prior versions or a minimal audit record to investigate abuse and recover from accidental edits.
- If a contributor account is deleted, approved content may be anonymized instead of removed, subject to policy and applicable law.
- Never expose hidden personal identifiers in public metadata or download files unintentionally.

## 6. Permission test cases

Test at minimum:
1. User A cannot read a private collection belonging to User B.
2. User A cannot fetch a restricted file by guessing its object key.
3. A search query cannot reveal titles or snippets from unauthorized content.
4. A deleted or revoked user cannot obtain new source access.
5. A regular user cannot call administrator APIs.
6. A contributor cannot approve their own flagged content when policy requires admin review.
7. A user cannot edit another user's contribution by changing an ID in the request.
8. Public profile endpoints omit private activity and collections.
9. Exports follow the same authorization rules as the UI.
10. Admin actions create audit records.
