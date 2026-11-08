import uuid
from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import engine
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth_subject = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=True)
    password_hash = Column(String(256), nullable=True)
    display_name = Column(String, nullable=True)
    status = Column(String, default='active', nullable=False)
    role = Column(String, default='user', nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    preferred_grade = Column(Integer, nullable=True)
    school = Column(String, nullable=True)
    deletion_requested_at = Column(DateTime(timezone=True), nullable=True)
    deletion_request_status = Column(String(16), nullable=False, default='none')
    deletion_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    deletion_reviewed_by = Column(UUID(as_uuid=True), nullable=True)
    deletion_review_note = Column(Text, nullable=True)
    preferred_subjects = relationship('Subject', secondary='user_subject_preferences')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
