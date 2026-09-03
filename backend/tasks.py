from celery import Celery
from datetime import datetime, timedelta
from models import Incident, SessionLocal
from services import NotificationService, audit
import os

celery_app = Celery("ajali", broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
celery_app.conf.update(task_serializer="json", accept_content=["json"], result_serializer="json", timezone="UTC", enable_utc=True)


@celery_app.task
def process_notifications():
    db = SessionLocal()
    try:
        return NotificationService(db).process_pending()
    finally:
        db.close()


@celery_app.task
def process_escalations():
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        incidents = db.query(Incident).filter(Incident.status == "DISPATCHING", Incident.updated_at < cutoff, Incident.is_escalated.is_(False)).all()
        for incident in incidents:
            incident.is_escalated = True
            incident.status = "ESCALATED"
            audit(db, "INCIDENT_ESCALATED", "incident", incident.id, metadata={"reason": "dispatch acknowledgement timeout"})
            if incident.reporter_phone:
                NotificationService(db).queue(incident.reporter_phone, "SMS", "incident.escalated", {"incident_number": incident.incident_number}, incident.id)
        db.commit()
        return len(incidents)
    finally:
        db.close()


@celery_app.on_after_configure.connect
def schedule_tasks(sender, **kwargs):
    sender.add_periodic_task(30.0, process_notifications.s(), name="process notifications")
    sender.add_periodic_task(30.0, process_escalations.s(), name="process escalations")