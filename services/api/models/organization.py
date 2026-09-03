import enum
import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class OrganizationType(str, enum.Enum):
    AMBULANCE = "AMBULANCE"
    FIRE = "FIRE"
    POLICE = "POLICE"
    SECURITY = "SECURITY"
    HOSPITAL = "HOSPITAL"
    NGO = "NGO"
    COUNTY_GOVERNMENT = "COUNTY_GOVERNMENT"
    NATIONAL_GOVERNMENT = "NATIONAL_GOVERNMENT"


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    type = Column(SQLEnum(OrganizationType), nullable=False)
    registration_number = Column(String(100), unique=True, nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(String(500), nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="organization")
    responders = relationship("Responder", back_populates="organization")
