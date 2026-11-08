import uuid, enum
from sqlalchemy import Boolean, Column, String, Integer, DateTime, ForeignKey, func, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from app.models.user import Base

class ProcessingStatus(str, enum.Enum):
    pending = 'pending'
    processing = 'processing'
    completed = 'completed'
    failed = 'failed'
    held = 'held'

class Document(Base):
    __tablename__ = 'documents'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uploader_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    title = Column(String, nullable=True)
    original_filename = Column(String(255), nullable=True)
    grade = Column(Integer, nullable=True)
    academic_year = Column(Integer, nullable=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey('subjects.id'), nullable=True, index=True)
    mime_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_object_key = Column(String, nullable=False)
    checksum = Column(String, nullable=False)
    no_answers_confirmed = Column(Boolean, nullable=False, default=False)
    security_status = Column(String(16), nullable=False, default='clean')
    security_scan_detail = Column(Text, nullable=True)
    security_scanned_at = Column(DateTime(timezone=True), nullable=True)
    security_reviewed_by = Column(UUID(as_uuid=True), nullable=True)
    security_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    security_review_note = Column(Text, nullable=True)
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.pending, nullable=False)
    page_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
