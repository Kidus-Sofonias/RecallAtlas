import uuid, enum
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from app.models.user import Base

class QualityStatus(str, enum.Enum):
    reliable='reliable'; held='held'

class Question(Base):
    __tablename__='questions'
    id=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id=Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=False)
    source_page_start=Column(Integer, nullable=True)
    source_page_end=Column(Integer, nullable=True)
    extracted_text=Column(Text, nullable=False)
    question_type=Column(String(32), nullable=False, default='unknown')
    content_json=Column(Text, nullable=True)
    quality_signals_json=Column(Text, nullable=True)
    extraction_version=Column(String(32), nullable=True)
    quality_status=Column(Enum(QualityStatus), default=QualityStatus.held, nullable=False)
    review_status=Column(String(16), nullable=False, default='pending')
    extraction_method=Column(String, nullable=True)
    embedding=Column(Text, nullable=True)  # JSON list of floats; pgvector vector in prod
    embedding_status=Column(String, default='pending', nullable=False)
    created_at=Column(DateTime(timezone=True), server_default=func.now())
