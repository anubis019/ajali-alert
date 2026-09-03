import os

from models import SessionLocal, IncidentType, Responder, User
from auth import hash_password

INCIDENT_TYPES = [
    {"name": "Road Accident", "code": "road_accident", "icon": "Road", "default_priority": 4},
    {"name": "Medical Emergency", "code": "medical", "icon": "Medical", "default_priority": 4},
    {"name": "Fire Emergency", "code": "fire", "icon": "Fire", "default_priority": 5},
    {"name": "Security Emergency", "code": "security", "icon": "Security", "default_priority": 4},
    {"name": "Other", "code": "other", "icon": "Other", "default_priority": 2},
]

# Roughly scattered around Nairobi CBD (-1.2864, 36.8172)
RESPONDERS = [
    {"name": "Ambulance Unit 1", "responder_type": "ambulance", "latitude": -1.2833, "longitude": 36.8167, "phone": "0700000001"},
    {"name": "Ambulance Unit 2", "responder_type": "ambulance", "latitude": -1.3000, "longitude": 36.7800, "phone": "0700000002"},
    {"name": "Fire Unit 1", "responder_type": "fire", "latitude": -1.2921, "longitude": 36.8219, "phone": "0700000003"},
    {"name": "Police Patrol 1", "responder_type": "police", "latitude": -1.2741, "longitude": 36.8121, "phone": "0700000004"},
    {"name": "Police Patrol 2", "responder_type": "police", "latitude": -1.3100, "longitude": 36.8500, "phone": "0700000005"},
    {"name": "Community Responder 1", "responder_type": "community", "latitude": -1.2650, "longitude": 36.8000, "phone": "0700000006"},
]


def seed():
    db = SessionLocal()
    try:
        if db.query(IncidentType).count() == 0:
            for t in INCIDENT_TYPES:
                db.add(IncidentType(**t))
        if db.query(Responder).count() == 0:
            for r in RESPONDERS:
                db.add(Responder(**r, status="AVAILABLE"))
        admin_email = os.getenv("BOOTSTRAP_ADMIN_EMAIL")
        admin_password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
        if admin_email and admin_password and not db.query(User).filter(User.email == admin_email.lower()).first():
            db.add(User(email=admin_email.lower(), password_hash=hash_password(admin_password), role="SUPER_ADMIN"))
        db.commit()
    finally:
        db.close()
