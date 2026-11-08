import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api.auth import _new_auth_token
from app.db.session import SessionLocal
from app.main import app
from app.models.auth_session import AuthSession
from app.models.audit_event import AuditEvent
from app.models.bookmark import Bookmark
from app.models.collection import Collection, CollectionItem
from app.models.document import Document
from app.models.notification import Notification
from app.models.user import User
from app.api import auth as auth_api
from app.services.auth import (
    SESSION_COOKIE,
    bootstrap_admin,
    hash_password,
    hash_token,
    issue_session,
    validate_password,
    verify_csrf_token,
    verify_password,
)

client = TestClient(app)
ADMIN_EMAIL = 'test-admin@example.test'
ADMIN_PASSWORD = 'Test-Only-Admin-Password-2026'


def _csrf(client_instance: TestClient) -> str:
    response = client_instance.get('/api/v1/auth/csrf')
    assert response.status_code == 200
    token = response.json()['csrf_token']
    client_instance.headers['X-CSRF-Token'] = token
    return token


def _login(client_instance: TestClient, email: str, password: str):
    _csrf(client_instance)
    return client_instance.post(
        '/api/v1/auth/login',
        json={'email': email, 'password': password},
    )


def test_password_hashing_and_policy():
    password = 'Strong-Test-Password-2026'
    encoded = hash_password(password)
    assert encoded.startswith('scrypt$16384$8$1$')
    assert verify_password(password, encoded)
    assert not verify_password('Wrong-Password-2026!', encoded)
    try:
        validate_password('weak')
    except ValueError:
        pass
    else:
        raise AssertionError('Weak passwords must be rejected.')


def test_admin_bootstrap_is_idempotent_and_never_resets_password():
    with SessionLocal() as db:
        assert not bootstrap_admin(db, ADMIN_EMAIL, 'Different-Password-2026!')
        assert not bootstrap_admin(db, ADMIN_EMAIL, 'Another-Different-Password-2026!')
        admin = db.query(User).filter(User.email == ADMIN_EMAIL).one()
        assert verify_password(ADMIN_PASSWORD, admin.password_hash)


def test_anonymous_requests_and_csrf_are_rejected():
    anonymous = TestClient(app)
    assert anonymous.get('/api/v1/bookmarks').status_code == 401
    assert anonymous.get('/api/v1/admin/users').status_code == 401
    assert anonymous.post('/api/v1/auth/login', json={'email': ADMIN_EMAIL, 'password': ADMIN_PASSWORD}).status_code == 403


def test_csrf_token_is_signed_and_tampering_is_rejected():
    csrf_client = TestClient(app)
    token = _csrf(csrf_client)
    assert verify_csrf_token(token)
    assert not verify_csrf_token(f'{token[:-1]}{"0" if token[-1] != "0" else "1"}')


def test_admin_login_me_cookie_and_logout_revoke_session():
    admin_client = TestClient(app)
    response = _login(admin_client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert response.status_code == 200
    cookie = response.cookies.get(SESSION_COOKIE)
    assert cookie
    assert response.headers['set-cookie'].lower().find('httponly') >= 0
    assert admin_client.get('/api/v1/auth/me').json()['role'] == 'admin'
    assert admin_client.get('/api/v1/admin/users').status_code == 200

    with SessionLocal() as db:
        stored = db.query(AuthSession).filter(AuthSession.token_hash == hash_token(cookie)).one()
        assert stored.token_hash != cookie

    assert admin_client.post('/api/v1/auth/logout').status_code == 200
    assert admin_client.get('/api/v1/auth/me').status_code == 401


def test_profile_update_and_deletion_request_revoke_sessions():
    email = 'profile-owner@example.test'
    password = 'Profile-Owner-Password-2026!'
    user_id = uuid.uuid4()
    with SessionLocal() as db:
        db.add(User(
            id=user_id,
            auth_subject=f'password:{email}',
            email=email,
            password_hash=hash_password(password),
            display_name='Profile Owner',
            status='active',
            role='user',
            onboarding_completed=True,
        ))
        db.commit()

    profile_client = TestClient(app)
    assert _login(profile_client, email, password).status_code == 200
    profile = profile_client.get('/api/v1/me')
    assert profile.status_code == 200
    assert profile.json()['display_name'] == 'Profile Owner'

    updated = profile_client.patch('/api/v1/me', json={
        'display_name': 'Updated Name',
        'school': 'Example School',
    })
    assert updated.status_code == 200
    assert updated.json()['display_name'] == 'Updated Name'
    assert updated.json()['school'] == 'Example School'

    assert profile_client.post(
        '/api/v1/me/deletion-request',
        json={'confirm': False},
    ).status_code == 422
    deletion = profile_client.post(
        '/api/v1/me/deletion-request',
        json={'confirm': True},
    )
    assert deletion.status_code == 202
    with SessionLocal() as db:
        stored_user = db.query(User).filter(User.id == user_id).one()
        stored_session = db.query(AuthSession).filter(AuthSession.user_id == user_id).one()
        assert stored_user.deletion_requested_at is not None
        assert stored_session.revoked_at is not None


def test_admin_approval_anonymizes_profile_and_removes_private_associations():
    email = f'delete-me-{uuid.uuid4()}@example.test'
    password = 'Deletion-Owner-Password-2026!'
    user_id = uuid.uuid4()
    with SessionLocal() as db:
        user = User(
            id=user_id,
            auth_subject=f'password:{email}',
            email=email,
            password_hash=hash_password(password),
            display_name='Private Name',
            school='Private School',
            status='active',
            role='user',
            onboarding_completed=True,
        )
        db.add(user)
        db.flush()
        document = Document(
            uploader_id=user.id,
            title='Retained academic contribution',
            original_filename='paper.pdf',
            mime_type='application/pdf',
            file_size=20,
            storage_object_key=f'uploads/{uuid.uuid4()}/original.pdf',
            checksum='private-checksum',
            security_status='clean',
        )
        collection = Collection(owner_id=user.id, name='Private collection')
        db.add_all([
            document,
            collection,
            Bookmark(user_id=user.id, target_type='question', target_id=uuid.uuid4()),
            Notification(recipient_id=user.id, title='Private notification'),
        ])
        db.flush()
        db.add(CollectionItem(collection_id=collection.id, question_id=uuid.uuid4()))
        session_token = issue_session(db, user)
        db.commit()
        document_id = document.id

    requester = TestClient(app)
    requester.cookies.set(SESSION_COOKIE, session_token)
    csrf = _csrf(requester)
    request = requester.post(
        '/api/v1/me/deletion-request',
        json={'confirm': True},
        headers={'X-CSRF-Token': csrf},
    )
    assert request.status_code == 202
    assert requester.get('/api/v1/auth/me').status_code == 401

    admin_client = TestClient(app)
    assert _login(admin_client, ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 200
    queued = admin_client.get('/api/v1/admin/deletion-requests')
    assert queued.status_code == 200
    assert any(item['user_id'] == str(user_id) for item in queued.json())
    decision = admin_client.post(
        f'/api/v1/admin/deletion-requests/{user_id}/decision',
        json={'decision': 'approve', 'note': 'Confirmed deletion request after account verification.'},
    )
    assert decision.status_code == 200
    assert decision.json()['deletion_request_status'] == 'completed'

    with SessionLocal() as db:
        deleted_user = db.query(User).filter(User.id == user_id).one()
        assert deleted_user.email is None
        assert deleted_user.password_hash is None
        assert deleted_user.school is None
        assert deleted_user.display_name == 'Deleted contributor'
        assert deleted_user.status == 'deleted'
        assert deleted_user.deletion_request_status == 'completed'
        assert db.query(Document).filter(Document.id == document_id).one().uploader_id == user_id
        assert db.query(Collection).filter(Collection.owner_id == user_id).count() == 0
        assert db.query(Bookmark).filter(Bookmark.user_id == user_id).count() == 0
        assert db.query(Notification).filter(Notification.recipient_id == user_id).count() == 0
        assert db.query(AuthSession).filter(AuthSession.user_id == user_id).count() == 0
        assert db.query(AuditEvent).filter(
            AuditEvent.action == 'account.deletion_completed',
            AuditEvent.target_id == str(user_id),
        ).count() == 1


def test_admin_can_reject_deletion_request_and_restore_account():
    email = f'deletion-review-{uuid.uuid4()}@example.test'
    user_id = uuid.uuid4()
    with SessionLocal() as db:
        user = User(
            id=user_id,
            auth_subject=f'password:{email}',
            email=email,
            password_hash=hash_password('Deletion-Review-Password-2026!'),
            status='deletion_requested',
            role='user',
            deletion_requested_at=datetime.now(timezone.utc),
            deletion_request_status='pending',
        )
        db.add(user)
        db.commit()

    admin_client = TestClient(app)
    assert _login(admin_client, ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 200
    decision = admin_client.post(
        f'/api/v1/admin/deletion-requests/{user_id}/decision',
        json={'decision': 'reject', 'note': 'Request could not be verified; account retained.'},
    )
    assert decision.status_code == 200
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).one()
        assert user.status == 'active'
        assert user.email == email
        assert user.deletion_request_status == 'rejected'


def test_users_cannot_read_other_users_private_data_or_admin_routes():
    password = 'Ordinary-User-Password-2026!'
    other_user_id = uuid.uuid4()
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == ADMIN_EMAIL).one()
        admin_bookmark_id = uuid.uuid4()
        user = User(
            id=other_user_id,
            auth_subject='password:student@example.test',
            email='student@example.test',
            password_hash=hash_password(password),
            display_name='Student',
            status='active',
            role='user',
            onboarding_completed=True,
        )
        db.add(user)
        db.add(Bookmark(
            id=admin_bookmark_id,
            user_id=admin.id,
            target_type='question',
            target_id=uuid.uuid4(),
        ))
        db.commit()

    student_client = TestClient(app)
    assert _login(student_client, 'student@example.test', password).status_code == 200
    assert student_client.get('/api/v1/admin/users').status_code == 403
    assert student_client.get('/api/v1/admin/deletion-requests').status_code == 403
    assert student_client.post(
        f'/api/v1/admin/deletion-requests/{other_user_id}/decision',
        json={'decision': 'approve', 'note': 'Unauthorized approval attempt.'},
    ).status_code == 403
    assert student_client.get('/api/v1/bookmarks').json() == []
    assert student_client.delete(f'/api/v1/bookmarks/{admin_bookmark_id}').status_code == 404


def test_email_verification_activates_once_and_registration_requires_delivery(monkeypatch):
    password = 'Verifiable-User-Password-2026!'
    user_email = 'verified@example.test'
    verification_tokens: list[str] = []
    register_client = TestClient(app)
    _csrf(register_client)
    register_client.headers['Origin'] = 'http://127.0.0.1:5173'
    monkeypatch.setattr(auth_api.settings, 'app_env', 'production')
    monkeypatch.setattr(auth_api.settings, 'email_dev_mode', False)
    monkeypatch.setattr(auth_api.settings, 'resend_api_key', 'test-provider-key')
    monkeypatch.setattr(
        auth_api,
        '_send_action_email',
        lambda user, token, purpose: verification_tokens.append(token),
    )

    response = register_client.post(
        '/api/v1/auth/register',
        json={'email': user_email, 'password': password},
    )
    assert response.status_code == 202
    assert len(verification_tokens) == 1
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == user_email).one()
        assert user.status == 'pending_verification'

    verification = register_client.post(
        '/api/v1/auth/verify-email',
        json={'token': verification_tokens[0]},
    )
    assert verification.status_code == 200
    assert register_client.post(
        '/api/v1/auth/verify-email',
        json={'token': verification_tokens[0]},
    ).status_code == 400
    monkeypatch.setattr(auth_api.settings, 'app_env', 'test')
    assert _login(register_client, user_email, password).status_code == 200


def test_registration_in_development_creates_active_user_and_session():
    registration_client = TestClient(app)
    _csrf(registration_client)
    email = f'dev-{uuid.uuid4()}@example.test'
    password = 'Strong-User-Password-2026!'
    response = registration_client.post(
        '/api/v1/auth/register',
        json={
            'email': email,
            'password': password,
        },
    )
    assert response.status_code == 202
    assert response.json()['user']['role'] == 'user'
    assert response.json()['development_account'] is True
    assert registration_client.get('/api/v1/auth/me').status_code == 200
    duplicate = registration_client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': password},
    )
    assert duplicate.status_code == 409
    assert registration_client.post('/api/v1/auth/logout').status_code == 200
    assert _login(registration_client, email, password).status_code == 200


def test_production_registration_fails_closed_without_email_delivery(monkeypatch):
    registration_client = TestClient(app)
    _csrf(registration_client)
    registration_client.headers['Origin'] = 'http://127.0.0.1:5173'
    monkeypatch.setattr(auth_api.settings, 'app_env', 'production')
    monkeypatch.setattr(auth_api.settings, 'email_dev_mode', True)
    email = f'email-disabled-{uuid.uuid4()}@example.test'
    response = registration_client.post(
        '/api/v1/auth/register',
        json={'email': email, 'password': 'Strong-User-Password-2026!'},
    )
    assert response.status_code == 503
    with SessionLocal() as db:
        assert db.query(User).filter(User.email == email).first() is None


def test_password_reset_revokes_existing_sessions():
    password = 'Resettable-User-Password-2026!'
    user_email = 'resettable@example.test'
    with SessionLocal() as db:
        user = User(
            auth_subject=f'password:{user_email}',
            email=user_email,
            password_hash=hash_password(password),
            display_name='Resettable',
            status='active',
            role='user',
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        reset_token = _new_auth_token(db, user, 'reset_password', timedelta(hours=1))

    reset_client = TestClient(app)
    assert _login(reset_client, user_email, password).status_code == 200
    _csrf(reset_client)
    response = reset_client.post(
        '/api/v1/auth/password-reset/complete',
        json={'token': reset_token, 'password': 'Updated-Password-2026!'},
    )
    assert response.status_code == 200
    assert reset_client.get('/api/v1/auth/me').status_code == 401
