import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.models.taxonomy import Subject, Topic
from app.models.user import User
from app.services.auth import require_admin

router = APIRouter(prefix='/api/v1/taxonomy', tags=['taxonomy'])

class SubjectIn(BaseModel):
    name: str

@router.get('/subjects')
def list_subjects(db: Session = Depends(get_db)):
    return [{'id':str(s.id),'name':s.name} for s in db.query(Subject).all()]

@router.post('/subjects')
def create_subject(body: SubjectIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    s = Subject(name=body.name); db.add(s); db.commit(); db.refresh(s)
    return {'id':str(s.id),'name':s.name}

@router.get('/topics')
def list_topics(subject_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Topic)
    if subject_id: q = q.filter(Topic.subject_id == uuid.UUID(subject_id))
    return [{'id':str(t.id),'name':t.name,'subject_id':str(t.subject_id) if t.subject_id else None} for t in q.all()]

@router.post('/topics')
def create_topic(name: str, subject_id: str | None = None, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    try:
        parsed_subject_id = uuid.UUID(subject_id) if subject_id else None
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    t = Topic(name=name, subject_id=parsed_subject_id); db.add(t); db.commit(); db.refresh(t)
    return {'id':str(t.id),'name':t.name}
