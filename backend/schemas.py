from datetime import datetime
from typing import Literal, Optional, List
from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    type_code: str
    description: str = Field(min_length=5)
    casualty_count: int = Field(default=0, ge=0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    location_description: str = ""
    landmark: str = ""
    reporter_phone: Optional[str] = None


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=12)
    role: Literal["CITIZEN"] = "CITIZEN"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class UserRoleUpdate(BaseModel):
    role: str
    is_active: bool | None = None


class DispatchRequest(BaseModel):
    responder_id: str
    assignment_type: Literal["PRIMARY", "BACKUP", "SUPPORT"] = "PRIMARY"
    note: str = ""


class StatusUpdate(BaseModel):
    status: Literal[
        "NEW",
        "DISPATCHING",
        "ESCALATED",
        "EN_ROUTE",
        "ARRIVED",
        "RESOLVED",
        "CLOSED",
        "CANCELLED",
        "FALSE_ALERT",
    ]
    note: Optional[str] = ""


class ResponderOut(BaseModel):
    id: str
    name: str
    responder_type: str
    status: str
    latitude: float
    longitude: float
    phone: str

    class Config:
        from_attributes = True


class AssignmentOut(BaseModel):
    id: str
    status: str
    eta_minutes: int
    responder: ResponderOut

    class Config:
        from_attributes = True


class HistoryOut(BaseModel):
    status: str
    note: str
    created_at: datetime

    class Config:
        from_attributes = True


class FirstAidTopicOut(BaseModel):
    id: str
    title: str
    steps: List[str]
    warnings: List[str] = []


class FirstAidQuery(BaseModel):
    query: str = Field(min_length=2)
    incident_id: Optional[str] = None
    type_code: Optional[str] = None


class AIChatRequest(BaseModel):
    message: str = Field(min_length=1)
    incident_id: Optional[str] = None
    user_role: str = "dispatcher"


class AIChatResponse(BaseModel):
    reply: str
    incident_id: Optional[str] = None
    user_role: str = "dispatcher"


class IncidentTypeOut(BaseModel):
    code: str
    name: str
    icon: str

    class Config:
        from_attributes = True


class IncidentOut(BaseModel):
    id: str
    incident_number: str
    status: str
    priority: int
    casualty_count: int
    description: str
    latitude: float
    longitude: float
    location_description: str
    landmark: str
    is_escalated: bool
    created_at: datetime
    updated_at: datetime
    type: Optional[IncidentTypeOut] = None
    history: List[HistoryOut] = []
    assignments: List[AssignmentOut] = []
    first_aid_suggestions: List[FirstAidTopicOut] = []

    class Config:
        from_attributes = True
