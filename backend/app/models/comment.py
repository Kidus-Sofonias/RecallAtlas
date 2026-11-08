import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from app.models.user import Base

class Comment(Base):
    __tablename__='comments'
    id=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id=Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    target_type=Column(String, nullable=False)
    target_id=Column(UUID(as_uuid=True), nullable=False)
    parent_comment_id=Column(UUID(as_uuid=True), ForeignKey('comments.id'), nullable=True)
    body=Column(Text, nullable=False)
    moderation_status=Column(String(16), nullable=False, default='published')
    created_at=Column(DateTime(timezone=True), server_default=func.now())
