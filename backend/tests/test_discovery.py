import uuid

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.document import Document, ProcessingStatus
from app.models.question import QualityStatus, Question
from app.models.taxonomy import Subject
from app.models.user import User

client = TestClient(app)


def test_discovery_feed_only_returns_reviewed_questions_and_supports_grade_filters():
    with SessionLocal() as db:
        user = User(
            auth_subject=f'discovery-{uuid.uuid4()}',
            email=None,
            display_name='Archive contributor',
        )
        db.add(user)
        db.flush()
        document = Document(
            uploader_id=user.id,
            title='Matric practice test',
            grade=10,
            academic_year=2023,
            mime_type='application/pdf',
            file_size=1024,
            storage_object_key=f'uploads/{uuid.uuid4()}/paper.pdf',
            checksum='test-checksum',
            processing_status=ProcessingStatus.completed,
        )
        pending_document = Document(
            uploader_id=user.id,
            title='Still processing',
            grade=10,
            academic_year=2024,
            mime_type='application/pdf',
            file_size=1024,
            storage_object_key=f'uploads/{uuid.uuid4()}/pending.pdf',
            checksum='test-checksum',
            processing_status=ProcessingStatus.pending,
        )
        db.add_all([document, pending_document])
        db.flush()
        reviewed = Question(
            document_id=document.id,
            extracted_text='Solve the equation x + 3 = 7.',
            quality_status=QualityStatus.reliable,
        )
        held = Question(
            document_id=document.id,
            extracted_text='This question is still being reviewed.',
            quality_status=QualityStatus.held,
        )
        not_published = Question(
            document_id=pending_document.id,
            extracted_text='This paper has not finished processing.',
            quality_status=QualityStatus.reliable,
        )
        db.add_all([reviewed, held, not_published])
        db.commit()
        question_id = str(reviewed.id)
        held_question_id = str(held.id)
        unpublished_question_id = str(not_published.id)
        document_id = str(document.id)

    response = client.get('/api/v1/discovery')
    assert response.status_code == 200
    feed = response.json()
    recent_by_id = {item['id']: item for item in feed['recent']}
    assert question_id in recent_by_id
    assert held_question_id not in recent_by_id
    assert unpublished_question_id not in recent_by_id
    assert feed['for_you'] == []
    recent_item = recent_by_id[question_id]
    assert recent_item['id'] == question_id
    assert recent_item['document_id'] == document_id
    assert recent_item['page'] is None
    assert recent_item['snippet'] == 'Solve the equation x + 3 = 7.'
    assert recent_item['title'] == 'Matric practice test'
    assert recent_item['grade'] == 10
    assert recent_item['academic_year'] == 2023
    assert recent_item['posted_by'] == 'Archive contributor'
    assert recent_item['posted_at']

    grade_response = client.get('/api/v1/discovery', params={'grade': 10})
    assert grade_response.status_code == 200
    recommended_ids = [item['id'] for item in grade_response.json()['for_you']]
    grade_recent_ids = [item['id'] for item in grade_response.json()['recent']]
    assert question_id in recommended_ids
    assert question_id not in grade_recent_ids
    assert held_question_id not in recommended_ids
    assert unpublished_question_id not in recommended_ids
    assert grade_response.json()['grade'] == 10

    search_response = client.get('/api/v1/search', params={'grade': 10})
    assert search_response.status_code == 200
    search_items = search_response.json()
    assert question_id in [item['id'] for item in search_items]
    assert unpublished_question_id not in [item['id'] for item in search_items]
    year_search = client.get('/api/v1/search', params={'q': '2023'})
    assert question_id in [item['id'] for item in year_search.json()]


def test_authenticated_user_can_update_grade_recommendations():
    csrf = client.get('/api/v1/auth/csrf')
    assert csrf.status_code == 200
    client.headers['X-CSRF-Token'] = csrf.json()['csrf_token']
    login = client.post('/api/v1/auth/login', json={
        'email': 'test-admin@example.test',
        'password': 'Test-Only-Admin-Password-2026',
    })
    assert login.status_code == 200

    updated = client.patch('/api/v1/auth/preferences', json={'preferred_grade': 11})
    assert updated.status_code == 200
    assert updated.json()['preferred_grade'] == 11
    invalid = client.patch('/api/v1/auth/preferences', json={'preferred_grade': 8})
    assert invalid.status_code == 422


def test_admin_published_articles_are_searchable_and_subject_preferences_persist():
    csrf = client.get('/api/v1/auth/csrf')
    assert csrf.status_code == 200
    client.headers['X-CSRF-Token'] = csrf.json()['csrf_token']
    login = client.post('/api/v1/auth/login', json={
        'email': 'test-admin@example.test',
        'password': 'Test-Only-Admin-Password-2026',
    })
    assert login.status_code == 200

    subject_name = f'Biology {uuid.uuid4()}'
    with SessionLocal() as db:
        subject = Subject(name=subject_name)
        db.add(subject)
        db.commit()
        subject_id = str(subject.id)

    preferences = client.patch('/api/v1/auth/preferences', json={
        'preferred_grade': 10,
        'preferred_subject_ids': [subject_id],
    })
    assert preferences.status_code == 200
    assert preferences.json()['preferred_grade'] == 10
    assert subject_id in preferences.json()['preferred_subject_ids']

    article = client.post('/api/v1/resources', json={
        'title': 'Cellular respiration overview',
        'summary': 'A concise guide to energy conversion.',
        'body': 'Mitochondria transform nutrients into usable energy.',
        'subject_id': subject_id,
    })
    assert article.status_code == 201
    article_id = article.json()['id']

    suggestions = client.get('/api/v1/search/suggestions', params={'q': 'mitochondria'})
    assert suggestions.status_code == 200
    assert any(item['id'] == article_id and item['type'] == 'article' for item in suggestions.json())

    explore = client.get('/api/v1/search/explore', params={'q': 'mitochondria'})
    assert explore.status_code == 200
    assert any(item['id'] == article_id for item in explore.json()['articles'])

    listed = client.get('/api/v1/resources')
    assert any(item['id'] == article_id for item in listed.json())
    detail = client.get(f'/api/v1/resources/{article_id}')
    assert detail.status_code == 200
    assert detail.json()['subject_id'] == subject_id
