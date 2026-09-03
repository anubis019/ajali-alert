import enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class AssignmentType(str, enum.Enum):
    PRIMARY = "PRIMARY"
    BACKUP = "BACKUP"
    SUPPORT = "SUPPORT"


class AssignmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    REJECTED = "REJECTED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    COMPLETED = "COMPLETED"


class DispatchAssignment(Base):
    __tablename__ = "dispatch_assignments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    responder_id = Column(String, ForeignKey("responders.id"), nullable=False)
    assigned_by = Column(String, ForeignKey("users.id"), nullable=False)
    assignment_type = Column(SQLEnum(AssignmentType), default=AssignmentType.PRIMARY)
    status = Column(SQLEnum(AssignmentStatus), default=AssignmentStatus.PENDING, nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    en_route_at = Column(DateTime(timezone=True), nullable=True)
    arrived_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    incident = relationship("Incident", back_populates="assignments")
    responder = relationship("Responder", back_populates="assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])
