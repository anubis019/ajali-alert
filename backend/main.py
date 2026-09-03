"""
Ajali Alert - scoped-down runnable backend.

Covers: incident reporting, simple nearest-responder dispatch, escalation
when nobody is available, status history/timeline, and a websocket feed
for live updates. Runs on SQLite with zero external services (no Postgres,
no Redis) so it's a `pip install -r requirements.txt && uvicorn main:app`
away from working.
"""
import json
import logging
import math
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from models import (
    SessionLocal, Incident, IncidentType, IncidentStatusHistory,
    Responder, DispatchAssignment,
    RefreshSession, User,
)
from schemas import (
    IncidentCreate, IncidentOut, StatusUpdate, IncidentTypeOut, ResponderOut,
    FirstAidQuery, FirstAidTopicOut, AIChatRequest, AIChatResponse,
    RegisterRequest, LoginRequest, RefreshRequest, TokenResponse, UserRoleUpdate, DispatchRequest,
)
from seed import seed
from first_aid import match_topics
from ai_service import get_ai_provider
from services import HospitalService, NotificationService, USSDService, audit
from auth import (
    ACCESS_MINUTES, OPERATIONAL_ROLES, REFRESH_DAYS, current_user, get_db as get_auth_db,
    create_refresh_token, hash_password, issue_token, require_roles, rotate_refresh_token, verify_password,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ajali")

app = FastAPI(title="Ajali Alert API", version="1.0.0")

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    return response

MAX_RESPONDER_RADIUS_KM = 25
REQUIRED_RESPONDER_TYPES = {
    "road_accident": ["ambulance", "police"],
    "medical": ["ambulance"],
    "fire": ["fire"],
    "security": ["police"],
    "other": ["community", "police", "ambulance", "fire"],
}
VALID_TRANSITIONS = {
    "NEW": {"DISPATCHING", "ESCALATED", "CANCELLED"},
    "DISPATCHING": {"EN_ROUTE", "ESCALATED", "CANCELLED"},
    "ESCALATED": {"DISPATCHING", "CANCELLED"},
    "EN_ROUTE": {"ARRIVED", "CANCELLED"},
    "ARRIVED": {"RESOLVED"},
    "RESOLVED": {"CLOSED"},
    "CLOSED": set(),
    "CANCELLED": set(),
    "FALSE_ALERT": set(),
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    seed()
    logger.info("Ajali Alert API ready.")


# ---------------------------------------------------------------------------
# Websocket connection manager (in-process broadcast; Redis pub/sub not needed
# at this scale since there's a single API process).
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, event: str, data: dict):
        payload = json.dumps({"event": event, "data": data, "ts": datetime.utcnow().isoformat()})
        try:
            import redis
            redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0")).publish("ajali.events", payload)
        except Exception:
            pass
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # client pings; we don't need the content
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/v1/hospitals")
def list_hospitals(db: Session = Depends(get_db), _: User = Depends(current_user)):
    from models import Hospital
    return db.query(Hospital).order_by(Hospital.name).all()


@app.get("/api/v1/hospitals/recommendations")
def hospital_recommendations(latitude: float, longitude: float, trauma: bool = False,
                             db: Session = Depends(get_db), _: User = Depends(require_roles("ADMIN", "DISPATCHER", "SUPERVISOR", "RESPONDER"))):
    hospitals = HospitalService(db).recommend(latitude, longitude, trauma=trauma)
    return [{"id": h.id, "name": h.name, "latitude": h.latitude, "longitude": h.longitude,
             "available_beds": h.available_beds, "trauma_capable": h.trauma_capable, "status": h.status} for h in hospitals]


@app.post("/api/v1/notifications/process")
def process_notifications(db: Session = Depends(get_db), _: User = Depends(require_roles("ADMIN", "SUPERVISOR"))):
    return {"processed": NotificationService(db).process_pending()}


@app.get("/api/v1/audit-logs")
def list_audit_logs(db: Session = Depends(get_db), _: User = Depends(require_roles("ADMIN", "SUPERVISOR"))):
    from models import AuditLog
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()


@app.post("/api/v1/ussd/webhook")
def ussd_webhook(payload: dict, db: Session = Depends(get_db)):
    expected = os.getenv("USSD_WEBHOOK_SECRET")
    if expected and payload.get("secret") != expected:
        raise HTTPException(status_code=401, detail="Invalid USSD webhook credentials")
    return {"response": USSDService(db).handle(payload.get("session_id", ""), payload.get("phone_number", ""), payload.get("text", ""))}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def add_history(db: Session, incident: Incident, status: str, note: str = ""):
    db.add(IncidentStatusHistory(incident_id=incident.id, status=status, note=note))
    incident.status = status
    incident.updated_at = datetime.utcnow()


def to_incident_out(db: Session, incident: Incident) -> IncidentOut:
    """Build the API response, attaching locally-matched first-aid guidance
    on the way out. This runs the keyword matcher fresh each time (cheap,
    deterministic) rather than storing suggestions in the DB, so it always
    reflects the current KB content."""
    type_code = incident.type.code if incident.type else None
    topics = match_topics(incident.description, type_code=type_code, limit=2)
    out = IncidentOut.model_validate(incident)
    out.first_aid_suggestions = [FirstAidTopicOut(**t) for t in topics]
    return out


def dispatch_nearest_responder(db: Session, incident: Incident, type_code: str) -> Optional[DispatchAssignment]:
    """Simplified stand-in for the full scoring/escalation-timer pipeline:
    just finds the closest AVAILABLE responder of a suitable type within
    MAX_RESPONDER_RADIUS_KM."""
    wanted_types = REQUIRED_RESPONDER_TYPES.get(type_code, ["community"])
    candidates = (
        db.query(Responder)
        .filter(Responder.status == "AVAILABLE", Responder.responder_type.in_(wanted_types))
        .all()
    )
    best, best_dist = None, None
    for r in candidates:
        d = haversine_km(incident.latitude, incident.longitude, r.latitude, r.longitude)
        if d <= MAX_RESPONDER_RADIUS_KM and (best is None or d < best_dist):
            best, best_dist = r, d

    if not best:
        return None

    eta = max(1, round(best_dist / 40 * 60))  # assume ~40km/h average
    assignment = DispatchAssignment(
        incident_id=incident.id, responder_id=best.id, status="ASSIGNED", eta_minutes=eta
    )
    best.status = "ASSIGNED"
    db.add(assignment)
    db.add(best)
    return assignment


def responder_candidates(db: Session, incident: Incident, type_code: str):
    wanted_types = REQUIRED_RESPONDER_TYPES.get(type_code, ["community"])
    rows = []
    for responder in db.query(Responder).filter(Responder.status == "AVAILABLE", Responder.responder_type.in_(wanted_types)).all():
        distance = haversine_km(incident.latitude, incident.longitude, responder.latitude, responder.longitude)
        if distance <= MAX_RESPONDER_RADIUS_KM:
            rows.append({"responder": responder, "distance_km": round(distance, 2), "eta_minutes": max(1, round(distance / 40 * 60))})
    return sorted(rows, key=lambda row: row["distance_km"])


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/live")
def live():
    return {"status": "alive"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Database readiness check failed")
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
    dependencies = {"database": "ready"}
    try:
        import redis
        redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0")).ping()
        dependencies["redis"] = "ready"
    except Exception:
        dependencies["redis"] = "unavailable"
    return {"status": "ready" if dependencies["redis"] == "ready" else "degraded", "dependencies": dependencies}


@app.get("/api/v1/incident-types", response_model=List[IncidentTypeOut])
def list_incident_types(db: Session = Depends(get_db)):
    return db.query(IncidentType).all()


@app.post("/api/v1/auth/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_auth_db)):
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = User(email=email, password_hash=hash_password(payload.password), role="CITIZEN")
    db.add(user)
    db.commit()
    db.refresh(user)
    refresh_token = create_refresh_token(db, user)
    audit(db, "USER_REGISTERED", "user", user.id, user.id, {"role": user.role})
    db.commit()
    return TokenResponse(
        access_token=issue_token(user, "access", timedelta(minutes=ACCESS_MINUTES)),
        refresh_token=refresh_token,
    )


@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_auth_db)):
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        audit(db, "LOGIN_FAILED", "user", user.id if user else None, metadata={"email": payload.email.strip().lower()}, result="FAILURE")
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    refresh_token = create_refresh_token(db, user)
    audit(db, "LOGIN_SUCCEEDED", "user", user.id, user.id)
    db.commit()
    return TokenResponse(
        access_token=issue_token(user, "access", timedelta(minutes=ACCESS_MINUTES)),
        refresh_token=refresh_token,
    )


@app.get("/api/v1/auth/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "role": user.role, "is_active": user.is_active}


@app.post("/api/v1/auth/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_auth_db)):
    user, refresh_token = rotate_refresh_token(db, payload.refresh_token)
    db.commit()
    return TokenResponse(
        access_token=issue_token(user, "access", timedelta(minutes=ACCESS_MINUTES)),
        refresh_token=refresh_token,
    )


@app.post("/api/v1/auth/logout", status_code=204)
def logout(payload: RefreshRequest, db: Session = Depends(get_auth_db)):
    from auth import token_hash
    session = db.query(RefreshSession).filter_by(token_hash=token_hash(payload.refresh_token)).first()
    if session and session.revoked_at is None:
        session.revoked_at = datetime.utcnow()
        audit(db, "LOGOUT", "user", session.user_id, session.user_id)
        db.commit()


@app.get("/api/v1/admin/users")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_roles("SUPER_ADMIN", "ADMIN"))):
    return [{"id": user.id, "email": user.email, "role": user.role, "is_active": user.is_active, "created_at": user.created_at} for user in db.query(User).order_by(User.email).all()]


@app.patch("/api/v1/admin/users/{user_id}/role")
def update_user_role(user_id: str, payload: UserRoleUpdate, db: Session = Depends(get_db), actor: User = Depends(require_roles("SUPER_ADMIN", "ADMIN"))):
    if payload.role not in OPERATIONAL_ROLES:
        raise HTTPException(status_code=422, detail="Unknown operational role")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if actor.role != "SUPER_ADMIN" and payload.role in {"SUPER_ADMIN", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Only a super administrator can grant administrator roles")
    user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    audit(db, "USER_ROLE_UPDATED", "user", user.id, actor.id, {"role": user.role, "is_active": user.is_active})
    db.commit()
    return {"id": user.id, "email": user.email, "role": user.role, "is_active": user.is_active}


@app.get("/api/v1/responders", response_model=List[ResponderOut])
def list_responders(db: Session = Depends(get_db), _: User = Depends(require_roles("ADMIN", "DISPATCHER", "SUPERVISOR", "RESPONDER"))):
    return db.query(Responder).all()


@app.get("/api/v1/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db), _: User = Depends(require_roles("ADMIN", "DISPATCHER", "SUPERVISOR"))):
    total_incidents = db.query(Incident).count()
    active_incidents = db.query(Incident).filter(
        Incident.status.notin_(["CLOSED", "CANCELLED", "FALSE_ALERT"])
    ).count()
    critical_incidents = db.query(Incident).filter(
        Incident.priority >= 4,
        Incident.status.notin_(["CLOSED", "CANCELLED", "FALSE_ALERT"])
    ).count()
    responders = db.query(Responder).count()
    available_responders = db.query(Responder).filter(Responder.status == "AVAILABLE").count()
    recent = (
        db.query(Incident)
        .order_by(Incident.created_at.desc())
        .limit(5)
        .all()
    )
    responder_rows = db.query(Responder).order_by(Responder.status, Responder.name).all()

    return {
        "total_incidents": total_incidents,
        "active_incidents": active_incidents,
        "critical_incidents": critical_incidents,
        "responders": responders,
        "available_responders": available_responders,
        "recent_incidents": [
            {
                "id": incident.id,
                "incident_number": incident.incident_number,
                "status": incident.status,
                "priority": incident.priority,
                "type": incident.type.code if incident.type else None,
                "location_description": incident.location_description or "Unspecified",
                "created_at": incident.created_at.isoformat(),
            }
            for incident in recent
        ],
        "responders_detail": [
            {
                "id": responder.id,
                "name": responder.name,
                "responder_type": responder.responder_type,
                "status": responder.status,
                "latitude": responder.latitude,
                "longitude": responder.longitude,
                "phone": responder.phone,
            }
            for responder in responder_rows
        ],
    }


@app.get("/api/v1/dispatch/incidents/{incident_id}/candidates")
def dispatch_candidates(incident_id: str, db: Session = Depends(get_db), _: User = Depends(require_roles("ADMIN", "DISPATCHER", "SUPERVISOR"))):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    rows = responder_candidates(db, incident, incident.type.code if incident.type else "other")
    return [{"responder_id": row["responder"].id, "name": row["responder"].name,
             "responder_type": row["responder"].responder_type, "distance_km": row["distance_km"],
             "eta_minutes": row["eta_minutes"], "status": row["responder"].status} for row in rows]


@app.post("/api/v1/dispatch/incidents/{incident_id}/assign")
async def assign_dispatch(incident_id: str, payload: DispatchRequest, db: Session = Depends(get_db), actor: User = Depends(require_roles("ADMIN", "DISPATCHER", "SUPERVISOR"))):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    responder = db.query(Responder).filter(Responder.id == payload.responder_id).first()
    if not incident or not responder:
        raise HTTPException(status_code=404, detail="Incident or responder not found")
    if responder.status != "AVAILABLE":
        raise HTTPException(status_code=409, detail="Responder is no longer available")
    distance = haversine_km(incident.latitude, incident.longitude, responder.latitude, responder.longitude)
    assignment = DispatchAssignment(incident_id=incident.id, responder_id=responder.id, status="ASSIGNED", eta_minutes=max(1, round(distance / 40 * 60)))
    responder.status = "ASSIGNED"
    db.add(assignment)
    add_history(db, incident, "DISPATCHING", f"{responder.name} assigned by dispatcher")
    audit(db, "RESPONDER_ASSIGNED", "dispatch_assignment", assignment.id, actor.id, {"responder_id": responder.id, "assignment_type": payload.assignment_type})
    db.commit()
    await manager.broadcast("dispatch.updated", {"id": incident.id, "assignment_id": assignment.id, "responder_id": responder.id})
    return {"id": assignment.id, "incident_id": incident.id, "responder_id": responder.id, "status": assignment.status, "eta_minutes": assignment.eta_minutes}


@app.post("/api/v1/incidents", response_model=IncidentOut)
async def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    itype = db.query(IncidentType).filter(IncidentType.code == payload.type_code).first()
    if not itype:
        raise HTTPException(status_code=400, detail=f"Unknown incident type '{payload.type_code}'")

    year = datetime.utcnow().year
    incident_number = f"AJL-{year}-{uuid.uuid4().hex[:10].upper()}"

    priority = itype.default_priority + (1 if payload.casualty_count >= 3 else 0)
    priority = min(priority, 5)

    incident = Incident(
        incident_number=incident_number,
        type_id=itype.id,
        reporter_phone=payload.reporter_phone,
        description=payload.description,
        priority=priority,
        casualty_count=payload.casualty_count,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_description=payload.location_description,
        landmark=payload.landmark,
        status="NEW",
        location=f"POINT({payload.longitude} {payload.latitude})",
    )
    db.add(incident)
    db.flush()
    add_history(db, incident, "NEW", "Incident reported")
    audit(db, "INCIDENT_CREATED", "incident", incident.id, metadata={"incident_number": incident.incident_number})
    if payload.reporter_phone:
        NotificationService(db).queue(payload.reporter_phone, "SMS", "incident.created", {"incident_number": incident.incident_number}, incident.id)

    add_history(db, incident, "DISPATCHING", "Awaiting dispatcher resource confirmation")

    db.commit()
    db.refresh(incident)

    await manager.broadcast("incident.created", {
        "id": incident.id,
        "incident_number": incident.incident_number,
        "status": incident.status,
        "priority": incident.priority,
    })

    return to_incident_out(db, incident)


@app.get("/api/v1/incidents", response_model=List[IncidentOut])
def list_incidents(db: Session = Depends(get_db), _: User = Depends(require_roles("ADMIN", "DISPATCHER", "SUPERVISOR", "RESPONDER"))):
    incidents = db.query(Incident).order_by(Incident.created_at.desc()).all()
    return [to_incident_out(db, i) for i in incidents]


@app.get("/api/v1/incidents/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: str, db: Session = Depends(get_db), _: User = Depends(current_user)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return to_incident_out(db, incident)


@app.patch("/api/v1/incidents/{incident_id}/status", response_model=IncidentOut)
async def update_status(incident_id: str, payload: StatusUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles("ADMIN", "DISPATCHER", "SUPERVISOR", "RESPONDER"))):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    allowed = VALID_TRANSITIONS.get(incident.status, set())
    if payload.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move from {incident.status} to {payload.status}. Allowed: {sorted(allowed)}",
        )

    add_history(db, incident, payload.status, payload.note or "")
    audit(db, "INCIDENT_STATUS_CHANGED", "incident", incident.id, metadata={"status": payload.status})
    if incident.reporter_phone:
        NotificationService(db).queue(incident.reporter_phone, "SMS", "incident.updated", {"status": payload.status}, incident.id)

    if payload.status in ("RESOLVED", "CANCELLED"):
        for a in incident.assignments:
            if a.responder:
                a.responder.status = "AVAILABLE"
                db.add(a.responder)

    db.commit()
    db.refresh(incident)

    await manager.broadcast("incident.updated", {
        "id": incident.id,
        "incident_number": incident.incident_number,
        "status": incident.status,
    })

    return to_incident_out(db, incident)


@app.post("/api/v1/first-aid/ask", response_model=List[FirstAidTopicOut])
def ask_first_aid(payload: FirstAidQuery, db: Session = Depends(get_db)):
    """Free-text first-aid follow-up. Matches purely against the local KB -
    no network call, same answer every time for the same question."""
    type_code = payload.type_code
    if payload.incident_id and not type_code:
        incident = db.query(Incident).filter(Incident.id == payload.incident_id).first()
        if incident and incident.type:
            type_code = incident.type.code
    topics = match_topics(payload.query, type_code=type_code, limit=3)
    return [FirstAidTopicOut(**t) for t in topics]


@app.post("/api/v1/assistant/chat", response_model=AIChatResponse)
def assistant_chat(payload: AIChatRequest, db: Session = Depends(get_db), _: User = Depends(require_roles("ADMIN", "DISPATCHER", "SUPERVISOR", "INTELLIGENCE_OFFICER"))):
    context = {}
    if payload.incident_id:
        incident = db.query(Incident).filter(Incident.id == payload.incident_id).first()
        if incident:
            context = {
                "status": incident.status,
                "priority": incident.priority,
                "type": incident.type.code if incident.type else None,
                "location": incident.location_description or "Unspecified",
                "description": incident.description,
            }
    provider = get_ai_provider()
    reply = provider.chat(
        payload.message,
        incident_id=payload.incident_id,
        context=context,
        user_role=payload.user_role,
    )
    return AIChatResponse(reply=reply, incident_id=payload.incident_id, user_role=payload.user_role)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
