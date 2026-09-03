import enum
import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class IncidentType(Base):
    __tablename__ = "incident_types"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(30), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    default_priority = Column(Integer, default=3)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    incidents = relationship("Incident", back_populates="type")


class IncidentStatus(str, enum.Enum):
    REPORTED = "REPORTED"
    RECEIVED = "RECEIVED"
    VERIFIED = "VERIFIED"
    DISPATCHING = "DISPATCHING"
    ASSIGNED = "ASSIGNED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


class IncidentSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (CheckConstraint("casualties >= 0", name="casualties_non_negative"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_number = Column(String(25), unique=True, nullable=False, index=True)
    type_id = Column(String, ForeignKey("incident_types.id"), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(SQLEnum(IncidentSeverity), default=IncidentSeverity.MEDIUM)
    status = Column(SQLEnum(IncidentStatus), default=IncidentStatus.REPORTED, nullable=False)
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    address = Column(String(255), nullable=True)
    landmark = Column(String(255), nullable=True)
    reporter_id = Column(String, ForeignKey("users.id"), nullable=True)
    reporter_phone = Column(String(20), nullable=True)
    casualties = Column(Integer, default=0)
    priority = Column(Integer, default=3)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

    type = relationship("IncidentType", back_populates="incidents")
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="incidents_created")
    status_history = relationship("IncidentStatusHistory", back_populates="incident", cascade="all, delete-orphan")
    media = relationship("IncidentMedia", back_populates="incident", cascade="all, delete-orphan")
    assignments = relationship("DispatchAssignment", back_populates="incident", cascade="all, delete-orphan")


class IncidentStatusHistory(Base):
    __tablename__ = "incident_status_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    old_status = Column(SQLEnum(IncidentStatus), nullable=True)
    new_status = Column(SQLEnum(IncidentStatus), nullable=False)
    changed_by = Column(String, ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    incident = relationship("Incident", back_populates="status_history")
    changer = relationship("User")


class IncidentMedia(Base):
    __tablename__ = "incident_media"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    incident = relationship("Incident", back_populates="media")
    uploader = relationship("User")
