import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import UUID
from app.models.user import Base

class DocumentVersion(Base):
    __tablename__='document_versions'
    id=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id=Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=False)
    version_number=Column(Integer, nullable=False)
    checksum=Column(String, nullable=False)
    storage_object_key=Column(String, nullable=False)
    created_at=Column(DateTime(timezone=True), server_default=func.now())
