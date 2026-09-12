import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum, Float, ForeignKey, Boolean, Index
)
from sqlalchemy.orm import relationship
from app.database import Base


# ── Emergency Categories ───────────────────────────────

class EmergencyCategoryEnum(str, enum.Enum):
    """The four core emergency types Ajali responds to."""
    accident = "accident"          # Road traffic accidents (Ajali)
    fire = "fire"                  # Fire emergencies & hazards
    medical = "medical"            # Health / medical emergencies
    security = "security"          # Security threats & crime


class EmergencySubTypeEnum(str, enum.Enum):
    """Sub-categories for each emergency type."""
    # Accident sub-types
    road_collision = "road_collision"
    vehicle_entrapment = "vehicle_entrapment"
    motorcycle_crash = "motorcycle_crash"
    pedestrian_hit = "pedestrian_hit"
    bus_accident = "bus_accident"
    multi_vehicle = "multi_vehicle"
    # Fire sub-types
    structural_fire = "structural_fire"
    vehicle_fire = "vehicle_fire"
    wildfire = "wildfire"
    gas_explosion = "gas_explosion"
    chemical_spill = "chemical_spill"
    electrical_fire = "electrical_fire"
    # Medical sub-types
    cardiac = "cardiac"
    maternity = "maternity"
    drowning = "drowning"
    poisoning = "poisoning"
    trauma = "trauma"
    epidemic = "epidemic"
    # Security sub-types
    robbery = "robbery"
    assault = "assault"
    home_invasion = "home_invasion"
    active_shooter = "active_shooter"
    kidnapping = "kidnapping"
    civil_unrest = "civil_unrest"


class ResponderTypeEnum(str, enum.Enum):
    """Types of emergency responders dispatched."""
    police = "police"
    ambulance = "ambulance"
    fire_brigade = "fire_brigade"
    community_responder = "community_responder"  # Boda Boda / Red Cross volunteers
    all = "all"  # Dispatch all available


class SeverityEnum(str, enum.Enum):
    critical = "critical"      # Life-threatening, Golden Hour critical
    high = "high"            # Serious but not immediately life-threatening
    medium = "medium"        # Moderate — requires response within 30 min
    low = "low"              # Minor — non-urgent


class StatusEnum(str, enum.Enum):
    active = "active"                  # Just reported — awaiting dispatch
    acknowledged = "acknowledged"      # Dispatcher confirmed receipt
    dispatching = "dispatching"        # Responders being assigned
    en_route = "en_route"              # Responder(s) on the way
    on_scene = "on_scene"              # Responder(s) arrived at scene
    investigating = "investigating"    # On-scene assessment underway
    resolved = "resolved"              # Incident closed
    escalated = "escalated"            # No response — escalated to county/backup
    suppressed = "suppressed"          # False alarm or duplicate


class RegionEnum(str, enum.Enum):
    """Kenya counties / regions covered by Ajali."""
    nairobi = "nairobi"
    mombasa = "mombasa"
    kisumu = "kisumu"
    nakuru = "nakuru"
    eldoret = "eldoret"
    garissa = "garissa"
    meru = "meru"
    kakamega = "kakamega"
    machakos = "machakos"
    nakuru_county = "nakuru_county"


class CallerChannelEnum(str, enum.Enum):
    """How the alert was initiated."""
    ussd = "ussd"            # USSD *1233# from feature phone
    app = "app"              # Smartphone app with GPS
    web = "web"              # Web portal
    sms = "sms"              # SMS to short code
    phone = "phone"          # Voice call to dispatch
    api = "api"              # Third-party API integration


class RoleEnum(str, enum.Enum):
    admin = "admin"
    dispatcher = "dispatcher"      # Central dispatcher
    responder = "responder"        # Field responder
    viewer = "viewer"              # Read-only


# ── User ──────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(256), unique=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    full_name = Column(String(128))
    phone = Column(String(20))                      # Responder phone for SMS/call
    role = Column(Enum(RoleEnum), default=RoleEnum.viewer, nullable=False)
    is_active = Column(Boolean, default=True)
    team = Column(String(64))
    responder_type = Column(Enum(ResponderTypeEnum), nullable=True)  # police/ambulance/fire/community
    badge_number = Column(String(32), nullable=True)  # Official ID number
    on_duty = Column(Boolean, default=False)        # Currently on shift
    county = Column(String(64), nullable=True)      # Assigned county
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)

    alerts_created = relationship("Alert", back_populates="creator", foreign_keys="Alert.created_by")
    alerts_assigned = relationship("Alert", back_populates="assignee", foreign_keys="Alert.assigned_to")


# ── Alert ─────────────────────────────────────────────
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Enum(SeverityEnum), nullable=False, index=True)
    status = Column(Enum(StatusEnum), default=StatusEnum.active, nullable=False, index=True)
    category = Column(Enum(EmergencyCategoryEnum), nullable=False, index=True)
    sub_type = Column(Enum(EmergencySubTypeEnum), nullable=True)   # Specific emergency sub-type
    region = Column(Enum(RegionEnum), default=RegionEnum.nairobi)

    # ── Emergency Location ─────────────────────────────
    location = Column(String(512), nullable=True)            # Human-readable address / landmark
    latitude = Column(Float, nullable=True)                    # GPS latitude
    longitude = Column(Float, nullable=True)                   # GPS longitude
    county = Column(String(64), nullable=True)                # County name

    # ── Caller Information ──────────────────────────────
    caller_phone = Column(String(20), nullable=True)           # Caller's phone number
    caller_name = Column(String(128), nullable=True)          # Caller's name (if provided)
    caller_channel = Column(Enum(CallerChannelEnum), default=CallerChannelEnum.app)

    # ── Casualty & Scene Telemetry ──────────────────────
    casualty_count = Column(Integer, default=0)                # Number of casualties reported
    entrapped = Column(Boolean, default=False)                  # Vehicle/person entrapment
    fire_severity = Column(String(20), nullable=True)         # small / medium / large / chemical
    hazard_present = Column(Boolean, default=False)           # Hazmat / chemical / gas leak

    # ── Responder Dispatch ──────────────────────────────
    responder_type = Column(Enum(ResponderTypeEnum), nullable=True)  # Which service dispatched
    eta_minutes = Column(Float, nullable=True)                       # Estimated arrival time
    dispatched_at = Column(DateTime, nullable=True)                  # When responders were dispatched
    arrived_at = Column(DateTime, nullable=True)                     # When responders arrived on scene

    # ── Source / Dedup ──────────────────────────────────
    source = Column(String(128))            # system that generated the alert (USSD, App, API)
    source_id = Column(String(128))         # dedup key from the source system

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    team = Column(String(64))

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # ── Performance Metrics ────────────────────────────
    response_time_seconds = Column(Float, nullable=True)      # time to first ack
    dispatch_time_seconds = Column(Float, nullable=True)      # time from creation to dispatch
    resolution_time_seconds = Column(Float, nullable=True)    # total time to resolve

    creator = relationship("User", back_populates="alerts_created", foreign_keys=[created_by])
    assignee = relationship("User", back_populates="alerts_assigned", foreign_keys=[assigned_to])
    events = relationship("AlertEvent", back_populates="alert", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="alert", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_alerts_source_id", "source", "source_id", unique=True),
        Index("ix_alerts_severity_status", "severity", "status"),
        Index("ix_alerts_category_severity", "category", "severity"),
    )


# ── AlertEvent (audit trail) ──────────────────────────
class EventKindEnum(str, enum.Enum):
    created = "created"
    acknowledged = "acknowledged"
    dispatching = "dispatching"
    en_route = "en_route"
    on_scene = "on_scene"
    escalated = "escalated"
    resolved = "resolved"
    suppressed = "suppressed"
    comment = "comment"
    reassigned = "reassigned"
    severity_changed = "severity_changed"
    casualty_update = "casualty_update"
    eta_update = "eta_update"


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False, index=True)
    kind = Column(Enum(EventKindEnum), nullable=False)
    message = Column(Text)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    alert = relationship("Alert", back_populates="events")


# ── Notification ──────────────────────────────────────
class NotifyChannelEnum(str, enum.Enum):
    email = "email"
    sms = "sms"                    # Primary channel for Kenya
    ussd = "ussd"                  # USSD callback
    webhook = "webhook"
    slack = "slack"
    pagerduty = "pagerduty"


class NotifyStatusEnum(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False, index=True)
    channel = Column(Enum(NotifyChannelEnum), nullable=False)
    recipient = Column(String(256), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(Enum(NotifyStatusEnum), default=NotifyStatusEnum.pending)
    sent_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)

    alert = relationship("Alert", back_populates="notifications")


# ── EscalationPolicy ─────────────────────────────────
class EscalationPolicy(Base):
    __tablename__ = "escalation_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    category = Column(Enum(EmergencyCategoryEnum), nullable=True)  # Which emergency type this applies to
    severity = Column(Enum(SeverityEnum), nullable=False)
    delay_minutes = Column(Integer, nullable=False)  # minutes before escalating
    notify_channel = Column(Enum(NotifyChannelEnum), default=NotifyChannelEnum.sms)
    notify_recipient = Column(String(256))  # team or individual
    responder_type = Column(Enum(ResponderTypeEnum), nullable=True)  # Which responder to escalate to
    auto_escalate = Column(Boolean, default=True)
    repeat_interval_minutes = Column(Integer, default=0)  # 0 = no repeat
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Team ──────────────────────────────────────────────
class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False)
    responder_type = Column(Enum(ResponderTypeEnum), nullable=True)  # Police / Ambulance / Fire / Community
    county = Column(String(64), nullable=True)                      # Which county this team covers
    on_call_count = Column(Integer, default=0)
    active_incidents = Column(Integer, default=0)
    avg_response_minutes = Column(Float, default=0.0)
    resolution_rate = Column(Float, default=0.0)
    escalation_rate = Column(Float, default=0.0)
    capacity_pct = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
