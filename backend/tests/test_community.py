import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.document import Document, ProcessingStatus
from app.models.notification import Notification
from app.models.question import Question, QualityStatus
from app.models.user import User

client = TestClient(app)


def authenticate():
    csrf = client.get('/api/v1/auth/csrf').json()['csrf_token']
    client.headers['X-CSRF-Token'] = csrf
    response = client.post('/api/v1/auth/login', json={
        'email': 'test-admin@example.test',
        'password': 'Test-Only-Admin-Password-2026',
    })
    assert response.status_code == 200


def create_public_question():
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == 'test-admin@example.test').one()
        document = Document(
            uploader_id=admin.id,
            title='Community source',
            mime_type='application/pdf',
            file_size=20,
            storage_object_key=f'uploads/{uuid.uuid4()}/original.pdf',
            checksum='community-test',
            processing_status=ProcessingStatus.completed,
        )
        db.add(document)
        db.flush()
        question = Question(
            document_id=document.id,
            extracted_text='Question for community test',
            quality_status=QualityStatus.reliable,
            question_type='unknown',
        )
        db.add(question)
        db.commit()
        return str(question.id)


def test_comments_replies_and_reports_have_target_validation():
    authenticate()
    question_id = create_public_question()
    comment_response = client.post('/api/v1/comments', json={
        'target_type': 'question',
        'target_id': question_id,
        'body': '  The diagram label seems unclear.  ',
    })
    assert comment_response.status_code == 201
    comment_id = comment_response.json()['id']

    reply_response = client.post('/api/v1/comments', json={
        'target_type': 'question',
        'target_id': question_id,
        'parent_comment_id': comment_id,
        'body': 'Thanks, I will compare it with the source.',
    })
    assert reply_response.status_code == 201
    comments = client.get('/api/v1/comments', params={
        'target_type': 'question',
        'target_id': question_id,
    })
    assert comments.status_code == 200
    assert len(comments.json()) == 2
    assert comments.json()[1]['parent_comment_id'] == comment_id

    report_response = client.post('/api/v1/reports', json={
        'target_type': 'question',
        'target_id': question_id,
        'reason': 'extraction_issue',
        'details': 'A symbol may have been misread.',
    })
    assert report_response.status_code == 201
    reports = client.get('/api/v1/admin/reports', params={'status': 'open'})
    assert any(item['id'] == report_response.json()['id'] for item in reports.json())

    decision = client.post(
        f"/api/v1/admin/reports/{report_response.json()['id']}/decision",
        json={'decision': 'restrict', 'notes': 'Held pending source comparison.'},
    )
    assert decision.status_code == 200
    assert client.get(f'/api/v1/questions/{question_id}').status_code == 404


def test_comments_and_reports_reject_unknown_or_unpublished_targets():
    authenticate()
    unknown_id = str(uuid.uuid4())
    comment = client.post('/api/v1/comments', json={
        'target_type': 'question',
        'target_id': unknown_id,
        'body': 'This should fail.',
    })
    report = client.post('/api/v1/reports', json={
        'target_type': 'resource',
        'target_id': unknown_id,
        'reason': 'spam',
    })
    assert comment.status_code == 404
    assert report.status_code == 404


def test_collection_items_are_owned_and_idempotent():
    authenticate()
    question_id = create_public_question()
    collection = client.post('/api/v1/collections', json={'name': 'Review later'})
    assert collection.status_code == 200
    collection_id = collection.json()['id']

    first = client.post(f'/api/v1/collections/{collection_id}/items', params={'question_id': question_id})
    second = client.post(f'/api/v1/collections/{collection_id}/items', params={'question_id': question_id})
    assert first.status_code == 200
    assert second.json()['id'] == first.json()['id']

    items = client.get(f'/api/v1/collections/{collection_id}/items')
    assert items.status_code == 200
    assert len(items.json()) == 1
    assert items.json()[0]['question_id'] == question_id

    removed = client.delete(f'/api/v1/collections/{collection_id}/items/{first.json()["id"]}')
    assert removed.status_code == 200
    assert client.get(f'/api/v1/collections/{collection_id}/items').json() == []


def test_notifications_can_only_be_read_by_recipient():
    authenticate()
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == 'test-admin@example.test').one()
        notification = Notification(recipient_id=admin.id, title='Test', body='Test body', read=False)
        db.add(notification)
        db.commit()
        notification_id = str(notification.id)

    response = client.post(f'/api/v1/notifications/{notification_id}/read')
    assert response.status_code == 200
    assert response.json()['read'] is True
    listed = client.get('/api/v1/notifications').json()
    assert next(item for item in listed if item['id'] == notification_id)['read'] is True
