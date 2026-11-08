# Authentication and Administrator Security

## Implemented account model

Recall Atlas uses self-hosted email/password accounts. Passwords are hashed with scrypt; the API never stores or returns a password. Passwords must be 8–128 characters.

In explicit `APP_ENV=development` or `test` mode, registration creates an active user and signs them in immediately; email verification is skipped so local development works with `EMAIL_DEV_MODE=true`. Duplicate local registrations return `ACCOUNT_ALREADY_EXISTS`. Development registration does not grant administrator privileges.

Outside development/test, registration creates a pending account and sends a one-time email-verification link. Password reset links expire after one hour and are single-use. Verification links expire after 24 hours. Responses for existing and unknown addresses use the same public message. Configure Resend delivery before enabling registration or reset; with `EMAIL_DEV_MODE=true`, these endpoints return `EMAIL_DELIVERY_UNAVAILABLE` and do not create or modify an account.

Authentication endpoints:

- `GET /api/v1/auth/csrf` — issues the CSRF cookie/token pair.
- `POST /api/v1/auth/register` and `/register/resend-verification`.
- `POST /api/v1/auth/verify-email` with the token in the request body.
- `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, and `GET /api/v1/auth/me`.
- `POST /api/v1/auth/password-reset/request` and `/password-reset/complete`.

## Sessions and request protection

- Login issues a random opaque session token in an HTTP-only, `SameSite=Lax` cookie. Only its SHA-256 digest is stored in the database. Sessions expire after 14 days and logout revokes the current session.
- Password reset revokes all active sessions for the account.
- Unsafe `/api/v1` requests require a valid signed `ra_csrf` cookie and matching `X-CSRF-Token` header. Outside development/test, the request `Origin` must exactly match the origin in `FRONTEND_URL`. The signing key is `SECRET_KEY`.
- Serve the frontend and API through the same site/reverse proxy. Do not put backend credentials in frontend `VITE_*` variables.
- Auth endpoints are rate-limited to 10 unsafe requests per IP per 15 minutes; other API requests use the existing 100 requests per IP per minute limit. These limits are process-local; production deployments with multiple workers/instances must also enforce distributed limits at the gateway.

## Initial administrator

For local development, copy the root `.env.example` to `.env`, then set `ADMIN_EMAIL` and `ADMIN_INITIAL_PASSWORD` to values you choose before starting the API. The API hashes the password and creates an active administrator only when no administrator exists. A database lock serializes bootstrap across concurrent application starts. Subsequent restarts do not reset an existing administrator, even if the bootstrap environment values change. Do not send this password to the browser or store it in a frontend environment variable.

If an administrator already exists but cannot authenticate, bootstrap intentionally will not replace their credentials. Use an audited, access-controlled operational recovery procedure; do not solve this by running a bootstrap on every restart.

Development creates a random ephemeral CSRF signing key at process start if `SECRET_KEY` is not set; restarting invalidates outstanding CSRF tokens. Outside development/test, startup requires an explicitly configured `SECRET_KEY` of at least 32 characters, used to sign CSRF tokens. The API also requires successful database initialization and an administrator to exist or be created. Keep `APP_ENV` out of development/test for deployed environments.

## Authorization

- Search, published questions, and limited document metadata are public. Public document metadata excludes storage paths and file checksums.
- Upload initiation, bookmarks, collections, notifications, and community submissions require an active authenticated user and use the request identity, not the first database user.
- Collection and bookmark access is owner-scoped.
- Moderation, taxonomy writes, document processing, embeddings, backup export, and user/role administration require an authenticated administrator. The backup endpoint remains a development-only workflow and uses local paths.
- Authorized original-document preview/download routes stream private files through the API and enforce uploader/admin/published-content access. They do not issue signed object-storage URLs. Notification read mutations, MFA, broad administrator audit logging, and administrative recovery tooling remain incomplete; treat them as release blockers where required by the product or deployment.

## Before public launch

- Configure HTTPS, production `SECRET_KEY`, `FRONTEND_URL`, `ADMIN_EMAIL`, and a strong one-time `ADMIN_INITIAL_PASSWORD`; remove the initial password from the deployment environment after bootstrap where operationally practical.
- Rotate any previously exposed credentials. Do not rely on defaults from source code; secrets must come from an ignored local `.env` or a deployment secret manager.
- Set `EMAIL_DEV_MODE=false`, configure a valid Resend API key/from address, and test registration, verification, and reset delivery.
- Add distributed authentication rate limits and operational audit logs.
- Decide and implement MFA for administrators before exposing high-impact admin functions.
- Run PostgreSQL migration/backup restoration tests and verify ownership checks on private source routes. Private file delivery currently uses authorized API streaming, not expiring object links.
