import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from app.models.user import Base

class Bookmark(Base):
    __tablename__='bookmarks'
    id=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id=Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    target_type=Column(String, nullable=False)
    target_id=Column(UUID(as_uuid=True), nullable=False)
    created_at=Column(DateTime(timezone=True), server_default=func.now())
