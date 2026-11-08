import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, func, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.models.user import Base

class Notification(Base):
    __tablename__='notifications'
    id=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_id=Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    title=Column(String, nullable=False)
    body=Column(Text, nullable=True)
    read=Column(Boolean, default=False)
    created_at=Column(DateTime(timezone=True), server_default=func.now())
