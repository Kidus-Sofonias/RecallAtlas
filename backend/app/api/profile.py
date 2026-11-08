import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.auth_token import AuthToken
from app.models.audit_event import AuditEvent
from app.models.bookmark import Bookmark
from app.models.collection import Collection, CollectionItem
from app.models.notification import Notification
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix='/api/v1/me', tags=['profile'])
admin_router = APIRouter(prefix='/api/v1/admin', tags=['admin'])


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    school: str | None = Field(default=None, max_length=200)


class DeletionRequest(BaseModel):
    confirm: bool = False


def _profile(user: User) -> dict:
    return {
        'id': str(user.id),
        'email': user.email,
        'display_name': user.display_name,
        'role': user.role,
        'school': user.school,
        'school_verified': False,
        'preferred_grade': user.preferred_grade,
        'preferred_subject_ids': [str(subject.id) for subject in user.preferred_subjects],
        'onboarding_completed': bool(user.onboarding_completed),
        'deletion_requested_at': user.deletion_requested_at.isoformat() if user.deletion_requested_at else None,
        'deletion_request_status': user.deletion_request_status,
    }


@router.get('')
def get_profile(user: User = Depends(get_current_user)):
    return _profile(user)


@router.patch('')
def update_profile(
    body: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.status != 'active':
        raise HTTPException(403, 'ACCOUNT_NOT_ACTIVE')
    if body.display_name is not None:
        user.display_name = body.display_name.strip() or None
    if body.school is not None:
        school = body.school.strip()
        if not school:
            raise HTTPException(422, 'SCHOOL_CANNOT_BE_BLANK')
        user.school = school
    db.commit()
    db.refresh(user)
    return _profile(user)


@router.post('/deletion-request', status_code=202)
def request_account_deletion(
    body: DeletionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not body.confirm:
        raise HTTPException(422, 'DELETION_CONFIRMATION_REQUIRED')
    if user.role == 'admin':
        raise HTTPException(409, 'ADMIN_DELETION_REQUIRES_SEPARATE_REVIEW')
    if user.deletion_request_status == 'pending':
        return {
            'status': 'requested',
            'requested_at': user.deletion_requested_at.isoformat(),
        }

    requested_at = datetime.now(timezone.utc)
    user.deletion_requested_at = requested_at
    user.deletion_request_status = 'pending'
    user.deletion_reviewed_at = None
    user.deletion_reviewed_by = None
    user.deletion_review_note = None
    user.status = 'deletion_requested'
    db.query(AuthSession).filter(
        AuthSession.user_id == user.id,
        AuthSession.revoked_at.is_(None),
    ).update(
        {'revoked_at': requested_at},
        synchronize_session=False,
    )
    db.query(AuthToken).filter(
        AuthToken.user_id == user.id,
        AuthToken.consumed_at.is_(None),
    ).update(
        {'consumed_at': requested_at},
        synchronize_session=False,
    )
    db.add(AuditEvent(
        actor_id=user.id,
        action='account.deletion_requested',
        target_type='user',
        target_id=str(user.id),
    ))
    db.commit()
    return {'status': 'requested', 'requested_at': requested_at.isoformat()}


@admin_router.get('/deletion-requests')
def list_deletion_requests(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    if admin.role != 'admin':
        raise HTTPException(403, 'FORBIDDEN')
    users = db.query(User).filter(
        User.deletion_request_status == 'pending',
    ).order_by(User.deletion_requested_at.asc()).limit(100).all()
    return [{
        'user_id': str(user.id),
        'email': user.email,
        'display_name': user.display_name,
        'requested_at': user.deletion_requested_at.isoformat() if user.deletion_requested_at else None,
    } for user in users]


class DeletionDecision(BaseModel):
    decision: str = Field(pattern='^(approve|reject)$')
    note: str = Field(min_length=4, max_length=1000)


@admin_router.post('/deletion-requests/{user_id}/decision')
def decide_deletion_request(
    user_id: str,
    body: DeletionDecision,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
):
    if admin.role != 'admin':
        raise HTTPException(403, 'FORBIDDEN')
    try:
        target_id = uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    target = db.query(User).filter(User.id == target_id).with_for_update().first()
    if not target:
        raise HTTPException(404, 'NOT_FOUND')
    if target.deletion_request_status != 'pending' or target.status != 'deletion_requested':
        raise HTTPException(409, 'DELETION_REQUEST_NOT_PENDING')
    if target.role == 'admin':
        raise HTTPException(409, 'ADMIN_DELETION_REQUIRES_SEPARATE_REVIEW')

    reviewed_at = datetime.now(timezone.utc)
    rationale = body.note.strip()
    if len(rationale) < 4:
        raise HTTPException(422, 'DELETION_REVIEW_NOTE_REQUIRED')
    target.deletion_reviewed_at = reviewed_at
    target.deletion_reviewed_by = admin.id
    target.deletion_review_note = rationale
    if body.decision == 'reject':
        target.deletion_request_status = 'rejected'
        target.status = 'active'
        db.add(AuditEvent(
            actor_id=admin.id,
            action='account.deletion_rejected',
            target_type='user',
            target_id=str(target.id),
            rationale=rationale,
        ))
        db.commit()
        return {'user_id': user_id, 'deletion_request_status': 'rejected'}

    db.query(CollectionItem).filter(
        CollectionItem.collection_id.in_(
            db.query(Collection.id).filter(Collection.owner_id == target.id),
        ),
    ).delete(synchronize_session=False)
    db.query(Collection).filter(Collection.owner_id == target.id).delete(synchronize_session=False)
    db.query(Bookmark).filter(Bookmark.user_id == target.id).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.recipient_id == target.id).delete(synchronize_session=False)
    db.query(AuthToken).filter(AuthToken.user_id == target.id).delete(synchronize_session=False)
    db.query(AuthSession).filter(AuthSession.user_id == target.id).delete(synchronize_session=False)
    target.preferred_subjects.clear()
    target.email = None
    target.password_hash = None
    target.auth_subject = f'deleted:{target.id}:{uuid.uuid4()}'
    target.display_name = 'Deleted contributor'
    target.school = None
    target.preferred_grade = None
    target.onboarding_completed = False
    target.status = 'deleted'
    target.deletion_request_status = 'completed'
    db.add(AuditEvent(
        actor_id=admin.id,
        action='account.deletion_completed',
        target_type='user',
        target_id=str(target.id),
        rationale=rationale,
    ))
    db.commit()
    return {'user_id': user_id, 'deletion_request_status': 'completed'}
