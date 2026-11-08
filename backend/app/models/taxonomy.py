import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Table, func
from sqlalchemy.dialects.postgresql import UUID
from app.models.user import Base

user_subject_preferences = Table(
    'user_subject_preferences',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('subject_id', UUID(as_uuid=True), ForeignKey('subjects.id', ondelete='CASCADE'), primary_key=True),
)

class Subject(Base):
    __tablename__='subjects'
    id=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name=Column(String, unique=True, nullable=False)
    created_at=Column(DateTime(timezone=True), server_default=func.now())

class Topic(Base):
    __tablename__='topics'
    id=Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id=Column(UUID(as_uuid=True), ForeignKey('subjects.id'), nullable=True)
    name=Column(String, nullable=False)
    created_at=Column(DateTime(timezone=True), server_default=func.now())
