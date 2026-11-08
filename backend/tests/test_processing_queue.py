import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document, ProcessingStatus
from app.models.job import JobStatus, ProcessingJob
from app.models.question import Question
from app.models.user import User
from app.services import extraction
from app.services.processing_queue import (
    _schedule_retry,
    claim_job,
    claim_next_job,
    recover_expired_jobs,
    run_claimed_job,
    worker_identifier,
)
from app.storage.files import save_bytes


def _queued_job():
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == 'test-admin@example.test').one()
        document_id = uuid.uuid4()
        storage_key = f'uploads/{document_id}/original.pdf'
        db.add(Document(
            id=document_id,
            uploader_id=user.id,
            title='Queue test',
            original_filename='queue.pdf',
            mime_type='application/pdf',
            file_size=5,
            storage_object_key=storage_key,
            checksum='test',
            security_status='clean',
            processing_status=ProcessingStatus.pending,
        ))
        job = ProcessingJob(
            document_id=document_id,
            job_type='extract',
            status=JobStatus.queued,
            attempt_count=0,
            available_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add(job)
        db.commit()
        job_id = str(job.id)
    save_bytes(storage_key, b'pdf test')
    return job_id, document_id


def test_worker_claims_durable_job_and_marks_completion(monkeypatch):
    job_id, document_id = _queued_job()
    monkeypatch.setattr(extraction, 'extract_candidates', lambda data, mime: (
        1,
        [{
            'text': 'A test question?',
            'question_type': 'short_answer',
            'content': {'blocks': [], 'source_page': 1},
            'signals': {'ocr_confidence': None, 'requires_review': True, 'reasons': []},
        }],
    ))

    worker_id = 'queue-test-worker'
    assert claim_job(job_id, worker_id) == job_id
    run_claimed_job(job_id, worker_id)
    with SessionLocal() as db:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == uuid.UUID(job_id)).one()
        document = db.query(Document).filter(Document.id == document_id).one()
        assert job.status == JobStatus.completed
        assert job.attempt_count == 1
        assert job.worker_id is None
        assert job.finished_at is not None
        assert document.processing_status == ProcessingStatus.completed
        assert db.query(Question).filter(Question.document_id == document_id).count() == 1


def test_failed_job_retries_with_backoff_then_becomes_terminal(monkeypatch):
    job_id, document_id = _queued_job()
    monkeypatch.setattr(settings, 'processing_max_attempts', 2)
    monkeypatch.setattr(settings, 'processing_retry_base_seconds', 1)

    worker_id = worker_identifier()
    claimed = claim_next_job(worker_id)
    assert claimed == job_id
    _schedule_retry(job_id, worker_id, RuntimeError('transient'))
    with SessionLocal() as db:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == uuid.UUID(job_id)).one()
        assert job.status == JobStatus.queued
        assert job.attempt_count == 1
        assert job.error_category == 'RuntimeError'
        assert job.available_at > datetime.now(timezone.utc).replace(tzinfo=None)

    with SessionLocal() as db:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == uuid.UUID(job_id)).one()
        job.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    worker_id = worker_identifier()
    assert claim_next_job(worker_id) == job_id
    _schedule_retry(job_id, worker_id, RuntimeError('still failing'))

    with SessionLocal() as db:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == uuid.UUID(job_id)).one()
        document = db.query(Document).filter(Document.id == document_id).one()
        assert job.status == JobStatus.failed
        assert job.attempt_count == 2
        assert job.finished_at is not None
        assert document.processing_status == ProcessingStatus.failed


def test_expired_worker_lease_returns_job_to_retry_queue(monkeypatch):
    job_id, document_id = _queued_job()
    monkeypatch.setattr(settings, 'processing_max_attempts', 3)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == uuid.UUID(job_id)).one()
        job.status = JobStatus.running
        job.attempt_count = 1
        job.worker_id = 'dead-worker'
        job.lease_expires_at = now - timedelta(seconds=1)
        db.commit()

    assert recover_expired_jobs(now) == 1
    with SessionLocal() as db:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == uuid.UUID(job_id)).one()
        assert job.status == JobStatus.queued
        assert job.worker_id is None
        assert job.lease_expires_at is None
        assert job.error_category == 'worker_lease_expired'
        assert job.available_at > now.replace(tzinfo=None)


def test_exhausted_expired_lease_is_terminal(monkeypatch):
    job_id, document_id = _queued_job()
    monkeypatch.setattr(settings, 'processing_max_attempts', 2)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == uuid.UUID(job_id)).one()
        job.status = JobStatus.running
        job.attempt_count = 2
        job.worker_id = 'dead-worker'
        job.lease_expires_at = now - timedelta(seconds=1)
        db.commit()

    assert recover_expired_jobs(now) == 1
    with SessionLocal() as db:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == uuid.UUID(job_id)).one()
        document = db.query(Document).filter(Document.id == document_id).one()
        assert job.status == JobStatus.failed
        assert job.error_category == 'worker_lease_expired'
        assert document.processing_status == ProcessingStatus.failed
