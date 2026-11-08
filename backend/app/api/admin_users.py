import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.models.user import User
from app.services.auth import require_admin

router = APIRouter(prefix='/api/v1/admin/users', tags=['admin-users'])

class RoleUpdate(BaseModel):
    role: str

@router.get('')
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return [{'id':str(u.id),'email':u.email,'display_name':u.display_name,'role':u.role,'status':u.status} for u in db.query(User).all()]

@router.patch('/{user_id}/role')
def change_role(user_id: str, body: RoleUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    try:
        target_uuid = uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    if body.role not in ('user','admin'): raise HTTPException(400,'VALIDATION_ERROR')
    target = db.query(User).filter(User.id == target_uuid).first()
    if not target: raise HTTPException(404,'NOT_FOUND')
    if target.role == 'admin' and body.role != 'admin':
        admins = db.query(User).filter(User.role=='admin').count()
        if admins <= 1: raise HTTPException(400,'LAST_ADMIN')
    target.role = body.role; db.commit()
    return {'id':str(target.id),'role':target.role}
