import uuid, json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.question import Question, QualityStatus
from app.models.user import User
from app.services.auth import require_admin
from app.services.embeddings import embed, to_json, from_json, cosine

router = APIRouter(tags=['semantic'])

@router.post('/api/v1/questions/{question_id}/embed')
def generate_embedding(question_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    try:
        parsed_id = uuid.UUID(question_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    q = db.query(Question).filter(Question.id == parsed_id).first()
    if not q: return {'error':'NOT_FOUND'}
    v = embed(q.extracted_text)
    q.embedding = to_json(v)
    db.commit()
    return {'id':question_id,'has_embedding': v is not None}

@router.get('/api/v1/search/hybrid')
def hybrid_search(q: str, db: Session = Depends(get_db)):
    qv = embed(q)
    results = []
    for r in db.query(Question).filter(Question.quality_status == QualityStatus.reliable).all():
        kw = 1.0 if q.lower() in (r.extracted_text or '').lower() else 0.0
        sem = cosine(qv, from_json(r.embedding)) if qv else 0.0
        score = 0.5*kw + 0.5*sem
        results.append({'id':str(r.id),'document_id':str(r.document_id),'page':r.source_page_start,'text':r.extracted_text[:200],'score':score,'has_embedding': r.embedding is not None})
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

from pydantic import BaseModel
from typing import List

class VectorQuery(BaseModel):
    vector: List[float]

@router.post('/api/v1/search/hybrid-vector')
def hybrid_vector_search(body: VectorQuery, db: Session = Depends(get_db)):
    if len(body.vector) != 384:
        raise HTTPException(400, 'INVALID_DIMENSION')
    if any(not isinstance(x, (int, float)) for x in body.vector):
        raise HTTPException(400, 'INVALID_VECTOR')
    qv = body.vector
    results = []
    for r in db.query(Question).filter(Question.quality_status == QualityStatus.reliable).all():
        sem = cosine(qv, from_json(r.embedding)) if r.embedding else 0.0
        kw = 0.0
        results.append({'id':str(r.id),'document_id':str(r.document_id),'page':r.source_page_start,'text':r.extracted_text[:200],'score':sem,'has_embedding': r.embedding is not None})
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

@router.get('/api/v1/admin/embedding-backlog')
def embedding_backlog(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    from sqlalchemy import func
    counts = db.query(Question.embedding_status, func.count(Question.id)).group_by(Question.embedding_status).all()
    return {str(k): v for k,v in counts}
