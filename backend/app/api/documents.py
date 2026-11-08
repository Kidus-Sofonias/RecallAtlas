import json
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.document import Document, ProcessingStatus
from app.models.question import Question, QualityStatus
from app.models.user import User
from app.services.auth import require_admin, require_onboarding
from app.storage.files import read_bytes
from app.models.job import JobStatus, ProcessingJob

router = APIRouter(prefix='/api/v1/documents', tags=['documents'])

def _readable_document(document_id: str, db: Session, user: User) -> Document:
    try:
        parsed_id = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    doc = db.query(Document).filter(Document.id == parsed_id).first()
    if not doc:
        raise HTTPException(404, 'NOT_FOUND')
    if doc.security_status != 'clean' and user.role != 'admin':
        raise HTTPException(404, 'NOT_FOUND')
    if doc.uploader_id != user.id and user.role != 'admin':
        has_published_question = db.query(Question.id).filter(
            Question.document_id == doc.id,
            Question.quality_status == QualityStatus.reliable,
            Question.review_status == 'approved',
        ).first()
        if doc.processing_status != ProcessingStatus.completed or not has_published_question:
            raise HTTPException(404, 'NOT_FOUND')
    return doc

@router.get('/{document_id}/source')
def get_source(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_onboarding),
):
    doc = _readable_document(document_id, db, user)
    data = read_bytes(doc.storage_object_key)
    filename = doc.original_filename or 'source-document'
    safe_filename = quote(filename, safe='')
    return Response(
        content=data,
        media_type=doc.mime_type,
        headers={
            'Content-Disposition': f"attachment; filename*=UTF-8''{safe_filename}",
            'Cache-Control': 'private, no-store',
            'X-Content-Type-Options': 'nosniff',
        },
    )

@router.get('/{document_id}/preview')
def get_source_preview(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_onboarding),
):
    doc = _readable_document(document_id, db, user)
    if doc.mime_type != 'application/pdf':
        raise HTTPException(415, 'PDF_PREVIEW_UNAVAILABLE')
    data = read_bytes(doc.storage_object_key)
    filename = quote(doc.original_filename or 'source-document.pdf', safe='')
    return Response(
        content=data,
        media_type='application/pdf',
        headers={
            'Content-Disposition': f"inline; filename*=UTF-8''{filename}",
            'Cache-Control': 'private, no-store',
            'X-Content-Type-Options': 'nosniff',
        },
    )

@router.get('/{document_id}/pages/{page_number}')
def get_source_page(
    document_id: str,
    page_number: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_onboarding),
):
    doc = _readable_document(document_id, db, user)
    if page_number < 1:
        raise HTTPException(404, 'NOT_FOUND')
    data = read_bytes(doc.storage_object_key)
    if doc.mime_type == 'application/pdf':
        try:
            import fitz
        except ImportError as exc:
            raise HTTPException(503, 'SOURCE_PREVIEW_UNAVAILABLE') from exc
        with fitz.open(stream=data, filetype='pdf') as pdf:
            if page_number > len(pdf):
                raise HTTPException(404, 'NOT_FOUND')
            pixmap = pdf[page_number - 1].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            content = pixmap.tobytes('png')
    elif doc.mime_type.startswith('image/'):
        from PIL import Image, UnidentifiedImageError
        import io

        try:
            with Image.open(io.BytesIO(data)) as image:
                if page_number > getattr(image, 'n_frames', 1):
                    raise HTTPException(404, 'NOT_FOUND')
                image.seek(page_number - 1)
                output = io.BytesIO()
                image.convert('RGB').save(output, format='PNG')
                content = output.getvalue()
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(415, 'SOURCE_PREVIEW_UNAVAILABLE') from exc
    else:
        raise HTTPException(415, 'SOURCE_PREVIEW_UNAVAILABLE')
    return Response(
        content=content,
        media_type='image/png',
        headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'},
    )

@router.get('/{document_id}')
def get_doc(document_id: str, db: Session = Depends(get_db)):
    try:
        parsed_id = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    doc = db.query(Document).filter(Document.id == parsed_id).first()
    if not doc: raise HTTPException(404,'NOT_FOUND')
    return {
        'id': str(doc.id),
        'status': doc.processing_status.value,
        'security_status': doc.security_status,
        'mime_type': doc.mime_type,
        'page_count': doc.page_count,
        'title': doc.title,
        'grade': doc.grade,
        'academic_year': doc.academic_year,
        'created_at': doc.created_at.isoformat() if doc.created_at else None,
    }

@router.get('/{document_id}/questions')
def get_questions(document_id: str, db: Session = Depends(get_db)):
    try:
        parsed_id = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    qs = db.query(Question).filter(
        Question.document_id == parsed_id,
        Question.quality_status == QualityStatus.reliable,
    ).all()
    return [{
        'id': str(q.id),
        'page': q.source_page_start,
        'text': q.extracted_text,
        'quality': q.quality_status.value,
        'question_type': q.question_type,
        'content': json.loads(q.content_json) if q.content_json else None,
        'quality_signals': json.loads(q.quality_signals_json) if q.quality_signals_json else None,
        'extraction_version': q.extraction_version,
    } for q in qs]

@router.post('/{document_id}/process')
def trigger(document_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    try:
        parsed_id = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    doc = db.query(Document).filter(Document.id == parsed_id).first()
    if not doc: raise HTTPException(404,'NOT_FOUND')
    if doc.security_status != 'clean':
        raise HTTPException(409, 'SECURITY_SCAN_REQUIRED')
    job = db.query(ProcessingJob).filter(
        ProcessingJob.document_id == doc.id,
    ).order_by(ProcessingJob.created_at.desc()).first()
    if job and job.status in {JobStatus.queued, JobStatus.running}:
        raise HTTPException(409, 'JOB_ALREADY_ACTIVE')
    now = datetime.now(timezone.utc)
    if not job:
        job = ProcessingJob(
            document_id=doc.id,
            job_type='extract',
            status=JobStatus.queued,
            attempt_count=0,
            available_at=now,
        )
        db.add(job)
    else:
        job.status = JobStatus.queued
        job.job_type = 'extract'
        job.attempt_count = 0
        job.error_category = None
        job.available_at = now
        job.started_at = None
        job.finished_at = None
        job.lease_expires_at = None
        job.worker_id = None
    doc.processing_status = ProcessingStatus.pending
    db.commit()
    return {'document_id':document_id,'job_id':str(job.id),'status':'queued'}
