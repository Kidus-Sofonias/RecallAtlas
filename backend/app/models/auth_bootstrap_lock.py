from sqlalchemy import Column, Integer

from .user import Base


class AuthBootstrapLock(Base):
    __tablename__ = 'auth_bootstrap_lock'

    id = Column(Integer, primary_key=True)
