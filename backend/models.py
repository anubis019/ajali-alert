"""
SQLAlchemy models for Ajali Alert (scoped-down runnable version).
Uses a persistent relational database (default SQLite) rather than an in-memory store,
so incidents, responders, and status history survive across restarts.
"""
import os
import hashlib
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import create_engine, JSON
from geoalchemy2 import Geometry

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ajali:ajali@localhost:5432/ajali")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
LocationType = Geometry("POINT", srid=4326) if not DATABASE_URL.startswith("sqlite") else String()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def gen_id() -> str:
    return str(uuid.uuid4())


class IncidentType(Base):
    __tablename__ = "incident_types"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)
    icon = Column(String, default="Alert")
    default_priority = Column(Integer, default=3)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="CITIZEN")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class Responder(Base):
    __tablename__ = "responders"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    responder_type = Column(String, nullable=False)  # ambulance, police, fire, community
    status = Column(String, default="AVAILABLE")  # AVAILABLE, ASSIGNED, EN_ROUTE, OFFLINE
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    phone = Column(String, default="")
    location = Column(LocationType, nullable=True)
    last_location_at = Column(DateTime, nullable=True)


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, default=gen_id)
    incident_number = Column(String, unique=True, nullable=False)
    type_id = Column(String, ForeignKey("incident_types.id"))
    reporter_phone = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    status = Column(String, default="NEW")
    priority = Column(Integer, default=3)
    casualty_count = Column(Integer, default=0)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_description = Column(String, default="")
    landmark = Column(String, default="")
    is_escalated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    location = Column(LocationType, nullable=True)

    type = relationship("IncidentType")
    history = relationship(
        "IncidentStatusHistory", back_populates="incident",
        order_by="IncidentStatusHistory.created_at"
    )
    assignments = relationship("DispatchAssignment", back_populates="incident")
    notifications = relationship("Notification", back_populates="incident")


class IncidentStatusHistory(Base):
    __tablename__ = "incident_status_history"

    id = Column(String, primary_key=True, default=gen_id)
    incident_id = Column(String, ForeignKey("incidents.id"))
    status = Column(String, nullable=False)
    note = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="history")


class DispatchAssignment(Base):
    __tablename__ = "dispatch_assignments"

    id = Column(String, primary_key=True, default=gen_id)
    incident_id = Column(String, ForeignKey("incidents.id"))
    responder_id = Column(String, ForeignKey("responders.id"))
    status = Column(String, default="ASSIGNED")
    eta_minutes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="assignments")
    responder = relationship("Responder")


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location = Column(LocationType, nullable=True)
    status = Column(String, nullable=False, default="OPERATIONAL")
    emergency_available = Column(Boolean, nullable=False, default=True)
    available_beds = Column(Integer, nullable=False, default=0)
    trauma_capable = Column(Boolean, nullable=False, default=False)
    phone = Column(String, default="")
    updated_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=gen_id)
    incident_id = Column(String, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True)
    recipient = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    event = Column(String, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, default="PENDING")
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

    incident = relationship("Incident", back_populates="notifications")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_id)
    actor_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    result = Column(String, nullable=False, default="SUCCESS")
    details = Column(JSON, nullable=False, default=dict)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class USSDSession(Base):
    __tablename__ = "ussd_sessions"

    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String, unique=True, nullable=False, index=True)
    phone_number = Column(String, nullable=False)
    state = Column(String, nullable=False, default="MAIN_MENU")
    data = Column(JSON, nullable=False, default=dict)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
