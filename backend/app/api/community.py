import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.comment import Comment
from app.models.document import Document, ProcessingStatus
from app.models.question import QualityStatus, Question
from app.models.report import Report
from app.models.resource import Resource
from app.models.user import User
from app.services.auth import require_admin, require_onboarding

router = APIRouter(tags=['community'])
CommentTarget = Literal['question', 'document', 'resource']
ReportTarget = Literal['question', 'document', 'resource', 'comment', 'user']


class CommentIn(BaseModel):
    target_type: CommentTarget
    target_id: uuid.UUID
    body: str = Field(min_length=1, max_length=2000)
    parent_comment_id: uuid.UUID | None = None


class ReportIn(BaseModel):
    target_type: ReportTarget
    target_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=64)
    details: str | None = Field(default=None, max_length=2000)


class ReportDecision(BaseModel):
    decision: Literal['dismiss', 'remove', 'restrict']
    notes: str | None = Field(default=None, max_length=2000)


def _target_exists(db: Session, target_type: str, target_id: uuid.UUID) -> bool:
    if target_type == 'question':
        return db.query(Question.id).filter(
            Question.id == target_id,
            Question.quality_status == QualityStatus.reliable,
        ).first() is not None
    if target_type == 'document':
        return db.query(Document.id).filter(
            Document.id == target_id,
            Document.processing_status == ProcessingStatus.completed,
            db.query(Question.id).filter(
                Question.document_id == Document.id,
                Question.quality_status == QualityStatus.reliable,
            ).exists(),
        ).first() is not None
    if target_type == 'resource':
        return db.query(Resource.id).filter(
            Resource.id == target_id,
            Resource.status == 'published',
        ).first() is not None
    if target_type == 'comment':
        return db.query(Comment.id).filter(
            Comment.id == target_id,
            Comment.moderation_status == 'published',
        ).first() is not None
    if target_type == 'user':
        return db.query(User.id).filter(User.id == target_id, User.status == 'active').first() is not None
    return False


@router.get('/api/v1/comments')
def list_comments(
    target_type: CommentTarget,
    target_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_onboarding),
):
    if not _target_exists(db, target_type, target_id):
        raise HTTPException(404, 'NOT_FOUND')
    comments = db.query(Comment, User).join(User, User.id == Comment.author_id).filter(
        Comment.target_type == target_type,
        Comment.target_id == target_id,
        Comment.moderation_status == 'published',
    ).order_by(Comment.created_at.asc()).limit(limit).all()
    return [{
        'id': str(comment.id),
        'author_id': str(author.id),
        'author_name': author.display_name or 'Recall Atlas user',
        'body': comment.body,
        'parent_comment_id': str(comment.parent_comment_id) if comment.parent_comment_id else None,
        'created_at': comment.created_at.isoformat() if comment.created_at else None,
    } for comment, author in comments]


@router.post('/api/v1/comments', status_code=201)
def add_comment(
    body: CommentIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_onboarding),
):
    clean_body = body.body.strip()
    if not clean_body:
        raise HTTPException(422, 'COMMENT_CANNOT_BE_BLANK')
    if not _target_exists(db, body.target_type, body.target_id):
        raise HTTPException(404, 'NOT_FOUND')
    if body.parent_comment_id:
        parent = db.query(Comment).filter(
            Comment.id == body.parent_comment_id,
            Comment.target_type == body.target_type,
            Comment.target_id == body.target_id,
        ).first()
        if not parent:
            raise HTTPException(404, 'PARENT_COMMENT_NOT_FOUND')
    comment = Comment(
        author_id=user.id,
        target_type=body.target_type,
        target_id=body.target_id,
        parent_comment_id=body.parent_comment_id,
        body=clean_body,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {'id': str(comment.id)}


@router.post('/api/v1/reports', status_code=201)
def add_report(
    body: ReportIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_onboarding),
):
    reason = body.reason.strip()
    if not reason:
        raise HTTPException(422, 'REPORT_REASON_REQUIRED')
    if not _target_exists(db, body.target_type, body.target_id):
        raise HTTPException(404, 'NOT_FOUND')
    report = Report(
        reporter_id=user.id,
        target_type=body.target_type,
        target_id=body.target_id,
        reason=reason,
        details=body.details.strip() if body.details and body.details.strip() else None,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {'id': str(report.id), 'status': report.status}


@router.get('/api/v1/admin/reports')
def list_reports(
    status: Literal['open', 'resolved', 'dismissed'] | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = db.query(Report).order_by(Report.created_at.asc())
    if status:
        query = query.filter(Report.status == status)
    return [{
        'id': str(report.id),
        'reporter_id': str(report.reporter_id),
        'target_type': report.target_type,
        'target_id': str(report.target_id),
        'reason': report.reason,
        'details': report.details,
        'status': report.status,
        'decision': report.decision,
        'review_notes': report.review_notes,
        'created_at': report.created_at.isoformat() if report.created_at else None,
    } for report in query.limit(limit).all()]


@router.post('/api/v1/admin/reports/{report_id}/decision')
def decide_report(
    report_id: str,
    body: ReportDecision,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        parsed_id = uuid.UUID(report_id)
    except ValueError as exc:
        raise HTTPException(400, 'VALIDATION_ERROR') from exc
    report = db.query(Report).filter(Report.id == parsed_id).first()
    if not report:
        raise HTTPException(404, 'NOT_FOUND')
    if report.status != 'open':
        raise HTTPException(409, 'REPORT_ALREADY_REVIEWED')
    report.decision = body.decision
    report.review_notes = body.notes.strip() if body.notes and body.notes.strip() else None
    report.reviewed_by = admin.id
    report.reviewed_at = datetime.now(timezone.utc)
    report.status = 'dismissed' if body.decision == 'dismiss' else 'resolved'
    if body.decision != 'dismiss':
        if report.target_type == 'question':
            target = db.query(Question).filter(Question.id == report.target_id).first()
            if target:
                target.quality_status = QualityStatus.held
        elif report.target_type == 'document':
            target = db.query(Document).filter(Document.id == report.target_id).first()
            if target:
                target.processing_status = ProcessingStatus.held
        elif report.target_type == 'resource':
            target = db.query(Resource).filter(Resource.id == report.target_id).first()
            if target:
                target.status = 'restricted' if body.decision == 'restrict' else 'removed'
        elif report.target_type == 'comment':
            target = db.query(Comment).filter(Comment.id == report.target_id).first()
            if target:
                target.moderation_status = 'restricted' if body.decision == 'restrict' else 'removed'
        elif report.target_type == 'user':
            target = db.query(User).filter(User.id == report.target_id).first()
            if target:
                target.status = 'suspended'
    db.commit()
    return {
        'id': str(report.id),
        'status': report.status,
        'decision': report.decision,
        'reviewed_at': report.reviewed_at.isoformat(),
    }
