import json
import logging
import os
from datetime import datetime, timedelta

from models import AuditLog, Hospital, Incident, IncidentStatusHistory, IncidentType, Notification, USSDSession, gen_id

logger = logging.getLogger("ajali.services")


def audit(db, action, resource_type, resource_id=None, actor_id=None, metadata=None, result="SUCCESS"):
    db.add(AuditLog(actor_id=actor_id, action=action, resource_type=resource_type,
                    resource_id=resource_id, result=result, details=metadata or {}))


class NotificationService:
    def __init__(self, db):
        self.db = db

    def queue(self, recipient, channel, event, payload, incident_id=None):
        notification = Notification(recipient=recipient, channel=channel, event=event,
                                    payload=payload, incident_id=incident_id)
        self.db.add(notification)
        self.db.flush()
        return notification

    def process_pending(self, limit=50):
        rows = self.db.query(Notification).filter(Notification.status.in_(["PENDING", "RETRYING"])).limit(limit).all()
        for row in rows:
            row.attempts += 1
            if row.channel == "IN_APP":
                row.status = "SENT"
                row.sent_at = datetime.utcnow()
            else:
                row.status = "FAILED"
                row.last_error = f"{row.channel} provider is not configured"
        self.db.commit()
        return len(rows)


class HospitalService:
    def __init__(self, db):
        self.db = db

    def recommend(self, latitude, longitude, trauma=False, limit=5):
        hospitals = self.db.query(Hospital).filter(
            Hospital.status == "OPERATIONAL", Hospital.emergency_available.is_(True), Hospital.available_beds > 0
        ).all()
        if trauma:
            hospitals = [hospital for hospital in hospitals if hospital.trauma_capable]
        hospitals.sort(key=lambda hospital: (latitude - hospital.latitude) ** 2 + (longitude - hospital.longitude) ** 2)
        return hospitals[:limit]


class USSDService:
    timeout = timedelta(minutes=5)

    def __init__(self, db):
        self.db = db

    def handle(self, session_id, phone, text):
        now = datetime.utcnow()
        session = self.db.query(USSDSession).filter(USSDSession.session_id == session_id).first()
        if not session or session.expires_at <= now:
            session = USSDSession(session_id=session_id, phone_number=phone, expires_at=now + self.timeout)
            self.db.add(session)
        session.updated_at = now
        parts = [part.strip() for part in (text or "").split("*") if part.strip()]
        if not parts:
            session.state = "TYPE"
            reply = "CON Emergency type:\n1. Medical\n2. Fire\n3. Accident\n4. Security"
        elif session.state == "TYPE":
            session.data = {"type_code": {"1": "medical", "2": "fire", "3": "road_accident", "4": "security"}.get(parts[-1], "other")}
            session.state = "DESCRIPTION"
            reply = "CON Describe the emergency"
        elif session.state == "DESCRIPTION":
            session.data = {**session.data, "description": parts[-1]}
            session.state = "CASUALTIES"
            reply = "CON Number of casualties"
        elif session.state == "CASUALTIES":
            try:
                casualties = max(0, int(parts[-1]))
            except ValueError:
                casualties = 0
            session.data = {**session.data, "casualty_count": casualties}
            session.state = "LOCATION"
            reply = "CON Enter a landmark or location"
        else:
            if session.incident_id:
                existing = self.db.query(Incident).filter(Incident.id == session.incident_id).first()
                return f"END Report already received. Incident {existing.incident_number}."
            session.data = {**session.data, "location_description": parts[-1]}
            session.state = "COMPLETE"
            incident_type = self.db.query(IncidentType).filter(IncidentType.code == session.data.get("type_code")).first()
            if not incident_type:
                incident_type = self.db.query(IncidentType).filter(IncidentType.code == "other").first()
            incident = Incident(
                incident_number=f"AJL-USSD-{session.session_id}",
                type_id=incident_type.id if incident_type else None,
                description=session.data.get("description", "USSD emergency report"),
                casualty_count=session.data.get("casualty_count", 0),
                latitude=0,
                longitude=0,
                location_description=session.data["location_description"],
                reporter_phone=session.phone_number,
                status="NEW",
            )
            self.db.add(incident)
            self.db.flush()
            self.db.add(IncidentStatusHistory(incident_id=incident.id, status="NEW", note="USSD report received"))
            session.incident_id = incident.id
            audit(self.db, "USSD_INCIDENT_CREATED", "incident", incident.id, metadata={"session_id": session.session_id})
            reply = f"END Report received. Incident {incident.incident_number}. A coordinator will contact you."
        self.db.commit()
        return reply