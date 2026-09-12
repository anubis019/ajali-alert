from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models import (
    EmergencyCategoryEnum, EmergencySubTypeEnum, ResponderTypeEnum,
    SeverityEnum, StatusEnum, RegionEnum, CallerChannelEnum, RoleEnum,
    EventKindEnum, NotifyChannelEnum, NotifyStatusEnum,
)


# ── Auth ──────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[RoleEnum] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# ── User ──────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., pattern=r"^[\w.-]+@[\w.-]+\.\w+$")
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: RoleEnum = RoleEnum.viewer
    team: Optional[str] = None
    responder_type: Optional[ResponderTypeEnum] = None
    badge_number: Optional[str] = None
    county: Optional[str] = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    role: RoleEnum
    is_active: bool
    team: Optional[str]
    responder_type: Optional[ResponderTypeEnum]
    badge_number: Optional[str]
    on_duty: bool
    county: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[RoleEnum] = None
    team: Optional[str] = None
    responder_type: Optional[ResponderTypeEnum] = None
    badge_number: Optional[str] = None
    on_duty: Optional[bool] = None
    county: Optional[str] = None
    is_active: Optional[bool] = None


# ── Alert ─────────────────────────────────────────────
class AlertCreate(BaseModel):
    """Schema for creating a new emergency alert."""
    title: str = Field(..., min_length=1, max_length=256)
    description: str = Field(..., min_length=1)
    severity: SeverityEnum
    category: EmergencyCategoryEnum
    sub_type: Optional[EmergencySubTypeEnum] = None
    region: RegionEnum = RegionEnum.nairobi

    # Location
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    county: Optional[str] = None

    # Caller info
    caller_phone: Optional[str] = None
    caller_name: Optional[str] = None
    caller_channel: CallerChannelEnum = CallerChannelEnum.app

    # Scene telemetry
    casualty_count: int = 0
    entrapped: bool = False
    fire_severity: Optional[str] = None
    hazard_present: bool = False

    # Responder
    responder_type: Optional[ResponderTypeEnum] = None
    eta_minutes: Optional[float] = None

    source: Optional[str] = None
    source_id: Optional[str] = None
    team: Optional[str] = None


class AlertUpdate(BaseModel):
    """Schema for updating an existing alert."""
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[SeverityEnum] = None
    status: Optional[StatusEnum] = None
    category: Optional[EmergencyCategoryEnum] = None
    sub_type: Optional[EmergencySubTypeEnum] = None
    region: Optional[RegionEnum] = None

    # Location
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    county: Optional[str] = None

    # Caller
    caller_phone: Optional[str] = None
    caller_name: Optional[str] = None

    # Scene telemetry
    casualty_count: Optional[int] = None
    entrapped: Optional[bool] = None
    fire_severity: Optional[str] = None
    hazard_present: Optional[bool] = None

    # Responder
    responder_type: Optional[ResponderTypeEnum] = None
    eta_minutes: Optional[float] = None
    assigned_to: Optional[int] = None
    team: Optional[str] = None


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    severity: SeverityEnum
    status: StatusEnum
    category: EmergencyCategoryEnum
    sub_type: Optional[EmergencySubTypeEnum]
    region: RegionEnum

    # Location
    location: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    county: Optional[str]

    # Caller
    caller_phone: Optional[str]
    caller_name: Optional[str]
    caller_channel: Optional[CallerChannelEnum]

    # Scene telemetry
    casualty_count: int
    entrapped: bool
    fire_severity: Optional[str]
    hazard_present: bool

    # Responder
    responder_type: Optional[ResponderTypeEnum]
    eta_minutes: Optional[float]
    dispatched_at: Optional[datetime]
    arrived_at: Optional[datetime]

    source: Optional[str]
    source_id: Optional[str]
    created_by: Optional[int]
    assigned_to: Optional[int]
    team: Optional[str]
    created_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    updated_at: Optional[datetime]
    response_time_seconds: Optional[float]
    dispatch_time_seconds: Optional[float]
    resolution_time_seconds: Optional[float]


class AlertListResponse(BaseModel):
    items: List[AlertRead]
    total: int
    page: int
    page_size: int


# ── AlertEvent ───────────────────────────────────────
class AlertEventCreate(BaseModel):
    kind: EventKindEnum
    message: Optional[str] = None


class AlertEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    alert_id: int
    kind: EventKindEnum
    message: Optional[str]
    performed_by: Optional[int]
    created_at: datetime


# ── Notification ──────────────────────────────────────
class NotificationCreate(BaseModel):
    alert_id: int
    channel: NotifyChannelEnum
    recipient: str
    message: str


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    alert_id: int
    channel: NotifyChannelEnum
    recipient: str
    message: str
    status: NotifyStatusEnum
    sent_at: Optional[datetime]
    error: Optional[str]


# ── EscalationPolicy ─────────────────────────────────
class EscalationPolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    category: Optional[EmergencyCategoryEnum] = None
    severity: SeverityEnum
    delay_minutes: int = Field(..., ge=1)
    notify_channel: NotifyChannelEnum = NotifyChannelEnum.sms
    notify_recipient: Optional[str] = None
    responder_type: Optional[ResponderTypeEnum] = None
    auto_escalate: bool = True
    repeat_interval_minutes: int = Field(0, ge=0)


class EscalationPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    category: Optional[EmergencyCategoryEnum]
    severity: SeverityEnum
    delay_minutes: int
    notify_channel: NotifyChannelEnum
    notify_recipient: Optional[str]
    responder_type: Optional[ResponderTypeEnum]
    auto_escalate: bool
    repeat_interval_minutes: int
    is_active: bool
    created_at: datetime


class EscalationPolicyUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[EmergencyCategoryEnum] = None
    delay_minutes: Optional[int] = None
    notify_channel: Optional[NotifyChannelEnum] = None
    notify_recipient: Optional[str] = None
    responder_type: Optional[ResponderTypeEnum] = None
    auto_escalate: Optional[bool] = None
    repeat_interval_minutes: Optional[int] = None
    is_active: Optional[bool] = None


# ── Team ──────────────────────────────────────────────
class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    responder_type: Optional[ResponderTypeEnum] = None
    county: Optional[str] = None
    on_call_count: int = 0
    active_incidents: int = 0
    avg_response_minutes: float = 0.0
    resolution_rate: float = 0.0
    escalation_rate: float = 0.0
    capacity_pct: float = 0.0


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    responder_type: Optional[ResponderTypeEnum]
    county: Optional[str]
    on_call_count: int
    active_incidents: int
    avg_response_minutes: float
    resolution_rate: float
    escalation_rate: float
    capacity_pct: float
    updated_at: Optional[datetime]


class TeamUpdate(BaseModel):
    responder_type: Optional[ResponderTypeEnum] = None
    county: Optional[str] = None
    on_call_count: Optional[int] = None
    active_incidents: Optional[int] = None
    avg_response_minutes: Optional[float] = None
    resolution_rate: Optional[float] = None
    escalation_rate: Optional[float] = None
    capacity_pct: Optional[float] = None


class TeamPerformance(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    responder_type: Optional[ResponderTypeEnum]
    county: Optional[str]
    on_call_count: int
    active_incidents: int
    avg_response_minutes: float
    resolution_rate: float
    escalation_rate: float
    capacity_pct: float
    updated_at: Optional[datetime]


# ── Dashboard Stats ───────────────────────────────────
class DashboardStats(BaseModel):
    active_alerts: int
    critical_events: int
    avg_response_minutes: float
    resolution_rate: float
    active_trend_24h: List[dict]  # [{"hour": "00:00", "critical": 1, ...}]
    severity_distribution: dict  # {"critical": 8, "high": 14, ...}
    category_distribution: dict  # {"accident": 12, "fire": 5, "medical": 8, "security": 3}
    region_distribution: dict   # {"nairobi": 19, ...}
    response_by_severity: dict  # {"critical": 2.1, ...}
    team_performance: List[dict]
    casualties_total: int = 0
    alerts_by_responder_type: dict = {}  # {"police": 5, "ambulance": 8, ...}
