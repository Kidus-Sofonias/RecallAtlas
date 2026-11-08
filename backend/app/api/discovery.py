from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document, ProcessingStatus
from app.models.question import Question, QualityStatus
from app.models.user import User

router = APIRouter(prefix='/api/v1/discovery', tags=['discovery'])


def _questions(db: Session, grade: int | None, limit: int) -> list[dict[str, object]]:
    query = (
        db.query(Question, Document, User)
        .join(Document, Document.id == Question.document_id)
        .outerjoin(User, User.id == Document.uploader_id)
        .filter(
            Question.quality_status == QualityStatus.reliable,
            Document.processing_status == ProcessingStatus.completed,
        )
    )
    if grade is not None:
        query = query.filter(Document.grade == grade)

    results = query.order_by(Document.created_at.desc(), Question.created_at.desc()).limit(limit).all()
    return [
        {
            'id': str(question.id),
            'document_id': str(document.id),
            'page': question.source_page_start,
            'snippet': question.extracted_text[:200],
            'title': document.title or 'Untitled test',
            'grade': document.grade,
            'academic_year': document.academic_year,
            'posted_by': (user.display_name or 'Student contributor') if user else 'Student contributor',
            'posted_at': document.created_at.isoformat() if document.created_at else None,
        }
        for question, document, user in results
    ]


@router.get('')
def get_discovery_feed(
    grade: int | None = Query(default=None, ge=9, le=12),
    limit: int = Query(default=8, ge=1, le=24),
    db: Session = Depends(get_db),
):
    recent = _questions(db, None, limit)
    for_you = _questions(db, grade, limit) if grade is not None else []
    if grade is not None:
        recommended_ids = {item['id'] for item in for_you}
        recent = [item for item in recent if item['id'] not in recommended_ids]
    return {
        'recent': recent,
        'for_you': for_you,
        'grade': grade,
    }
