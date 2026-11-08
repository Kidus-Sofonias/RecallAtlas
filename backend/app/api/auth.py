import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.auth_token import AuthToken
from app.models.user import User
from app.models.taxonomy import Subject
from app.services.auth import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    create_csrf_token,
    get_current_user,
    hash_password,
    hash_token,
    issue_session,
    normalize_email,
    require_onboarding,
    set_session_cookie,
    user_payload,
    _as_utc,
    validate_password,
    verify_password,
)
from app.services.email import send_email

router = APIRouter(prefix='/api/v1/auth', tags=['authentication'])


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class PasswordReset(BaseModel):
    token: str
    password: str = Field(max_length=128)


class TokenRequest(BaseModel):
    token: str


class EmailRequest(BaseModel):
    email: str = Field(max_length=254)


class OnboardingRequest(BaseModel):
    school: str = Field(max_length=200)
    display_name: str | None = Field(default=None, max_length=100)
    preferred_grade: int | None = Field(default=None, ge=9, le=12)
    preferred_subject_ids: list[str] | None = None
    terms_accepted: bool = False


class PreferencesRequest(BaseModel):
    preferred_grade: int | None = Field(default=None, ge=9, le=12)
    preferred_subject_ids: list[str] | None = None


def _new_auth_token(db: Session, user: User, purpose: str, lifetime: timedelta) -> str:
    raw_token = secrets.token_urlsafe(32)
    db.add(AuthToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        purpose=purpose,
        expires_at=datetime.now(timezone.utc) + lifetime,
    ))
    db.commit()
    return raw_token


def _send_action_email(user: User, token: str, purpose: str) -> None:
    if purpose == 'verify_email':
        path = '/verify-email'
        subject = 'Verify your Recall Atlas email'
        message = 'Verify your email address to activate your Recall Atlas account.'
    else:
        path = '/reset-password'
        subject = 'Reset your Recall Atlas password'
        message = 'Use this one-time link to reset your Recall Atlas password.'
    link = f'{settings.frontend_url.rstrip("/")}{path}#token={quote(token)}'
    try:
        send_email(user.email or '', subject, f'{message}\n\n{link}')
    except (httpx.HTTPError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail='EMAIL_DELIVERY_UNAVAILABLE') from exc


def _require_email_delivery() -> None:
    if settings.email_dev_mode or not settings.resend_api_key:
        raise HTTPException(status_code=503, detail='EMAIL_DELIVERY_UNAVAILABLE')


@router.get('/csrf')
def csrf_token(response: Response):
    token = create_csrf_token()
    response.set_cookie(
        CSRF_COOKIE,
        token,
        max_age=60 * 60 * 24 * 14,
        httponly=False,
        secure=settings.app_env.lower() not in {'development', 'test'},
        samesite='lax',
        path='/',
    )
    return {'csrf_token': token}


@router.post('/register', status_code=202)
def register(body: Credentials, response: Response, db: Session = Depends(get_db)):
    try:
        email = normalize_email(body.email)
        validate_password(body.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    development_mode = settings.app_env.lower() in {'development', 'test'}
    if not development_mode:
        _require_email_delivery()

    existing = db.query(User).filter(User.email.ilike(email)).first()
    if existing:
        if development_mode:
            raise HTTPException(status_code=409, detail='ACCOUNT_ALREADY_EXISTS')
        return {'status': 'verification_if_account_exists'}
    user = User(
        auth_subject=f'password:{email}',
        email=email,
        password_hash=hash_password(body.password),
        display_name=email.split('@', 1)[0][:100],
        status='active' if development_mode else 'pending_verification',
        role='user',
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if development_mode:
            raise HTTPException(status_code=409, detail='ACCOUNT_ALREADY_EXISTS')
        return {'status': 'verification_if_account_exists'}
    db.refresh(user)
    if development_mode:
        session_token = issue_session(db, user)
        set_session_cookie(response, session_token)
        return {'user': user_payload(user), 'development_account': True}

    token = _new_auth_token(db, user, 'verify_email', timedelta(hours=24))
    _send_action_email(user, token, 'verify_email')
    return {'status': 'verification_if_account_exists'}


@router.post('/register/resend-verification', status_code=202)
def resend_verification(body: EmailRequest, db: Session = Depends(get_db)):
    _require_email_delivery()
    try:
        email = normalize_email(body.email)
    except ValueError:
        return {'status': 'verification_if_account_exists'}
    user = db.query(User).filter(
        User.email.ilike(email),
        User.status == 'pending_verification',
    ).first()
    if user:
        db.query(AuthToken).filter(
            AuthToken.user_id == user.id,
            AuthToken.purpose == 'verify_email',
            AuthToken.consumed_at.is_(None),
        ).update({'consumed_at': datetime.now(timezone.utc)}, synchronize_session=False)
        db.commit()
        token = _new_auth_token(db, user, 'verify_email', timedelta(hours=24))
        _send_action_email(user, token, 'verify_email')
    return {'status': 'verification_if_account_exists'}


@router.post('/verify-email')
def verify_email(body: TokenRequest, db: Session = Depends(get_db)):
    auth_token = db.query(AuthToken).filter(
        AuthToken.token_hash == hash_token(body.token),
        AuthToken.purpose == 'verify_email',
        AuthToken.consumed_at.is_(None),
    ).with_for_update().first()
    now = datetime.now(timezone.utc)
    if not auth_token or _as_utc(auth_token.expires_at) <= now:
        raise HTTPException(status_code=400, detail='INVALID_OR_EXPIRED_TOKEN')
    user = db.query(User).filter(User.id == auth_token.user_id).first()
    if not user or user.status != 'pending_verification':
        raise HTTPException(status_code=400, detail='INVALID_OR_EXPIRED_TOKEN')
    auth_token.consumed_at = now
    user.status = 'active'
    db.commit()
    return {'status': 'verified'}


@router.post('/login')
def login(body: Credentials, response: Response, db: Session = Depends(get_db)):
    try:
        email = normalize_email(body.email)
    except ValueError:
        email = ''
    user = db.query(User).filter(User.email.ilike(email)).first() if email else None
    password_hash = user.password_hash if user else _DUMMY_PASSWORD_HASH
    password_matches = verify_password(body.password, password_hash)
    if not user or user.status != 'active' or not password_matches:
        raise HTTPException(status_code=401, detail='INVALID_CREDENTIALS')
    token = issue_session(db, user)
    set_session_cookie(response, token)
    return {'user': user_payload(user)}


@router.post('/logout')
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get(SESSION_COOKIE)
    if raw_token:
        session = db.query(AuthSession).filter(AuthSession.token_hash == hash_token(raw_token)).first()
        if session and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()
    response.delete_cookie(SESSION_COOKIE, path='/', secure=settings.app_env.lower() not in {'development', 'test'}, httponly=True, samesite='lax')
    return {'status': 'logged_out'}


@router.get('/me')
def me(user: User = Depends(get_current_user)):
    return user_payload(user)


@router.patch('/preferences')
def update_preferences(
    body: PreferencesRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.status != 'active':
        raise HTTPException(status_code=403, detail='ACCOUNT_NOT_ACTIVE')
    user.preferred_grade = body.preferred_grade
    if body.preferred_subject_ids is not None:
        try:
            subject_ids = {uuid.UUID(value) for value in body.preferred_subject_ids}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail='Invalid subject selection.') from exc
        subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).all() if subject_ids else []
        if len(subjects) != len(subject_ids):
            raise HTTPException(status_code=422, detail='A selected subject is no longer available.')
        user.preferred_subjects = subjects
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_payload(user)


@router.post('/onboarding')
def complete_onboarding(
    body: OnboardingRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.status != 'active':
        raise HTTPException(status_code=403, detail='ACCOUNT_NOT_ACTIVE')
    if user.onboarding_completed:
        return user_payload(user)
    if not body.terms_accepted:
        raise HTTPException(status_code=422, detail='You must accept the terms to continue.')
    school = (body.school or '').strip()
    if not school:
        raise HTTPException(status_code=422, detail='Please select or enter your school.')
    display_name = (body.display_name or '').strip() or None
    user.school = school
    user.preferred_grade = body.preferred_grade
    if body.preferred_subject_ids:
        try:
            subject_ids = {uuid.UUID(value) for value in body.preferred_subject_ids}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail='Invalid subject selection.') from exc
        subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).all()
        if len(subjects) != len(subject_ids):
            raise HTTPException(status_code=422, detail='A selected subject is no longer available.')
        user.preferred_subjects = subjects
    if display_name:
        user.display_name = display_name
    user.onboarding_completed = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_payload(user)


@router.post('/password-reset/request', status_code=202)
def request_password_reset(body: EmailRequest, db: Session = Depends(get_db)):
    _require_email_delivery()
    try:
        email = normalize_email(body.email)
    except ValueError:
        return {'status': 'reset_if_account_exists'}
    user = db.query(User).filter(User.email.ilike(email), User.status == 'active').first()
    if user:
        db.query(AuthToken).filter(
            AuthToken.user_id == user.id,
            AuthToken.purpose == 'reset_password',
            AuthToken.consumed_at.is_(None),
        ).update({'consumed_at': datetime.now(timezone.utc)}, synchronize_session=False)
        db.commit()
        token = _new_auth_token(db, user, 'reset_password', timedelta(hours=1))
        _send_action_email(user, token, 'reset_password')
    return {'status': 'reset_if_account_exists'}


@router.post('/password-reset/complete')
def complete_password_reset(body: PasswordReset, db: Session = Depends(get_db)):
    try:
        validate_password(body.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    auth_token = db.query(AuthToken).filter(
        AuthToken.token_hash == hash_token(body.token),
        AuthToken.purpose == 'reset_password',
        AuthToken.consumed_at.is_(None),
    ).with_for_update().first()
    now = datetime.now(timezone.utc)
    if not auth_token or _as_utc(auth_token.expires_at) <= now:
        raise HTTPException(status_code=400, detail='INVALID_OR_EXPIRED_TOKEN')
    user = db.query(User).filter(User.id == auth_token.user_id).first()
    if not user or user.status != 'active':
        raise HTTPException(status_code=400, detail='INVALID_OR_EXPIRED_TOKEN')
    auth_token.consumed_at = now
    user.password_hash = hash_password(body.password)
    db.query(AuthSession).filter(
        AuthSession.user_id == user.id,
        AuthSession.revoked_at.is_(None),
    ).update({'revoked_at': now}, synchronize_session=False)
    db.commit()
    return {'status': 'password_updated'}


_DUMMY_PASSWORD_HASH = hash_password('Dummy-Only-Password-Hash-2026!')
