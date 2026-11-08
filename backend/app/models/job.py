import uuid, enum
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from app.models.user import Base

class JobStatus(str, enum.Enum):
    queued='queued'; running='running'; completed='completed'; failed='failed'; held='held'

class ProcessingJob(Base):
    __tablename__='processing_jobs'
    id=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id=Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=False)
    job_type=Column(String, default='extract', nullable=False)
    status=Column(Enum(JobStatus), default=JobStatus.queued, nullable=False)
    attempt_count=Column(Integer, default=0, nullable=False)
    error_category=Column(String, nullable=True)
    created_at=Column(DateTime(timezone=True), server_default=func.now())
    available_at=Column(DateTime(timezone=True), nullable=True, index=True)
    started_at=Column(DateTime(timezone=True), nullable=True)
    finished_at=Column(DateTime(timezone=True), nullable=True)
    lease_expires_at=Column(DateTime(timezone=True), nullable=True, index=True)
    worker_id=Column(String(128), nullable=True)

    __table_args__ = (
        Index('ix_processing_jobs_status_available', 'status', 'available_at'),
    )
