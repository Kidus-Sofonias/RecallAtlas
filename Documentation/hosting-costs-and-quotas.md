# Hosting, Costs, and Quota Management

## 1. Budget philosophy

The project is free-first and accepts slower processing when that protects cost and reliability. “Free” is not treated as a permanent guarantee. Providers can change quotas, suspend services, introduce limits, or change terms. Re-check current terms before deployment and periodically thereafter.

## 2. Candidate services discussed

- Frontend: static hosting such as Netlify or Vercel may be considered.
- API: a suitable hosted service such as Render was considered.
- Database/auth: managed PostgreSQL and a provider such as Supabase were considered.
- File storage: Cloudflare R2 was a candidate.
- OCR/model experiments: Colab or Kaggle may be useful for experiments, not permanent production workers.
- Search: PostgreSQL full-text search and pgvector were considered.

These are candidates, not final selections. Do not assume a free tier currently provides every required feature.

## 3. Known operational cautions

- Some free web services sleep after inactivity.
- Ephemeral filesystems are not durable storage.
- Free databases may have expiry, storage, connection, or compute limits.
- Background OCR/vision processing may exceed serverless time or memory limits.
- Free-tier quotas can change.
- External AI services may send document data outside the platform and may impose usage or privacy constraints.

## 4. Storage architecture

- Store originals in private object storage, not in the API container's filesystem.
- Store object keys, checksums, sizes, and metadata in PostgreSQL.
- Generate previews and crops as derived objects.
- Use lifecycle policies and documented retention.
- Monitor total storage, request volume, and egress.
- Keep a backup copy in a separate location/provider where feasible and within capacity.

## 5. Processing quotas

Implement:
- maximum upload size (default 10 MB, configurable);
- per-user upload limits;
- bounded global worker concurrency;
- fair queue scheduling;
- retry caps and backoff;
- cost/usage accounting where available;
- alert thresholds;
- pause controls for nonessential processing.

When quota is near exhaustion, alert the admin and pause nonessential processing before a hard limit is exceeded. Preserve queue state and tell users when processing is delayed.

## 6. Capacity metrics

Monitor:
- storage used and growth rate;
- uploads per day;
- pages processed;
- OCR/vision calls;
- job queue length and oldest job age;
- average and p95 processing duration;
- retries and terminal failures;
- API/database utilization;
- email delivery failures;
- search latency;
- estimated monthly cost and free-tier headroom.

## 7. Migration planning

For every provider, document:
- export format;
- how to retrieve all original files;
- database dump procedure;
- secret/configuration inventory;
- DNS/domain migration;
- downtime strategy;
- restore test;
- cost trigger that prompts migration.

Avoid a design that requires one provider's proprietary AI model to remain available forever.
