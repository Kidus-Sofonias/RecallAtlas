import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.auth_bootstrap_lock import AuthBootstrapLock
from app.models.user import User

SESSION_COOKIE = 'ra_session'
CSRF_COOKIE = 'ra_csrf'
SESSION_LIFETIME = timedelta(days=14)
_EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def normalize_email(email: str) -> str:
    normalized = email.strip().casefold()
    if len(normalized) > 254 or not _EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError('Enter a valid email address.')
    return normalized


def validate_password(password: str) -> None:
    if len(password) < 8 or len(password) > 128:
        raise ValueError('Password must be between 8 and 128 characters.')


def hash_password(password: str) -> str:
    validate_password(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=2**14, r=8, p=1, dklen=32, maxmem=128 * 1024 * 1024)
    salt_text = base64.urlsafe_b64encode(salt).decode('ascii').rstrip('=')
    digest_text = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
    return f'scrypt$16384$8$1${salt_text}${digest_text}'


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, n, r, p, salt_text, digest_text = encoded.split('$')
        if algorithm != 'scrypt' or (n, r, p) != ('16384', '8', '1'):
            return False
        salt = base64.urlsafe_b64decode(salt_text + '=' * (-len(salt_text) % 4))
        expected = base64.urlsafe_b64decode(digest_text + '=' * (-len(digest_text) % 4))
        actual = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=2**14, r=8, p=1, dklen=len(expected), maxmem=128 * 1024 * 1024)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def create_csrf_token() -> str:
    nonce = secrets.token_urlsafe(32)
    signature = hmac.new(
        settings.secret_key.encode('utf-8'),
        nonce.encode('ascii'),
        hashlib.sha256,
    ).hexdigest()
    return f'{nonce}.{signature}'


def verify_csrf_token(token: str) -> bool:
    try:
        nonce, signature = token.rsplit('.', 1)
    except ValueError:
        return False
    expected = hmac.new(
        settings.secret_key.encode('utf-8'),
        nonce.encode('ascii'),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected)


def issue_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + SESSION_LIFETIME,
    ))
    db.commit()
    return token


def user_payload(user: User) -> dict[str, str | int | list[str] | None | bool]:
    return {
        'id': str(user.id),
        'email': user.email,
        'display_name': user.display_name,
        'role': user.role,
        'onboarding_completed': bool(user.onboarding_completed),
        'preferred_grade': user.preferred_grade,
        'preferred_subject_ids': [str(subject.id) for subject in user.preferred_subjects],
    }


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        raise HTTPException(status_code=401, detail='AUTHENTICATION_REQUIRED')
    session = db.query(AuthSession).filter(
        AuthSession.token_hash == hash_token(raw_token),
        AuthSession.revoked_at.is_(None),
    ).first()
    if not session or _as_utc(session.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail='AUTHENTICATION_REQUIRED')
    user = db.query(User).filter(User.id == session.user_id, User.status == 'active').first()
    if not user:
        raise HTTPException(status_code=401, detail='AUTHENTICATION_REQUIRED')
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail='FORBIDDEN')
    return user


def require_onboarding(user: User = Depends(get_current_user)) -> User:
    if user.role != 'admin' and not user.onboarding_completed:
        raise HTTPException(status_code=403, detail='ONBOARDING_REQUIRED')
    return user


def bootstrap_admin(db: Session, email: str, password: str) -> bool:
    lock_updated = db.query(AuthBootstrapLock).filter(
        AuthBootstrapLock.id == 1,
    ).update(
        {AuthBootstrapLock.id: AuthBootstrapLock.id},
        synchronize_session=False,
    )
    if lock_updated != 1:
        raise RuntimeError('Administrator bootstrap lock is missing; apply database migrations.')
    admins = db.query(User).filter(User.role == 'admin').first()
    if admins:
        return False
    if not email or not password:
        raise RuntimeError(
            'No administrator exists. Configure ADMIN_EMAIL and ADMIN_INITIAL_PASSWORD '
            'to create the initial administrator.'
        )

    normalized_email = normalize_email(email)
    password_hash = hash_password(password)
    existing = db.query(User).filter(User.email.ilike(normalized_email)).first()
    if existing:
        raise RuntimeError('ADMIN_EMAIL already belongs to a non-administrator account.')
    user = User(
        auth_subject=f'password:{normalized_email}',
        email=normalized_email,
        password_hash=password_hash,
        display_name='Administrator',
        status='active',
        role='admin',
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if db.query(User).filter(User.role == 'admin').first():
            return False
        raise
    return True


def set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        secure=settings.app_env.lower() not in {'development', 'test'},
        samesite='lax',
        path='/',
    )
