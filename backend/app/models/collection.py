import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.models.user import Base

class Collection(Base):
    __tablename__='collections'
    id=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id=Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    name=Column(String, nullable=False)
    created_at=Column(DateTime(timezone=True), server_default=func.now())

class CollectionItem(Base):
    __tablename__='collection_items'
    id=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id=Column(UUID(as_uuid=True), ForeignKey('collections.id'), nullable=False)
    question_id=Column(UUID(as_uuid=True), nullable=False)
    position=Column(Integer, default=0)
    created_at=Column(DateTime(timezone=True), server_default=func.now())
