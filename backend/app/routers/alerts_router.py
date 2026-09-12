from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, require_role
from app.database import get_db
from app.models import (
    User, Alert, AlertEvent, Notification,
    EmergencyCategoryEnum, EmergencySubTypeEnum, ResponderTypeEnum,
    SeverityEnum, StatusEnum, RegionEnum, CallerChannelEnum, RoleEnum,
    EventKindEnum, NotifyChannelEnum, NotifyStatusEnum,
)
from app.schemas import (
    AlertCreate, AlertUpdate, AlertRead, AlertListResponse,
    AlertEventCreate, AlertEventRead, NotificationCreate, NotificationRead,
)
from app.websocket_manager import ws_manager

router = APIRouter(prefix="/alerts", tags=["Alerts"])


# ── CRUD ──────────────────────────────────────────────────

@router.post("/", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: AlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new emergency alert and broadcast it via WebSocket."""
    # Dedup check
    if body.source and body.source_id:
        existing = await db.execute(
            select(Alert).where(Alert.source == body.source, Alert.source_id == body.source_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Duplicate alert from this source")

    alert = Alert(
        **body.model_dump(),
        created_by=current_user.id,
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)

    # Audit event
    event = AlertEvent(
        alert_id=alert.id,
        kind=EventKindEnum.created,
        message=f"{body.category.value.upper()} emergency reported via {body.caller_channel.value} by {current_user.username}",
        performed_by=current_user.id,
    )
    db.add(event)

    # Auto-notify based on category
    responder_map = {
        EmergencyCategoryEnum.accident: ("Police + Ambulance", NotifyChannelEnum.sms),
        EmergencyCategoryEnum.fire: ("Fire Brigade + Ambulance", NotifyChannelEnum.sms),
        EmergencyCategoryEnum.medical: ("Ambulance", NotifyChannelEnum.sms),
        EmergencyCategoryEnum.security: ("Police", NotifyChannelEnum.sms),
    }
    target_team, channel = responder_map.get(body.category, ("Dispatch", NotifyChannelEnum.sms))

    notification = Notification(
        alert_id=alert.id,
        channel=channel,
        recipient=target_team,
        message=(
            f"🚨 AJALI ALERT [{body.severity.value.upper()}] {body.category.value.upper()}\n"
            f"Location: {body.location or 'GPS: ' + str(body.latitude) + ',' + str(body.longitude) if body.latitude else 'Unknown'}\n"
            f"Casualties: {body.casualty_count} | Entrapped: {'Yes' if body.entrapped else 'No'}\n"
            f"Responder needed: {target_team}\n"
            f"Description: {body.description}"
        ),
        status=NotifyStatusEnum.pending,
    )
    db.add(notification)

    # Broadcast to WebSocket clients
    alert_data = AlertRead.model_validate(alert).model_dump(mode="json")
    await ws_manager.broadcast_alert(alert_data)

    return alert


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    severity: Optional[SeverityEnum] = None,
    status: Optional[StatusEnum] = None,
    category: Optional[EmergencyCategoryEnum] = None,
    sub_type: Optional[EmergencySubTypeEnum] = None,
    region: Optional[RegionEnum] = None,
    responder_type: Optional[ResponderTypeEnum] = None,
    team: Optional[str] = None,
    county: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List alerts with filtering, search, and pagination."""
    query = select(Alert)

    if severity:
        query = query.where(Alert.severity == severity)
    if status:
        query = query.where(Alert.status == status)
    if category:
        query = query.where(Alert.category == category)
    if sub_type:
        query = query.where(Alert.sub_type == sub_type)
    if region:
        query = query.where(Alert.region == region)
    if responder_type:
        query = query.where(Alert.responder_type == responder_type)
    if team:
        query = query.where(Alert.team == team)
    if county:
        query = query.where(Alert.county == county)
    if search:
        query = query.where(Alert.title.ilike(f"%{search}%") | Alert.description.ilike(f"%{search}%") | Alert.location.ilike(f"%{search}%"))

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.order_by(desc(Alert.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return AlertListResponse(items=alerts, total=total, page=page, page_size=page_size)


@router.get("/{alert_id}", response_model=AlertRead)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{alert_id}", response_model=AlertRead)
async def update_alert(
    alert_id: int,
    body: AlertUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    now = datetime.now(timezone.utc)
    update_data = body.model_dump(exclude_unset=True)

    # Track status transitions
    new_status = update_data.get("status")
    if new_status and new_status != alert.status:
        if new_status == StatusEnum.acknowledged and alert.status == StatusEnum.active:
            alert.acknowledged_at = now
            alert.response_time_seconds = (now - alert.created_at).total_seconds()
            event = AlertEvent(alert_id=alert.id, kind=EventKindEnum.acknowledged,
                              message=f"Dispatch acknowledged by {current_user.username}",
                              performed_by=current_user.id)
            db.add(event)

        elif new_status == StatusEnum.dispatching:
            alert.dispatched_at = now
            alert.dispatch_time_seconds = (now - alert.created_at).total_seconds()
            event = AlertEvent(alert_id=alert.id, kind=EventKindEnum.dispatching,
                              message=f"Dispatching {alert.responder_type.value if alert.responder_type else 'responders'} to scene",
                              performed_by=current_user.id)
            db.add(event)

        elif new_status == StatusEnum.en_route:
            event = AlertEvent(alert_id=alert.id, kind=EventKindEnum.en_route,
                              message=f"Responder(s) en route — ETA {alert.eta_minutes or '?'} min",
                              performed_by=current_user.id)
            db.add(event)

        elif new_status == StatusEnum.on_scene:
            alert.arrived_at = now
            event = AlertEvent(alert_id=alert.id, kind=EventKindEnum.on_scene,
                              message=f"Responder arrived on scene",
                              performed_by=current_user.id)
            db.add(event)

        elif new_status == StatusEnum.resolved:
            alert.resolved_at = now
            alert.resolution_time_seconds = (now - alert.created_at).total_seconds()
            event = AlertEvent(alert_id=alert.id, kind=EventKindEnum.resolved,
                              message=f"Incident resolved by {current_user.username}",
                              performed_by=current_user.id)
            db.add(event)

        elif new_status == StatusEnum.escalated:
            event = AlertEvent(alert_id=alert.id, kind=EventKindEnum.escalated,
                              message=f"Escalated — no response within timeout window",
                              performed_by=current_user.id)
            db.add(event)

        elif new_status == StatusEnum.suppressed:
            event = AlertEvent(alert_id=alert.id, kind=EventKindEnum.suppressed,
                              message=f"Suppressed by {current_user.username}",
                              performed_by=current_user.id)
            db.add(event)

    # Track severity changes
    new_severity = update_data.get("severity")
    if new_severity and new_severity != alert.severity:
        event = AlertEvent(alert_id=alert.id, kind=EventKindEnum.severity_changed,
                          message=f"Severity changed from {alert.severity.value} to {new_severity.value} by {current_user.username}",
                          performed_by=current_user.id)
        db.add(event)

    # Track reassignment
    new_assignee = update_data.get("assigned_to")
    if new_assignee is not None and new_assignee != alert.assigned_to:
        event = AlertEvent(alert_id=alert.id, kind=EventKindEnum.reassigned,
                          message=f"Reassigned to responder #{new_assignee} by {current_user.username}",
                          performed_by=current_user.id)
        db.add(event)

    # Track casualty updates
    new_casualties = update_data.get("casualty_count")
    if new_casualties is not None and new_casualties != alert.casualty_count:
        event = AlertEvent(alert_id=alert.id, kind=EventKindEnum.casualty_update,
                          message=f"Casualty count updated: {alert.casualty_count} -> {new_casualties}",
                          performed_by=current_user.id)
        db.add(event)

    # Track ETA updates
    new_eta = update_data.get("eta_minutes")
    if new_eta is not None and new_eta != alert.eta_minutes:
        event = AlertEvent(alert_id=alert.id, kind=EventKindEnum.eta_update,
                          message=f"ETA updated: {alert.eta_minutes or '?'} min -> {new_eta} min",
                          performed_by=current_user.id)
        db.add(event)

    for field, value in update_data.items():
        setattr(alert, field, value)
    alert.updated_at = now
    db.add(alert)
    await db.flush()
    await db.refresh(alert)

    # Broadcast status change
    alert_data = AlertRead.model_validate(alert).model_dump(mode="json")
    await ws_manager.broadcast_event("alert_updated", alert_data)

    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.admin)),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.delete(alert)


# ── Quick Dispatch Endpoint ───────────────────────────────

@router.post("/{alert_id}/dispatch", response_model=AlertRead)
async def dispatch_responders(
    alert_id: int,
    responder_type: ResponderTypeEnum = Query(...),
    eta_minutes: float = Query(..., ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.admin, RoleEnum.dispatcher)),
):
    """Quick-dispatch responders to an alert — sets status to dispatching."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    now = datetime.now(timezone.utc)
    alert.responder_type = responder_type
    alert.eta_minutes = eta_minutes
    alert.status = StatusEnum.dispatching
    alert.dispatched_at = now
    alert.dispatch_time_seconds = (now - alert.created_at).total_seconds()
    alert.updated_at = now

    event = AlertEvent(
        alert_id=alert.id,
        kind=EventKindEnum.dispatching,
        message=f"Dispatched {responder_type.value} — ETA {eta_minutes} min",
        performed_by=current_user.id,
    )
    db.add(event)

    # Create notification to the dispatched team
    notification = Notification(
        alert_id=alert.id,
        channel=NotifyChannelEnum.sms,
        recipient=responder_type.value,
        message=(
            f"🚨 DISPATCH ORDER [{alert.severity.value.upper()}] {alert.category.value.upper()}\n"
            f"Location: {alert.location or 'See GPS'}\n"
            f"ETA Required: {eta_minutes} min\n"
            f"Casualties: {alert.casualty_count}\n"
            f"Incident: {alert.title}"
        ),
        status=NotifyStatusEnum.pending,
    )
    db.add(notification)

    await db.flush()
    await db.refresh(alert)

    # Broadcast dispatch
    alert_data = AlertRead.model_validate(alert).model_dump(mode="json")
    await ws_manager.broadcast_event("alert_dispatched", alert_data)

    return alert


# ── Acknowledge & Resolve ─────────────────────────────────

@router.post("/{alert_id}/acknowledge", response_model=AlertRead)
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Acknowledge an alert — dispatcher confirms receipt."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status != StatusEnum.active:
        raise HTTPException(status_code=400, detail=f"Cannot acknowledge alert in {alert.status.value} status")

    now = datetime.now(timezone.utc)
    alert.status = StatusEnum.acknowledged
    alert.acknowledged_at = now
    alert.response_time_seconds = (now - alert.created_at).total_seconds()
    alert.assigned_to = current_user.id
    alert.updated_at = now

    event = AlertEvent(
        alert_id=alert.id,
        kind=EventKindEnum.acknowledged,
        message=f"Acknowledged by {current_user.username}",
        performed_by=current_user.id,
    )
    db.add(event)
    await db.flush()
    await db.refresh(alert)

    alert_data = AlertRead.model_validate(alert).model_dump(mode="json")
    await ws_manager.broadcast_event("alert_acknowledged", alert_data)

    return alert


@router.post("/{alert_id}/resolve", response_model=AlertRead)
async def resolve_alert(
    alert_id: int,
    outcome: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resolve an emergency incident."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    now = datetime.now(timezone.utc)
    alert.status = StatusEnum.resolved
    alert.resolved_at = now
    alert.resolution_time_seconds = (now - alert.created_at).total_seconds()
    alert.updated_at = now

    resolution_msg = f"Incident resolved by {current_user.username}"
    if outcome:
        resolution_msg += f" — {outcome}"

    event = AlertEvent(
        alert_id=alert.id,
        kind=EventKindEnum.resolved,
        message=resolution_msg,
        performed_by=current_user.id,
    )
    db.add(event)
    await db.flush()
    await db.refresh(alert)

    alert_data = AlertRead.model_validate(alert).model_dump(mode="json")
    await ws_manager.broadcast_event("alert_resolved", alert_data)

    return alert


# ── Alert Events (Audit Trail) ────────────────────────────

@router.get("/{alert_id}/events", response_model=List[AlertEventRead])
async def list_alert_events(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AlertEvent).where(AlertEvent.alert_id == alert_id).order_by(AlertEvent.created_at)
    )
    return result.scalars().all()


@router.post("/{alert_id}/events", response_model=AlertEventRead, status_code=status.HTTP_201_CREATED)
async def add_alert_event(
    alert_id: int,
    body: AlertEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify alert exists
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Alert not found")

    event = AlertEvent(
        alert_id=alert_id,
        kind=body.kind,
        message=body.message,
        performed_by=current_user.id,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


# ── Notifications ──────────────────────────────────────────

@router.post("/{alert_id}/notify", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
async def send_notification(
    alert_id: int,
    body: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.admin, RoleEnum.dispatcher)),
):
    # Verify alert exists
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Alert not found")

    notification = Notification(
        alert_id=alert_id,
        channel=body.channel,
        recipient=body.recipient,
        message=body.message,
        status=NotifyStatusEnum.pending,
    )
    db.add(notification)
    await db.flush()
    await db.refresh(notification)
    return notification


@router.get("/{alert_id}/notifications", response_model=List[NotificationRead])
async def list_alert_notifications(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Notification).where(Notification.alert_id == alert_id).order_by(Notification.sent_at)
    )
    return result.scalars().all()


# ── WebSocket Endpoint ─────────────────────────────────────

@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Client can send subscription updates
            import json
            msg = json.loads(data)
            if msg.get("type") == "subscribe":
                ws_manager.subscribe(
                    websocket,
                    severities=msg.get("severities"),
                    categories=msg.get("categories"),
                    regions=msg.get("regions"),
                )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
