import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.db.session import get_db
from app.models.user import User
from app.models.collection import Collection, CollectionItem
from app.models.notification import Notification
from app.models.document import Document
from app.models.question import Question, QualityStatus
from app.services.auth import require_onboarding, require_admin
from fastapi import HTTPException

router = APIRouter(tags=['phase4-5'])

class CollectionIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)

@router.post('/api/v1/collections')
def create_collection(body: CollectionIn, db: Session = Depends(get_db), user: User = Depends(require_onboarding)):
    name = body.name.strip()
    if not name:
        raise HTTPException(422, 'COLLECTION_NAME_REQUIRED')
    c = Collection(owner_id=user.id, name=name); db.add(c); db.commit(); db.refresh(c)
    return {'id':str(c.id)}

@router.get('/api/v1/collections')
def list_collections(db: Session = Depends(get_db), user: User = Depends(require_onboarding)):
    collections = db.query(Collection).filter(Collection.owner_id == user.id).order_by(Collection.created_at.desc()).all()
    return [{
        'id': str(collection.id),
        'name': collection.name,
        'item_count': db.query(CollectionItem.id).filter(CollectionItem.collection_id == collection.id).count(),
    } for collection in collections]

def _owned_collection(collection_id: str, db: Session, user: User) -> Collection:
    try:
        parsed_id = uuid.UUID(collection_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    collection = db.query(Collection).filter(
        Collection.id == parsed_id,
        Collection.owner_id == user.id,
    ).first()
    if not collection:
        raise HTTPException(404, 'NOT_FOUND')
    return collection

@router.post('/api/v1/collections/{collection_id}/items')
def add_item(collection_id: str, question_id: str, db: Session = Depends(get_db), user: User = Depends(require_onboarding)):
    try:
        parsed_question_id = uuid.UUID(question_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    collection = _owned_collection(collection_id, db, user)
    question = db.query(Question).filter(
        Question.id == parsed_question_id,
        Question.quality_status == QualityStatus.reliable,
    ).first()
    if not question:
        raise HTTPException(404, 'NOT_FOUND')
    existing = db.query(CollectionItem).filter(
        CollectionItem.collection_id == collection.id,
        CollectionItem.question_id == parsed_question_id,
    ).first()
    if existing:
        return {'id': str(existing.id)}
    item = CollectionItem(collection_id=collection.id, question_id=parsed_question_id)
    db.add(item); db.commit()
    db.refresh(item)
    return {'id':str(item.id)}

@router.get('/api/v1/collections/{collection_id}/items')
def list_collection_items(
    collection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_onboarding),
):
    collection = _owned_collection(collection_id, db, user)
    rows = db.query(CollectionItem, Question).join(
        Question,
        Question.id == CollectionItem.question_id,
    ).filter(
        CollectionItem.collection_id == collection.id,
        Question.quality_status == QualityStatus.reliable,
    ).order_by(CollectionItem.position.asc(), CollectionItem.created_at.asc()).all()
    return [{
        'id': str(item.id),
        'question_id': str(question.id),
        'page': question.source_page_start,
        'text': question.extracted_text,
        'question_type': question.question_type,
    } for item, question in rows]

@router.delete('/api/v1/collections/{collection_id}/items/{item_id}')
def remove_collection_item(
    collection_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_onboarding),
):
    collection = _owned_collection(collection_id, db, user)
    try:
        parsed_item_id = uuid.UUID(item_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    item = db.query(CollectionItem).filter(
        CollectionItem.id == parsed_item_id,
        CollectionItem.collection_id == collection.id,
    ).first()
    if not item:
        raise HTTPException(404, 'NOT_FOUND')
    db.delete(item)
    db.commit()
    return {'status': 'deleted'}

@router.get('/api/v1/notifications')
def list_notifications(db: Session = Depends(get_db), user: User = Depends(require_onboarding)):
    return [{
        'id': str(n.id),
        'title': n.title,
        'body': n.body,
        'read': n.read,
        'created_at': n.created_at.isoformat() if n.created_at else None,
    } for n in db.query(Notification).filter(
        Notification.recipient_id == user.id,
    ).order_by(Notification.created_at.desc()).limit(100).all()]

@router.post('/api/v1/notifications/{notification_id}/read')
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_onboarding),
):
    try:
        parsed_id = uuid.UUID(notification_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    notification = db.query(Notification).filter(
        Notification.id == parsed_id,
        Notification.recipient_id == user.id,
    ).first()
    if not notification:
        raise HTTPException(404, 'NOT_FOUND')
    notification.read = True
    db.commit()
    return {'id': str(notification.id), 'read': True}

@router.post('/api/v1/documents/{document_id}/duplicate-check')
def duplicate_check(document_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    try:
        parsed_id = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    doc = db.query(Document).filter(Document.id == parsed_id).first()
    if not doc: 
        return {'error':'NOT_FOUND'}
    dupes = db.query(Document).filter(Document.checksum == doc.checksum, Document.id != doc.id).all()
    return {'document_id':document_id,'duplicates':[str(d.id) for d in dupes]}

@router.get('/api/v1/questions/{question_id}/metadata-suggestion')
def metadata_suggestion(question_id: str):
    return {'year':None,'curriculum':None,'topic':None,'note':'unknown - requires AI provider decision'}
