import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.user import User
from app.models.question import Question, QualityStatus
from app.models.document import Document, ProcessingStatus
from app.models.job import JobStatus, ProcessingJob
from app.services.auth import require_admin
from app.services.malware_scan import ScanStatus, scan_bytes
from app.storage.files import move, read_bytes

router = APIRouter(prefix='/api/v1/admin', tags=['admin'])


class SecurityRejection(BaseModel):
    note: str = Field(min_length=4, max_length=1000)


@router.get('/quality-dashboard')
def quality_dashboard(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    counts = db.query(Question.quality_status, func.count(Question.id)).group_by(Question.quality_status).all()
    return {str(k.value if hasattr(k,'value') else k): v for k,v in counts}

@router.get('/documents')
def list_documents(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    docs = db.query(Document).all()
    return [{'id':str(d.id),'status':d.processing_status.value,'pages':d.page_count} for d in docs]

@router.get('/question-review-queue')
def question_review_queue(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = db.query(Question, Document).join(
        Document,
        Question.document_id == Document.id,
    ).filter(
        Question.quality_status == QualityStatus.held,
        Question.review_status == 'pending',
    ).order_by(
        Question.created_at.asc(),
    ).limit(100).all()
    return [{
        'id': str(question.id),
        'document_id': str(document.id),
        'document_title': document.title,
        'original_filename': document.original_filename,
        'source_download_url': f'/api/v1/documents/{document.id}/source',
        'page': question.source_page_start,
        'source_page_url': (
            f'/api/v1/documents/{document.id}/pages/{question.source_page_start}'
            if question.source_page_start else None
        ),
        'text': question.extracted_text,
        'question_type': question.question_type,
        'content': json.loads(question.content_json) if question.content_json else None,
        'quality_signals': json.loads(question.quality_signals_json) if question.quality_signals_json else None,
        'extraction_version': question.extraction_version,
    } for question, document in rows]


@router.get('/security-quarantine')
def security_quarantine(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    documents = db.query(Document).filter(
        Document.security_status.in_(['infected', 'unavailable']),
    ).order_by(Document.created_at.asc()).limit(100).all()
    return [{
        'id': str(document.id),
        'title': document.title,
        'original_filename': document.original_filename,
        'security_status': document.security_status,
        'scan_detail': document.security_scan_detail,
        'uploaded_at': document.created_at.isoformat() if document.created_at else None,
        'source_url': f'/api/v1/documents/{document.id}/source',
    } for document in documents]


@router.post('/documents/{document_id}/security-rescan')
def rescan_quarantined_document(
    document_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        parsed_id = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    document = db.query(Document).filter(Document.id == parsed_id).first()
    if not document:
        raise HTTPException(404, 'NOT_FOUND')
    expected_prefix = f'quarantine/{document.id}/'
    if document.security_status not in {'infected', 'unavailable'} or not document.storage_object_key.startswith(expected_prefix):
        raise HTTPException(409, 'DOCUMENT_NOT_IN_SECURITY_QUARANTINE')

    result = scan_bytes(read_bytes(document.storage_object_key))
    document.security_scan_detail = result.detail
    document.security_scanned_at = datetime.now(timezone.utc) if result.status != ScanStatus.unavailable else None
    if result.status == ScanStatus.unavailable:
        document.security_status = 'unavailable'
        db.commit()
        raise HTTPException(503, 'MALWARE_SCANNER_UNAVAILABLE')
    if result.status == ScanStatus.infected:
        document.security_status = 'infected'
        job = db.query(ProcessingJob).filter(
            ProcessingJob.document_id == document.id,
        ).order_by(ProcessingJob.created_at.desc()).first()
        if job:
            job.status = JobStatus.held
            job.error_category = result.detail
        db.commit()
        return {'document_id': document_id, 'security_status': 'infected', 'status': 'quarantined'}

    extension = document.storage_object_key.rsplit('.', 1)[-1]
    target_key = f'uploads/{document.id}/original.{extension}'
    move(document.storage_object_key, target_key)
    document.storage_object_key = target_key
    document.security_status = 'clean'
    document.processing_status = ProcessingStatus.pending
    document.security_scan_detail = 'clean'
    job = db.query(ProcessingJob).filter(
        ProcessingJob.document_id == document.id,
    ).order_by(ProcessingJob.created_at.desc()).first()
    if not job:
        job = ProcessingJob(
            document_id=document.id,
            job_type='extract',
            status=JobStatus.queued,
            attempt_count=0,
            available_at=datetime.now(timezone.utc),
        )
        db.add(job)
    else:
        job.status = JobStatus.queued
        job.job_type = 'extract'
        job.error_category = None
        job.attempt_count = 0
        job.available_at = datetime.now(timezone.utc)
        job.started_at = None
        job.finished_at = None
        job.worker_id = None
        job.lease_expires_at = None
    db.commit()
    return {'document_id': document_id, 'security_status': 'clean', 'status': 'queued'}


@router.post('/documents/{document_id}/security-reject')
def reject_quarantined_document(
    document_id: str,
    body: SecurityRejection,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        parsed_id = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    document = db.query(Document).filter(Document.id == parsed_id).first()
    if not document:
        raise HTTPException(404, 'NOT_FOUND')
    expected_prefix = f'quarantine/{document.id}/'
    if document.security_status not in {'infected', 'unavailable'} or not document.storage_object_key.startswith(expected_prefix):
        raise HTTPException(409, 'DOCUMENT_NOT_IN_SECURITY_QUARANTINE')
    if len(body.note.strip()) < 4:
        raise HTTPException(422, 'SECURITY_REJECTION_RATIONALE_REQUIRED')
    document.security_status = 'rejected'
    document.security_reviewed_by = admin.id
    document.security_reviewed_at = datetime.now(timezone.utc)
    document.security_review_note = body.note.strip()
    job = db.query(ProcessingJob).filter(
        ProcessingJob.document_id == document.id,
    ).order_by(ProcessingJob.created_at.desc()).first()
    if job:
        job.status = JobStatus.held
        job.error_category = 'admin_rejected'
    db.commit()
    return {'document_id': document_id, 'security_status': 'rejected'}


@router.get('/jobs')
def list_processing_jobs(
    status: JobStatus | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = db.query(ProcessingJob, Document).join(
        Document,
        ProcessingJob.document_id == Document.id,
    )
    if status is not None:
        query = query.filter(ProcessingJob.status == status)
    rows = query.order_by(ProcessingJob.created_at.desc()).limit(limit).all()
    return [{
        'id': str(job.id),
        'document_id': str(document.id),
        'document_title': document.title,
        'original_filename': document.original_filename,
        'job_type': job.job_type,
        'status': job.status.value,
        'attempt_count': job.attempt_count or 0,
        'available_at': job.available_at.isoformat() if job.available_at else None,
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'finished_at': job.finished_at.isoformat() if job.finished_at else None,
        'lease_expires_at': job.lease_expires_at.isoformat() if job.lease_expires_at else None,
        'error_category': job.error_category,
        'processing_status': document.processing_status.value,
    } for job, document in rows]


@router.get('/jobs/{job_id}')
def get_processing_job(
    job_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        parsed_id = uuid.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    row = db.query(ProcessingJob, Document).join(
        Document,
        ProcessingJob.document_id == Document.id,
    ).filter(ProcessingJob.id == parsed_id).first()
    if not row:
        raise HTTPException(404, 'NOT_FOUND')
    job, document = row
    return {
        'id': str(job.id),
        'document_id': str(document.id),
        'document_title': document.title,
        'original_filename': document.original_filename,
        'job_type': job.job_type,
        'status': job.status.value,
        'attempt_count': job.attempt_count or 0,
        'available_at': job.available_at.isoformat() if job.available_at else None,
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'finished_at': job.finished_at.isoformat() if job.finished_at else None,
        'lease_expires_at': job.lease_expires_at.isoformat() if job.lease_expires_at else None,
        'worker_id': job.worker_id,
        'error_category': job.error_category,
        'processing_status': document.processing_status.value,
    }


@router.post('/jobs/{job_id}/retry')
def retry_processing_job(
    job_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        parsed_id = uuid.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    job = db.query(ProcessingJob).filter(ProcessingJob.id == parsed_id).with_for_update().first()
    if not job:
        raise HTTPException(404, 'NOT_FOUND')
    if job.status != JobStatus.failed:
        raise HTTPException(409, 'JOB_NOT_RETRYABLE')
    document = db.query(Document).filter(Document.id == job.document_id).first()
    if not document:
        raise HTTPException(404, 'NOT_FOUND')
    if document.security_status != 'clean':
        raise HTTPException(409, 'SECURITY_SCAN_REQUIRED')
    now = datetime.now(timezone.utc)
    job.status = JobStatus.queued
    job.attempt_count = 0
    job.available_at = now
    job.started_at = None
    job.finished_at = None
    job.lease_expires_at = None
    job.worker_id = None
    job.error_category = None
    document.processing_status = 'pending'
    db.commit()
    return {'job_id': job_id, 'status': 'queued'}
