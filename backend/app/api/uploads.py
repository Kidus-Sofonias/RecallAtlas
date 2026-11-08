import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.schemas.upload import UploadInitiateRequest, UploadInitiateResponse
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.document import Document, ProcessingStatus
from app.models.taxonomy import Subject
from app.models.job import ProcessingJob, JobStatus
from app.storage.files import move, save_bytes, checksum
from app.services.malware_scan import ScanStatus, scan_bytes
from app.services.auth import require_onboarding

router = APIRouter(prefix='/api/v1/uploads', tags=['uploads'])
ALLOWED_MIME = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'image/png',
    'image/jpeg',
    'image/webp',
    'image/tiff',
    'image/bmp',
}
def max_upload_size() -> int:
    return settings.max_upload_size_mb * 1024 * 1024

@router.get('/limits')
def upload_limits():
    from app.schemas.upload import SUPPORTED_UPLOADS

    return {
        'max_size_mb': settings.max_upload_size_mb,
        'max_size_bytes': max_upload_size(),
        'extensions': sorted(SUPPORTED_UPLOADS),
    }

@router.post('/initiate', response_model=UploadInitiateResponse)
def initiate(req: UploadInitiateRequest, db: Session = Depends(get_db), user: User = Depends(require_onboarding)):
    if req.mime_type not in ALLOWED_MIME: raise HTTPException(415, 'UNSUPPORTED_FORMAT')
    if req.file_size > max_upload_size(): raise HTTPException(413, 'FILE_TOO_LARGE')
    try:
        req.validate_supported_file()
    except ValueError as exc:
        raise HTTPException(415, 'UNSUPPORTED_FORMAT') from exc
    if not req.no_answers_confirmed:
        raise HTTPException(422, 'NO_ANSWERS_POLICY_CONFIRMATION_REQUIRED')
    if req.subject_id and not db.query(Subject.id).filter(Subject.id == req.subject_id).first():
        raise HTTPException(422, 'INVALID_SUBJECT')
    doc_id = uuid.uuid4()
    extension = req.filename.rsplit('.', 1)[-1].lower()
    key = f'uploads/{doc_id}/original.{extension}'
    doc = Document(
        id=doc_id,
        uploader_id=user.id,
        title=req.title,
        original_filename=req.filename.replace('\r', '').replace('\n', '')[:255],
        grade=req.grade,
        academic_year=req.academic_year,
        subject_id=req.subject_id,
        mime_type=req.mime_type,
        file_size=req.file_size,
        storage_object_key=key,
        checksum='pending',
        no_answers_confirmed=True,
        security_status='pending',
        processing_status=ProcessingStatus.pending,
    )
    db.add(doc); db.commit()
    return UploadInitiateResponse(document_id=str(doc_id), storage_object_key=key, upload_url=f'/api/v1/uploads/{doc_id}/complete')

@router.post('/{document_id}/complete')
def complete(
    document_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_onboarding),
):
    try:
        parsed_id = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    doc = db.query(Document).filter(Document.id == parsed_id).first()
    if not doc: raise HTTPException(404, 'NOT_FOUND')
    if doc.uploader_id != user.id and user.role != 'admin':
        raise HTTPException(404, 'NOT_FOUND')
    if doc.checksum != 'pending':
        raise HTTPException(409, 'UPLOAD_ALREADY_COMPLETED')
    limit = max_upload_size()
    data = file.file.read(limit + 1)
    if len(data) > limit: raise HTTPException(413, 'FILE_TOO_LARGE')
    from app.services.extraction import detect_upload_mime
    try:
        actual_mime = detect_upload_mime(data)
    except ValueError as exc:
        raise HTTPException(415, 'INVALID_FILE') from exc
    if actual_mime != doc.mime_type:
        raise HTTPException(415, 'FILE_TYPE_MISMATCH')
    cs = checksum(data)
    extension = doc.storage_object_key.rsplit('.', 1)[-1]
    quarantine_key = f'quarantine/{doc.id}/original.{extension}'
    save_bytes(quarantine_key, data)
    result = scan_bytes(data)
    doc.checksum = cs
    doc.file_size = len(data)
    doc.security_scan_detail = result.detail
    doc.security_scanned_at = datetime.now(timezone.utc) if result.status != ScanStatus.unavailable else None
    if result.status == ScanStatus.clean:
        move(quarantine_key, doc.storage_object_key)
        doc.security_status = 'clean'
        doc.processing_status = ProcessingStatus.pending
    else:
        doc.storage_object_key = quarantine_key
        doc.security_status = result.status.value
        doc.processing_status = ProcessingStatus.held
    job = ProcessingJob(
        document_id=doc.id,
        status=JobStatus.queued if result.status == ScanStatus.clean else JobStatus.held,
        job_type='extract' if result.status == ScanStatus.clean else 'security_scan',
        error_category=None if result.status == ScanStatus.clean else result.detail,
        available_at=datetime.now(timezone.utc) if result.status == ScanStatus.clean else None,
    )
    db.add(job); db.commit()
    if result.status == ScanStatus.clean:
        return {
            'document_id': document_id,
            'status': 'queued',
            'security_status': 'clean',
            'job_id': str(job.id),
        }

    return {
        'document_id': document_id,
        'status': 'quarantined',
        'security_status': result.status.value,
        'job_id': str(job.id),
    }
