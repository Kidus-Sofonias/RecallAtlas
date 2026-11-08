import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.bookmark import Bookmark
from app.models.user import User
from app.services.auth import require_onboarding

router = APIRouter(prefix='/api/v1/bookmarks', tags=['bookmarks'])

@router.get('')
def list_bm(db: Session = Depends(get_db), user: User = Depends(require_onboarding)):
    return [{'id':str(b.id),'target_type':b.target_type,'target_id':str(b.target_id)} for b in db.query(Bookmark).filter(Bookmark.user_id==user.id).all()]

@router.post('')
def add_bm(target_type: str, target_id: str, db: Session = Depends(get_db), user: User = Depends(require_onboarding)):
    if target_type not in {'question', 'document'}:
        raise HTTPException(400, 'VALIDATION_ERROR')
    try:
        parsed_target_id = uuid.UUID(target_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    b = Bookmark(user_id=user.id, target_type=target_type, target_id=parsed_target_id); db.add(b); db.commit(); db.refresh(b)
    return {'id':str(b.id)}

@router.delete('/{bookmark_id}')
def del_bm(bookmark_id: str, db: Session = Depends(get_db), user: User = Depends(require_onboarding)):
    try:
        parsed_id = uuid.UUID(bookmark_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    b = db.query(Bookmark).filter(Bookmark.id==parsed_id, Bookmark.user_id==user.id).first()
    if not b: raise HTTPException(404,'NOT_FOUND')
    db.delete(b); db.commit(); return {'status':'deleted'}
