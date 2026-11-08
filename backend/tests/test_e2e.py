import io
import re
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.question import Question, QualityStatus
import uuid

client = TestClient(app)

PDF_PATH = Path(__file__).resolve().parents[2] / 'sample.pdf'
PDF = PDF_PATH.read_bytes()

def test_e2e(monkeypatch):
    from app.api import uploads
    from app.services.malware_scan import ScanResult, ScanStatus
    from app.services.processing_queue import process_one_job

    monkeypatch.setattr(
        uploads,
        'scan_bytes',
        lambda data: ScanResult(ScanStatus.clean, 'clean'),
    )
    csrf_response = client.get('/api/v1/auth/csrf')
    assert csrf_response.status_code == 200
    client.headers['X-CSRF-Token'] = csrf_response.json()['csrf_token']
    login = client.post('/api/v1/auth/login', json={
        'email': 'test-admin@example.test',
        'password': 'Test-Only-Admin-Password-2026',
    })
    assert login.status_code == 200

    r = client.post('/api/v1/uploads/initiate', json={
        'filename': PDF_PATH.name,
        'mime_type': 'application/pdf',
        'file_size': len(PDF),
        'title': 'Repository sample PDF',
        'grade': 12,
        'academic_year': 2019,
        'no_answers_confirmed': True,
    })
    assert r.status_code==200
    did = r.json()['document_id']
    r = client.post(f'/api/v1/uploads/{did}/complete', files={'file':(PDF_PATH.name, io.BytesIO(PDF), 'application/pdf')})
    assert r.status_code==200
    assert process_one_job('test-worker')
    r = client.get(f'/api/v1/documents/{did}')
    assert r.json()['status']=='completed'
    assert 'checksum' not in r.json()
    assert r.json()['title'] == 'Repository sample PDF'
    assert r.json()['grade'] == 12
    assert r.json()['academic_year'] == 2019
    r = client.get(f'/api/v1/documents/{did}/questions')
    assert r.status_code == 200
    assert r.json() == []
    vector_results = client.post('/api/v1/search/hybrid-vector', json={'vector': [0.0] * 384})
    assert vector_results.status_code == 200

    with SessionLocal() as db:
        question = db.query(Question).filter(Question.document_id == uuid.UUID(did)).first()
        assert question is not None
        assert question.quality_status == QualityStatus.held
        question_id = str(question.id)
        search_term = re.findall(r'\w+', question.extracted_text)[0]

    assert client.get(f'/api/v1/questions/{question_id}').status_code == 404
    review = client.post(f'/api/v1/questions/{question_id}/review', params={'decision': 'approve'})
    assert review.status_code == 200
    assert client.get(f'/api/v1/questions/{question_id}').status_code == 200
    assert len(client.get(f'/api/v1/documents/{did}/questions').json()) >= 1
    results = client.get('/api/v1/search', params={'q': search_term}).json()
    assert any(result['document_id'] == did for result in results)
    explore_results = client.get('/api/v1/search/explore', params={'q': search_term}).json()
    assert any(result['id'] == question_id for result in explore_results['questions'])
    assert any(result['id'] == did for result in explore_results['papers'])
    vector_results = client.post('/api/v1/search/hybrid-vector', json={'vector': [0.0] * 384})
    assert any(result['document_id'] == did for result in vector_results.json())

    bookmark = client.post('/api/v1/bookmarks', params={'target_type': 'question', 'target_id': question_id})
    assert bookmark.status_code == 200
    bookmark_id = bookmark.json()['id']
    saved = client.get('/api/v1/bookmarks').json()
    assert any(item['id'] == bookmark_id for item in saved)
    assert client.delete(f'/api/v1/bookmarks/{bookmark_id}').status_code == 200
