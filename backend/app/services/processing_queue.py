import logging
import socket
import threading
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document, ProcessingStatus
from app.models.job import JobStatus, ProcessingJob

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def worker_identifier() -> str:
    return f'{socket.gethostname()[:80]}:{uuid.uuid4()}'


def recover_expired_jobs(now: datetime | None = None) -> int:
    current_time = now or _now()
    recovered = 0
    with SessionLocal() as db:
        jobs = db.query(ProcessingJob).filter(
            ProcessingJob.status == JobStatus.running,
            ProcessingJob.lease_expires_at.is_not(None),
            ProcessingJob.lease_expires_at <= current_time,
        ).with_for_update(skip_locked=True).all()
        for job in jobs:
            if (job.attempt_count or 0) >= settings.processing_max_attempts:
                job.status = JobStatus.failed
                job.error_category = 'worker_lease_expired'
                job.finished_at = current_time
                document = db.query(Document).filter(Document.id == job.document_id).first()
                if document:
                    document.processing_status = ProcessingStatus.failed
            else:
                delay = min(
                    settings.processing_retry_base_seconds * (2 ** max((job.attempt_count or 1) - 1, 0)),
                    3600,
                )
                job.status = JobStatus.queued
                job.error_category = 'worker_lease_expired'
                job.available_at = current_time + timedelta(seconds=delay)
            job.worker_id = None
            job.lease_expires_at = None
            recovered += 1
        db.commit()
    return recovered


def _claim_job(db, job: ProcessingJob, worker_id: str, current_time: datetime) -> bool:
    claimed = db.query(ProcessingJob).filter(
        ProcessingJob.id == job.id,
        ProcessingJob.status == JobStatus.queued,
        or_(ProcessingJob.available_at.is_(None), ProcessingJob.available_at <= current_time),
        ProcessingJob.attempt_count < settings.processing_max_attempts,
    ).update({
        ProcessingJob.status: JobStatus.running,
        ProcessingJob.attempt_count: func.coalesce(ProcessingJob.attempt_count, 0) + 1,
        ProcessingJob.started_at: current_time,
        ProcessingJob.finished_at: None,
        ProcessingJob.worker_id: worker_id,
        ProcessingJob.lease_expires_at: current_time + timedelta(seconds=settings.processing_lease_seconds),
    }, synchronize_session=False)
    if claimed != 1:
        db.rollback()
        return False
    document = db.query(Document).filter(Document.id == job.document_id).first()
    if document and document.security_status == 'clean':
        document.processing_status = ProcessingStatus.processing
    db.commit()
    return True


def claim_job(job_id: str, worker_id: str, now: datetime | None = None) -> str | None:
    current_time = now or _now()
    recover_expired_jobs(current_time)
    with SessionLocal() as db:
        job = db.query(ProcessingJob).filter(
            ProcessingJob.id == uuid.UUID(job_id),
        ).with_for_update(skip_locked=True).first()
        if not job or not _claim_job(db, job, worker_id, current_time):
            return None
        return str(job.id)


def claim_next_job(worker_id: str, now: datetime | None = None) -> str | None:
    current_time = now or _now()
    recover_expired_jobs(current_time)
    with SessionLocal() as db:
        job = db.query(ProcessingJob).filter(
            ProcessingJob.status == JobStatus.queued,
            or_(ProcessingJob.available_at.is_(None), ProcessingJob.available_at <= current_time),
            ProcessingJob.attempt_count < settings.processing_max_attempts,
        ).order_by(
            ProcessingJob.available_at.asc(),
            ProcessingJob.created_at.asc(),
        ).with_for_update(skip_locked=True).first()
        if not job:
            return None
        if not _claim_job(db, job, worker_id, current_time):
            return None
        return str(job.id)


def renew_job_lease(job_id: str, worker_id: str) -> bool:
    now = _now()
    with SessionLocal() as db:
        updated = db.query(ProcessingJob).filter(
            ProcessingJob.id == uuid.UUID(job_id),
            ProcessingJob.status == JobStatus.running,
            ProcessingJob.worker_id == worker_id,
        ).update({
            ProcessingJob.lease_expires_at: now + timedelta(seconds=settings.processing_lease_seconds),
        }, synchronize_session=False)
        db.commit()
        return updated == 1


def _schedule_retry(job_id: str, worker_id: str, error: Exception) -> None:
    current_time = _now()
    with SessionLocal() as db:
        job = db.query(ProcessingJob).filter(
            ProcessingJob.id == uuid.UUID(job_id),
            ProcessingJob.status == JobStatus.running,
            ProcessingJob.worker_id == worker_id,
        ).with_for_update().first()
        if not job:
            return
        document = db.query(Document).filter(Document.id == job.document_id).first()
        job.error_category = type(error).__name__[:128]
        job.worker_id = None
        job.lease_expires_at = None
        if (job.attempt_count or 0) < settings.processing_max_attempts:
            delay = min(
                settings.processing_retry_base_seconds * (2 ** max((job.attempt_count or 1) - 1, 0)),
                3600,
            )
            job.status = JobStatus.queued
            job.available_at = current_time + timedelta(seconds=delay)
            if document:
                document.processing_status = ProcessingStatus.pending
        else:
            job.status = JobStatus.failed
            job.finished_at = current_time
            if document:
                document.processing_status = ProcessingStatus.failed
        db.commit()


def run_claimed_job(job_id: str, worker_id: str) -> None:
    from app.services.extraction import extract_job

    stopped = threading.Event()

    def maintain_lease() -> None:
        interval = max(settings.processing_lease_seconds // 3, 10)
        while not stopped.wait(interval):
            try:
                if not renew_job_lease(job_id, worker_id):
                    logger.warning('Processing job %s no longer belongs to worker %s', job_id, worker_id)
                    return
            except Exception:
                logger.exception('Could not renew lease for processing job %s', job_id)
                return

    heartbeat = threading.Thread(target=maintain_lease, name=f'job-lease-{job_id}', daemon=True)
    heartbeat.start()
    try:
        extract_job(job_id, worker_id)
    except Exception as exc:
        logger.exception('Processing job %s failed (%s)', job_id, type(exc).__name__)
        _schedule_retry(job_id, worker_id, exc)
    finally:
        stopped.set()
        heartbeat.join(timeout=2)


def process_one_job(worker_id: str) -> bool:
    job_id = claim_next_job(worker_id)
    if job_id is None:
        return False
    run_claimed_job(job_id, worker_id)
    return True
