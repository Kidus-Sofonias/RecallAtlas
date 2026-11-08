import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from app.models.user import Base

class DuplicateGroup(Base):
    __tablename__='duplicate_groups'
    id=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_document_id=Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=True)
    created_at=Column(DateTime(timezone=True), server_default=func.now())
