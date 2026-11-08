import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.models.user import Base


class Resource(Base):
    __tablename__ = 'resources'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey('subjects.id'), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    summary = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    resource_type = Column(String(32), nullable=False, default='article')
    status = Column(String(24), nullable=False, default='published')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
