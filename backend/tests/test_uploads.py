import uuid

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.job import ProcessingJob
from app.models.question import Question, QualityStatus
from app.models.user import User
from app.services.auth import issue_session
from app.storage.files import save_bytes

client = TestClient(app)

def authenticate():
    csrf = client.get('/api/v1/auth/csrf').json()['csrf_token']
    client.headers['X-CSRF-Token'] = csrf
    response = client.post('/api/v1/auth/login', json={
        'email': 'test-admin@example.test',
        'password': 'Test-Only-Admin-Password-2026',
    })
    assert response.status_code == 200

def test_initiate_ok():
    authenticate()
    r = client.post('/api/v1/uploads/initiate', json={
        'filename': 't.pdf',
        'mime_type': 'application/pdf',
        'file_size': 1000,
        'no_answers_confirmed': True,
    })
    assert r.status_code == 200
    assert 'document_id' in r.json()

def test_unsupported():
    authenticate()
    r = client.post('/api/v1/uploads/initiate', json={'filename':'t.txt','mime_type':'text/plain','file_size':1000})
    assert r.status_code == 415

def test_supported_extension_and_mime_must_match():
    authenticate()
    response = client.post('/api/v1/uploads/initiate', json={
        'filename': 'notes.pdf',
        'mime_type': 'image/png',
        'file_size': 1000,
    })
    assert response.status_code == 415

def test_pptx_upload_format_is_supported():
    authenticate()
    response = client.post('/api/v1/uploads/initiate', json={
        'filename': 'worksheet.pptx',
        'mime_type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'file_size': 1000,
        'no_answers_confirmed': True,
    })
    assert response.status_code == 200

def test_upload_content_must_match_declared_mime_type():
    authenticate()
    initiated = client.post('/api/v1/uploads/initiate', json={
        'filename': 'notes.pdf',
        'mime_type': 'application/pdf',
        'file_size': 20,
        'no_answers_confirmed': True,
    })
    assert initiated.status_code == 200
    response = client.post(
        initiated.json()['upload_url'],
        files={'file': ('notes.pdf', b'not actually a pdf', 'application/pdf')},
    )
    assert response.status_code == 415

def test_private_original_download_is_available_to_admin():
    authenticate()
    payload = b'%PDF-1.4 test fixture'
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == 'test-admin@example.test').one()
        document = Document(
            uploader_id=admin.id,
            title='Private source',
            original_filename='source.pdf',
            mime_type='application/pdf',
            file_size=len(payload),
            storage_object_key=f'uploads/{uuid.uuid4()}/original.pdf',
            checksum='test',
        )
        db.add(document)
        db.commit()
        document_id = document.id
        storage_key = document.storage_object_key
    save_bytes(storage_key, payload)

    response = client.get(f'/api/v1/documents/{document_id}/source')

    assert response.status_code == 200
    assert response.content == payload
    assert response.headers['cache-control'] == 'private, no-store'
    assert 'source.pdf' in response.headers['content-disposition']

def test_private_pdf_preview_is_inline_and_available_to_admin():
    authenticate()
    payload = b'%PDF-1.4 test fixture'
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == 'test-admin@example.test').one()
        document = Document(
            uploader_id=admin.id,
            title='Private source',
            original_filename='source.pdf',
            mime_type='application/pdf',
            file_size=len(payload),
            storage_object_key=f'uploads/{uuid.uuid4()}/original.pdf',
            checksum='test',
        )
        db.add(document)
        db.commit()
        document_id = document.id
        storage_key = document.storage_object_key
    save_bytes(storage_key, payload)

    response = client.get(f'/api/v1/documents/{document_id}/preview')

    assert response.status_code == 200
    assert response.content == payload
    assert response.headers['content-type'] == 'application/pdf'
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.headers['content-disposition'].startswith('inline;')

def test_private_original_download_is_hidden_from_other_users():
    payload = b'%PDF-1.4 private'
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == 'test-admin@example.test').one()
        user = User(
            auth_subject=f'password:reader-{uuid.uuid4()}@example.test',
            email=f'reader-{uuid.uuid4()}@example.test',
            status='active',
            role='user',
            onboarding_completed=True,
        )
        document = Document(
            uploader_id=admin.id,
            title='Private source',
            original_filename='private.pdf',
            mime_type='application/pdf',
            file_size=len(payload),
            storage_object_key=f'uploads/{uuid.uuid4()}/original.pdf',
            checksum='test',
        )
        db.add_all([user, document])
        db.commit()
        document_id = document.id
        storage_key = document.storage_object_key
        session_token = issue_session(db, user)
    save_bytes(storage_key, payload)
    reader = TestClient(app)
    reader.cookies.set('ra_session', session_token)

    response = reader.get(f'/api/v1/documents/{document_id}/source')

    assert response.status_code == 404
    assert reader.get(f'/api/v1/documents/{document_id}/preview').status_code == 404

def test_admin_review_queue_exposes_held_extraction_with_source():
    authenticate()
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == 'test-admin@example.test').one()
        document = Document(
            uploader_id=admin.id,
            title='Review source',
            original_filename='review.pdf',
            mime_type='application/pdf',
            file_size=10,
            storage_object_key=f'uploads/{uuid.uuid4()}/original.pdf',
            checksum='test',
        )
        db.add(document)
        db.flush()
        question = Question(
            document_id=document.id,
            extracted_text='Question awaiting review',
            quality_status=QualityStatus.held,
            question_type='unknown',
            content_json='{"blocks":[]}',
            quality_signals_json='{"requires_review":true}',
            extraction_version='2',
        )
        db.add(question)
        db.commit()
        question_id = str(question.id)

    response = client.get('/api/v1/admin/question-review-queue')

    assert response.status_code == 200
    queued = next(item for item in response.json() if item['id'] == question_id)
    assert queued['document_title'] == 'Review source'
    assert queued['text'] == 'Question awaiting review'
    assert queued['quality_signals']['requires_review'] is True
    assert queued['source_download_url'].endswith('/source')
    assert queued['source_page_url'] is None
    rejected = client.post(f'/api/v1/questions/{question_id}/review?decision=reject')
    assert rejected.status_code == 200
    assert rejected.json()['review_status'] == 'rejected'
    assert all(item['id'] != question_id for item in client.get('/api/v1/admin/question-review-queue').json())

def test_too_large():
    authenticate()
    r = client.post('/api/v1/uploads/initiate', json={'filename':'t.pdf','mime_type':'application/pdf','file_size':100*1024*1024})
    assert r.status_code == 413

def test_upload_requires_no_answers_policy_confirmation():
    authenticate()
    response = client.post('/api/v1/uploads/initiate', json={
        'filename': 'practice.pdf',
        'mime_type': 'application/pdf',
        'file_size': 1000,
    })
    assert response.status_code == 422
    assert response.json()['detail'] == 'NO_ANSWERS_POLICY_CONFIRMATION_REQUIRED'

def test_optional_grade_and_year_metadata_are_persisted():
    authenticate()
    response = client.post('/api/v1/uploads/initiate', json={
        'filename': 'matric-2019.pdf',
        'mime_type': 'application/pdf',
        'file_size': 1000,
        'title': 'Matric 2019',
        'grade': 12,
        'academic_year': 2019,
        'no_answers_confirmed': True,
    })
    assert response.status_code == 200
    with SessionLocal() as db:
        document = db.query(Document).filter(Document.id == uuid.UUID(response.json()['document_id'])).one()
        assert document.grade == 12
        assert document.academic_year == 2019


def test_unavailable_scanner_quarantines_and_admin_rescan_releases(monkeypatch):
    import io
    from pathlib import Path
    from app.api import uploads, admin as admin_api
    from app.services.malware_scan import ScanResult, ScanStatus
    from app.services import extraction
    from app.services.processing_queue import claim_job, run_claimed_job

    payload = (Path(__file__).resolve().parents[2] / 'sample.pdf').read_bytes()
    monkeypatch.setattr(
        uploads,
        'scan_bytes',
        lambda data: ScanResult(ScanStatus.unavailable, 'scanner_unreachable'),
    )
    initiated = client.post('/api/v1/uploads/initiate', json={
        'filename': 'sample.pdf',
        'mime_type': 'application/pdf',
        'file_size': len(payload),
        'no_answers_confirmed': True,
    })
    document_id = initiated.json()['document_id']
    completed = client.post(
        initiated.json()['upload_url'],
        files={'file': ('sample.pdf', io.BytesIO(payload), 'application/pdf')},
    )
    assert completed.status_code == 200
    assert completed.json()['status'] == 'quarantined'
    assert completed.json()['security_status'] == 'unavailable'
    with SessionLocal() as db:
        document = db.query(Document).filter(Document.id == uuid.UUID(document_id)).one()
        assert document.storage_object_key.startswith(f'quarantine/{document_id}/')
        assert document.processing_status.value == 'held'
        assert document.security_status == 'unavailable'
    assert any(item['id'] == document_id for item in client.get('/api/v1/admin/security-quarantine').json())

    monkeypatch.setattr(
        admin_api,
        'scan_bytes',
        lambda data: ScanResult(ScanStatus.clean, 'clean'),
    )
    monkeypatch.setattr(extraction, 'extract_candidates', lambda data, mime_type: (1, []))
    released = client.post(f'/api/v1/admin/documents/{document_id}/security-rescan')
    assert released.status_code == 200
    assert released.json()['security_status'] == 'clean'
    worker_id = 'quarantine-test-worker'
    claimed_job = claim_job(completed.json()['job_id'], worker_id)
    assert claimed_job == completed.json()['job_id']
    run_claimed_job(claimed_job, worker_id)
    with SessionLocal() as db:
        document = db.query(Document).filter(Document.id == uuid.UUID(document_id)).one()
        assert document.security_status == 'clean'
        assert document.storage_object_key.startswith(f'uploads/{document_id}/')
        assert document.processing_status.value == 'held'


def test_quarantine_rejection_requires_rationale(monkeypatch):
    import io
    from pathlib import Path
    from app.api import uploads
    from app.services.malware_scan import ScanResult, ScanStatus

    payload = (Path(__file__).resolve().parents[2] / 'sample.pdf').read_bytes()
    monkeypatch.setattr(
        uploads,
        'scan_bytes',
        lambda data: ScanResult(ScanStatus.infected, 'malware_detected'),
    )
    initiated = client.post('/api/v1/uploads/initiate', json={
        'filename': 'sample.pdf',
        'mime_type': 'application/pdf',
        'file_size': len(payload),
        'no_answers_confirmed': True,
    })
    document_id = initiated.json()['document_id']
    completed = client.post(
        initiated.json()['upload_url'],
        files={'file': ('sample.pdf', io.BytesIO(payload), 'application/pdf')},
    )
    assert completed.json()['security_status'] == 'infected'
    invalid = client.post(
        f'/api/v1/admin/documents/{document_id}/security-reject',
        json={'note': 'no'},
    )
    assert invalid.status_code == 422
    rejected = client.post(
        f'/api/v1/admin/documents/{document_id}/security-reject',
        json={'note': 'Confirmed malware detection; reject the upload.'},
    )
    assert rejected.status_code == 200
    with SessionLocal() as db:
        document = db.query(Document).filter(Document.id == uuid.UUID(document_id)).one()
        assert document.security_status == 'rejected'
        assert document.security_reviewed_by is not None
        assert document.security_review_note.startswith('Confirmed malware')


def test_quarantined_source_is_not_downloadable_by_uploader(monkeypatch):
    import io
    from pathlib import Path
    from fastapi.testclient import TestClient
    from app.api import uploads
    from app.services.auth import issue_session
    from app.services.malware_scan import ScanResult, ScanStatus

    payload = (Path(__file__).resolve().parents[2] / 'sample.pdf').read_bytes()
    monkeypatch.setattr(
        uploads,
        'scan_bytes',
        lambda data: ScanResult(ScanStatus.unavailable, 'scanner_unreachable'),
    )
    with SessionLocal() as db:
        user = User(
            auth_subject=f'password:quarantine-{uuid.uuid4()}@example.test',
            email=f'quarantine-{uuid.uuid4()}@example.test',
            status='active',
            role='user',
            onboarding_completed=True,
        )
        db.add(user)
        db.commit()
        token = issue_session(db, user)
    uploader = TestClient(app)
    uploader.cookies.set('ra_session', token)
    csrf = uploader.get('/api/v1/auth/csrf').json()['csrf_token']
    uploader.headers['X-CSRF-Token'] = csrf
    initiated = uploader.post('/api/v1/uploads/initiate', json={
        'filename': 'sample.pdf',
        'mime_type': 'application/pdf',
        'file_size': len(payload),
        'no_answers_confirmed': True,
    })
    document_id = initiated.json()['document_id']
    uploaded = uploader.post(
        initiated.json()['upload_url'],
        files={'file': ('sample.pdf', io.BytesIO(payload), 'application/pdf')},
    )
    assert uploaded.json()['security_status'] == 'unavailable'
    assert uploader.get(f'/api/v1/documents/{document_id}/source').status_code == 404


def test_admin_can_inspect_and_retry_only_failed_processing_jobs():
    authenticate()
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == 'test-admin@example.test').one()
        document = Document(
            uploader_id=admin.id,
            title='Failed job fixture',
            original_filename='failed.pdf',
            mime_type='application/pdf',
            file_size=5,
            storage_object_key=f'uploads/{uuid.uuid4()}/original.pdf',
            checksum='fixture',
            security_status='clean',
            processing_status='failed',
        )
        db.add(document)
        db.flush()
        job = ProcessingJob(
            document_id=document.id,
            status='failed',
            job_type='extract',
            attempt_count=3,
            error_category='RuntimeError',
        )
        db.add(job)
        db.commit()
        job_id = str(job.id)

    listed = client.get('/api/v1/admin/jobs?status=failed')
    assert listed.status_code == 200
    assert any(item['id'] == job_id for item in listed.json())
    retried = client.post(f'/api/v1/admin/jobs/{job_id}/retry')
    assert retried.status_code == 200
    assert retried.json()['status'] == 'queued'
    assert client.post(f'/api/v1/admin/jobs/{job_id}/retry').status_code == 409
