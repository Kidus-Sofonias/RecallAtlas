import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.resource import Resource
from app.models.taxonomy import Subject
from app.models.user import User
from app.services.auth import require_admin

router = APIRouter(prefix='/api/v1/resources', tags=['resources'])


class ArticleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=50000)
    subject_id: uuid.UUID | None = None


@router.get('')
def list_articles(
    subject_id: uuid.UUID | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = db.query(Resource).filter(Resource.status == 'published')
    if subject_id:
        query = query.filter(Resource.subject_id == subject_id)
    return [
        {
            'id': str(resource.id),
            'title': resource.title,
            'summary': resource.summary,
            'subject_id': str(resource.subject_id) if resource.subject_id else None,
            'created_at': resource.created_at.isoformat() if resource.created_at else None,
        }
        for resource in query.order_by(Resource.created_at.desc()).limit(limit).all()
    ]


@router.get('/{resource_id}')
def get_article(resource_id: str, db: Session = Depends(get_db)):
    try:
        parsed_id = uuid.UUID(resource_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    resource = db.query(Resource).filter(
        Resource.id == parsed_id,
        Resource.status == 'published',
    ).first()
    if not resource:
        raise HTTPException(404, 'NOT_FOUND')
    return {
        'id': str(resource.id),
        'title': resource.title,
        'summary': resource.summary,
        'body': resource.body,
        'subject_id': str(resource.subject_id) if resource.subject_id else None,
        'created_at': resource.created_at.isoformat() if resource.created_at else None,
    }


@router.post('', status_code=201)
def create_article(
    body: ArticleCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if body.subject_id and not db.query(Subject.id).filter(Subject.id == body.subject_id).first():
        raise HTTPException(422, 'INVALID_SUBJECT')
    resource = Resource(
        created_by=admin.id,
        subject_id=body.subject_id,
        title=body.title.strip(),
        summary=body.summary.strip(),
        body=body.body.strip(),
        resource_type='article',
        status='published',
    )
    if not resource.title or not resource.summary or not resource.body:
        raise HTTPException(422, 'Article fields cannot be blank.')
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return {
        'id': str(resource.id),
        'title': resource.title,
        'summary': resource.summary,
        'subject_id': str(resource.subject_id) if resource.subject_id else None,
        'created_at': resource.created_at.isoformat() if resource.created_at else None,
    }
