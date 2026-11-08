import json
import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.models.question import Question, QualityStatus
from app.models.user import User
from app.services.auth import require_admin

router = APIRouter(prefix='/api/v1/questions', tags=['questions'])

class PatchBody(BaseModel):
    extracted_text: str | None = None

@router.get('/{question_id}')
def get_q(question_id: str, db: Session = Depends(get_db)):
    q = db.query(Question).filter(
        Question.id == uuid.UUID(question_id),
        Question.quality_status == QualityStatus.reliable,
    ).first()
    if not q: raise HTTPException(404,'NOT_FOUND')
    return {
        'id': str(q.id),
        'document_id': str(q.document_id),
        'page': q.source_page_start,
        'text': q.extracted_text,
        'quality': q.quality_status.value,
        'question_type': q.question_type,
        'content': json.loads(q.content_json) if q.content_json else None,
        'quality_signals': json.loads(q.quality_signals_json) if q.quality_signals_json else None,
        'extraction_version': q.extraction_version,
    }

@router.patch('/{question_id}')
def patch_q(question_id: str, body: PatchBody, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    try:
        parsed_id = uuid.UUID(question_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    q = db.query(Question).filter(Question.id == parsed_id).first()
    if not q: raise HTTPException(404,'NOT_FOUND')
    if body.extracted_text is not None:
        q.extracted_text = body.extracted_text
    db.commit()
    return {'id':str(q.id),'quality':q.quality_status.value}

@router.post('/{question_id}/review')
def review(question_id: str, decision: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    try:
        parsed_id = uuid.UUID(question_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    q = db.query(Question).filter(Question.id == parsed_id).first()
    if not q: raise HTTPException(404,'NOT_FOUND')
    if decision == 'approve':
        q.quality_status = QualityStatus.reliable
        q.review_status = 'approved'
    elif decision == 'reject':
        q.quality_status = QualityStatus.held
        q.review_status = 'rejected'
    else: raise HTTPException(400,'VALIDATION_ERROR')
    db.commit()
    return {'id':str(q.id),'quality':q.quality_status.value,'review_status':q.review_status}
