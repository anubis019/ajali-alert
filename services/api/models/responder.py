import enum
import uuid

from geoalchemy2 import Geometry
from sqlalchemy import ARRAY, Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class ResponderType(str, enum.Enum):
    AMBULANCE = "AMBULANCE"
    PARAMEDIC = "PARAMEDIC"
    FIRE_UNIT = "FIRE_UNIT"
    POLICE_UNIT = "POLICE_UNIT"
    SECURITY_UNIT = "SECURITY_UNIT"
    RESCUE_TEAM = "RESCUE_TEAM"
    MEDICAL_TEAM = "MEDICAL_TEAM"
    OTHER = "OTHER"


class ResponderStatus(str, enum.Enum):
    OFFLINE = "OFFLINE"
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    BUSY = "BUSY"
    UNAVAILABLE = "UNAVAILABLE"


class Responder(Base):
    __tablename__ = "responders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    identifier = Column(String(30), unique=True, nullable=False)
    responder_type = Column(SQLEnum(ResponderType), nullable=False)
    status = Column(SQLEnum(ResponderStatus), default=ResponderStatus.OFFLINE, nullable=False)
    current_location = Column(Geometry("POINT", srid=4326), nullable=True)
    availability = Column(Boolean, default=False)
    vehicle_id = Column(String(50), nullable=True)
    capabilities = Column(ARRAY(String), default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="responder")
    organization = relationship("Organization", back_populates="responders")
    assignments = relationship("DispatchAssignment", back_populates="responder")
    status_history = relationship("ResponderStatusHistory", back_populates="responder")


class ResponderStatusHistory(Base):
    __tablename__ = "responder_status_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    responder_id = Column(String, ForeignKey("responders.id", ondelete="CASCADE"), nullable=False)
    old_status = Column(SQLEnum(ResponderStatus), nullable=True)
    new_status = Column(SQLEnum(ResponderStatus), nullable=False)
    changed_by = Column(String, ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    responder = relationship("Responder", back_populates="status_history")
    changer = relationship("User")
