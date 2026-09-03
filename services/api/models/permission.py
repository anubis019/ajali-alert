import uuid

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False)
    resource = Column(String(50), nullable=True)
    action = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")
