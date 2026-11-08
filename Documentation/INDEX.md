# Recall Atlas — Documentation Index

**Brand:** Recall Atlas  
**Tagline:** *Find it. Understand it. Remember it.*

## Document map

The documents are stored directly in this folder; the numbered folders described in the original planning pack were never created.

| Topic | Documents |
|---|---|
| Product, roles, and journeys | [01-product-vision-and-scope.md](./01-product-vision-and-scope.md), [02-functional-requirements.md](./02-functional-requirements.md), [03-user-roles-and-permissions.md](./03-user-roles-and-permissions.md), [key-user-journeys.md](./key-user-journeys.md) |
| Brand and navigation | [brand-identity.md](./brand-identity.md), [brand-usage-and-copy.md](./brand-usage-and-copy.md), [information-architecture-and-navigation.md](./information-architecture-and-navigation.md) |
| Extraction and search | [document-processing-pipeline.md](./document-processing-pipeline.md), [quality-and-review.md](./quality-and-review.md), [search-design.md](./search-design.md) |
| Architecture and data | [system-architecture.md](./system-architecture.md), [repository-and-environments.md](./repository-and-environments.md), [data-model.md](./data-model.md), [api-contracts.md](./api-contracts.md), [postgresql-setup.md](./postgresql-setup.md) |
| Security and governance | [authentication-and-admin-security.md](./authentication-and-admin-security.md), [file-security-and-moderation.md](./file-security-and-moderation.md), [privacy-retention-and-content-policy.md](./privacy-retention-and-content-policy.md), [terms-of-service.md](./terms-of-service.md) |
| Operations and launch | [admin-console-and-monitoring.md](./admin-console-and-monitoring.md), [backup-recovery-and-outages.md](./backup-recovery-and-outages.md), [hosting-costs-and-quotas.md](./hosting-costs-and-quotas.md), [metrics-and-launch-checklist.md](./metrics-and-launch-checklist.md) |
| Planning and status | [implementation-roadmap.md](./implementation-roadmap.md), [risks-and-open-decisions.md](./risks-and-open-decisions.md), [PROJECT_STATUS.md](../docs/PROJECT_STATUS.md) |
| Testing | [test-strategy-and-acceptance.md](./test-strategy-and-acceptance.md) |

## Status conventions

`docs/PROJECT_STATUS.md` is the implementation source of truth. This pack contains both implemented behavior and requirements that remain planned. Checklists use `[x]` only for behavior verified in code/tests; infrastructure provisioning, a live PostgreSQL test, operational ClamAV, legal review, restore testing, and the pilot remain incomplete until evidenced.

The initial SQLite implementation and historical SQLite migration branches are retained only as legacy/reference material. The active application, local development setup, migrations, and test harness now require PostgreSQL.
