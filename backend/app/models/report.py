import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from app.models.user import Base

class Report(Base):
    __tablename__='reports'
    id=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id=Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    target_type=Column(String, nullable=False)
    target_id=Column(UUID(as_uuid=True), nullable=False)
    reason=Column(String, nullable=False)
    details=Column(Text, nullable=True)
    status=Column(String, default='open', nullable=False)
    decision=Column(String, nullable=True)
    reviewed_by=Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    reviewed_at=Column(DateTime(timezone=True), nullable=True)
    review_notes=Column(Text, nullable=True)
    created_at=Column(DateTime(timezone=True), server_default=func.now())
