import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func

from app.database import async_session, init_db
from app.models import (
    User, Alert, AlertEvent, Team, EscalationPolicy, Notification,
    EmergencyCategoryEnum, EmergencySubTypeEnum, ResponderTypeEnum,
    SeverityEnum, StatusEnum, RegionEnum, CallerChannelEnum, RoleEnum,
    EventKindEnum, NotifyChannelEnum, NotifyStatusEnum,
)
from app.auth import hash_password

logger = logging.getLogger("ajali.seed")


async def seed():
    await init_db()

    async with async_session() as db:
        # ── Users (Emergency Response Staff) ────────
        users_data = [
            {"username": "admin", "email": "admin@ajali.systems", "password": "admin1234",
             "full_name": "Grace Wanjiku", "phone": "+254712345678", "role": RoleEnum.admin,
             "team": "Dispatch HQ", "county": "Nairobi"},
            {"username": "sarah.chen", "email": "sarah@ajali.systems", "password": "responder1",
             "full_name": "Sarah Chen", "phone": "+254723456789", "role": RoleEnum.dispatcher,
             "team": "Nairobi Dispatch", "county": "Nairobi"},
            {"username": "james.okafor", "email": "james@ajali.systems", "password": "responder2",
             "full_name": "James Okafor", "phone": "+254734567890", "role": RoleEnum.responder,
             "team": "Nairobi Ambulance", "responder_type": ResponderTypeEnum.ambulance, "county": "Nairobi"},
            {"username": "officer.wambua", "email": "wambua@ajali.systems", "password": "police1",
             "full_name": "David Wambua", "phone": "+254745678901", "role": RoleEnum.responder,
             "team": "Nairobi Police", "responder_type": ResponderTypeEnum.police, "badge_number": "KP-28451", "county": "Nairobi"},
            {"username": "firefighter.akello", "email": "akello@ajali.systems", "password": "fire1",
             "full_name": "Peter Akello", "phone": "+254756789012", "role": RoleEnum.responder,
             "team": "Nairobi Fire Brigade", "responder_type": ResponderTypeEnum.fire_brigade, "badge_number": "NFB-0112", "county": "Nairobi"},
            {"username": "boda.kamau", "email": "kamau@ajali.systems", "password": "community1",
             "full_name": "John Kamau", "phone": "+254767890123", "role": RoleEnum.responder,
             "team": "Ruai Community Responders", "responder_type": ResponderTypeEnum.community_responder, "county": "Nairobi"},
            {"username": "viewer", "email": "viewer@ajali.systems", "password": "viewer1234",
             "full_name": "Read Only", "role": RoleEnum.viewer, "team": None},
        ]
        for u in users_data:
            exists = await db.execute(select(User).where(User.username == u["username"]))
            if not exists.scalar_one_or_none():
                user = User(
                    username=u["username"],
                    email=u["email"],
                    hashed_password=hash_password(u["password"]),
                    full_name=u["full_name"],
                    phone=u.get("phone"),
                    role=u["role"],
                    team=u.get("team"),
                    responder_type=u.get("responder_type"),
                    badge_number=u.get("badge_number"),
                    county=u.get("county"),
                )
                db.add(user)
        await db.commit()

        # ── Teams (Emergency Response Teams) ────────
        teams_data = [
            {"name": "Nairobi Dispatch HQ", "responder_type": None, "county": "Nairobi",
             "on_call_count": 6, "active_incidents": 5, "avg_response_minutes": 2.1,
             "resolution_rate": 96.5, "escalation_rate": 3.5, "capacity_pct": 82},
            {"name": "Nairobi Ambulance Unit", "responder_type": ResponderTypeEnum.ambulance, "county": "Nairobi",
             "on_call_count": 8, "active_incidents": 4, "avg_response_minutes": 4.8,
             "resolution_rate": 94.2, "escalation_rate": 5.8, "capacity_pct": 71},
            {"name": "Nairobi Police Response", "responder_type": ResponderTypeEnum.police, "county": "Nairobi",
             "on_call_count": 12, "active_incidents": 6, "avg_response_minutes": 5.2,
             "resolution_rate": 91.0, "escalation_rate": 9.0, "capacity_pct": 68},
            {"name": "Nairobi Fire Brigade", "responder_type": ResponderTypeEnum.fire_brigade, "county": "Nairobi",
             "on_call_count": 5, "active_incidents": 2, "avg_response_minutes": 6.1,
             "resolution_rate": 89.5, "escalation_rate": 10.5, "capacity_pct": 55},
            {"name": "Ruai Community Responders", "responder_type": ResponderTypeEnum.community_responder, "county": "Nairobi",
             "on_call_count": 15, "active_incidents": 3, "avg_response_minutes": 1.5,
             "resolution_rate": 78.0, "escalation_rate": 22.0, "capacity_pct": 90},
            {"name": "Mombasa County Ambulance", "responder_type": ResponderTypeEnum.ambulance, "county": "Mombasa",
             "on_call_count": 4, "active_incidents": 2, "avg_response_minutes": 7.3,
             "resolution_rate": 88.0, "escalation_rate": 12.0, "capacity_pct": 60},
            {"name": "Nakuru Fire & Rescue", "responder_type": ResponderTypeEnum.fire_brigade, "county": "Nakuru",
             "on_call_count": 3, "active_incidents": 1, "avg_response_minutes": 8.0,
             "resolution_rate": 85.0, "escalation_rate": 15.0, "capacity_pct": 45},
        ]
        for t in teams_data:
            exists = await db.execute(select(Team).where(Team.name == t["name"]))
            if not exists.scalar_one_or_none():
                db.add(Team(**t))
        await db.commit()

        # ── Escalation Policies (Emergency-Grade) ──
        policies = [
            # Critical accidents — escalate after 3 min (Golden Hour target)
            {"name": "Critical-Accident-3min", "category": EmergencyCategoryEnum.accident,
             "severity": SeverityEnum.critical, "delay_minutes": 3,
             "notify_channel": NotifyChannelEnum.sms, "notify_recipient": "county-ambulance-backup",
             "responder_type": ResponderTypeEnum.ambulance, "auto_escalate": True, "repeat_interval_minutes": 2},
            # Critical medical — escalate after 3 min
            {"name": "Critical-Medical-3min", "category": EmergencyCategoryEnum.medical,
             "severity": SeverityEnum.critical, "delay_minutes": 3,
             "notify_channel": NotifyChannelEnum.sms, "notify_recipient": "county-medical-backup",
             "responder_type": ResponderTypeEnum.ambulance, "auto_escalate": True, "repeat_interval_minutes": 2},
            # Critical fire — escalate after 2 min
            {"name": "Critical-Fire-2min", "category": EmergencyCategoryEnum.fire,
             "severity": SeverityEnum.critical, "delay_minutes": 2,
             "notify_channel": NotifyChannelEnum.sms, "notify_recipient": "county-fire-backup",
             "responder_type": ResponderTypeEnum.fire_brigade, "auto_escalate": True, "repeat_interval_minutes": 2},
            # Critical security — escalate after 3 min
            {"name": "Critical-Security-3min", "category": EmergencyCategoryEnum.security,
             "severity": SeverityEnum.critical, "delay_minutes": 3,
             "notify_channel": NotifyChannelEnum.sms, "notify_recipient": "county-police-backup",
             "responder_type": ResponderTypeEnum.police, "auto_escalate": True, "repeat_interval_minutes": 3},
            # High-severity any category — 10 min
            {"name": "High-Any-10min", "severity": SeverityEnum.high, "delay_minutes": 10,
             "notify_channel": NotifyChannelEnum.sms, "notify_recipient": "dispatch-lead",
             "auto_escalate": True, "repeat_interval_minutes": 5},
            # Medium — 30 min
            {"name": "Medium-30min", "severity": SeverityEnum.medium, "delay_minutes": 30,
             "notify_channel": NotifyChannelEnum.email, "notify_recipient": "team-lead",
             "auto_escalate": True, "repeat_interval_minutes": 0},
            # Low — no auto-escalate
            {"name": "Low-NoAuto", "severity": SeverityEnum.low, "delay_minutes": 1440,
             "notify_channel": NotifyChannelEnum.email, "notify_recipient": "",
             "auto_escalate": False, "repeat_interval_minutes": 0},
        ]
        for p in policies:
            exists = await db.execute(select(EscalationPolicy).where(EscalationPolicy.name == p["name"]))
            if not exists.scalar_one_or_none():
                db.add(EscalationPolicy(**p))
        await db.commit()

        # ── Sample Emergency Alerts ─────────────────
        now = datetime.now(timezone.utc)
        alerts_data = [
            # ACCIDENT alerts
            {"title": "Head-on collision — Thika Super Highway near Kenyatta University",
             "description": "Two vehicles involved in head-on collision. At least 3 casualties reported, 2 possibly entrapped. Bystanders attempting first aid.",
             "severity": SeverityEnum.critical, "status": StatusEnum.dispatching,
             "category": EmergencyCategoryEnum.accident, "sub_type": EmergencySubTypeEnum.multi_vehicle,
             "region": RegionEnum.nairobi, "location": "Thika Super Highway, Near Kenyatta University",
             "latitude": -1.1558, "longitude": 36.9285, "county": "Nairobi",
             "caller_phone": "+254712345000", "caller_name": "Mary Njoroge",
             "caller_channel": CallerChannelEnum.app,
             "casualty_count": 3, "entrapped": True, "hazard_present": False,
             "responder_type": ResponderTypeEnum.ambulance, "eta_minutes": 6.5,
             "source": "Ajali App", "source_id": "app-accident-001",
             "team": "Nairobi Ambulance Unit",
             "created_at": now - timedelta(minutes=4),
             "dispatched_at": now - timedelta(minutes=2),
             "dispatch_time_seconds": 120},

            {"title": "Motorcycle vs pedestrian — Moi Avenue, CBD",
             "description": "Boda boda rider struck pedestrian at crossing. Victim unconscious, bleeding from head.",
             "severity": SeverityEnum.high, "status": StatusEnum.en_route,
             "category": EmergencyCategoryEnum.accident, "sub_type": EmergencySubTypeEnum.pedestrian_hit,
             "region": RegionEnum.nairobi, "location": "Moi Avenue, Nairobi CBD",
             "latitude": -1.2864, "longitude": 36.8245, "county": "Nairobi",
             "caller_phone": "+254723456000", "caller_channel": CallerChannelEnum.ussd,
             "casualty_count": 2, "entrapped": False, "hazard_present": False,
             "responder_type": ResponderTypeEnum.ambulance, "eta_minutes": 3.0,
             "source": "USSD *1233#", "source_id": "ussd-accident-002",
             "team": "Nairobi Ambulance Unit",
             "created_at": now - timedelta(minutes=8),
             "acknowledged_at": now - timedelta(minutes=7),
             "response_time_seconds": 60,
             "dispatched_at": now - timedelta(minutes=6),
             "dispatch_time_seconds": 120},

            {"title": "Bus overturned — Nakuru-Eldoret Highway",
             "description": "Matatu bus lost control and overturned. Multiple passengers trapped inside. 8+ casualties estimated.",
             "severity": SeverityEnum.critical, "status": StatusEnum.active,
             "category": EmergencyCategoryEnum.accident, "sub_type": EmergencySubTypeEnum.bus_accident,
             "region": RegionEnum.nakuru, "location": "Nakuru-Eldoret Highway, Near Salgaa",
             "latitude": -0.2833, "longitude": 36.0667, "county": "Nakuru",
             "caller_phone": "+254734567000", "caller_name": "Francis Kiprop",
             "caller_channel": CallerChannelEnum.phone,
             "casualty_count": 8, "entrapped": True, "hazard_present": False,
             "source": "Voice Call", "source_id": "call-accident-003",
             "team": "Nakuru Fire & Rescue",
             "created_at": now - timedelta(minutes=2)},

            # FIRE alerts
            {"title": "Structural fire — Kibera residential block",
             "description": "Fire engulfing residential block in Kibera. Smoke visible from 500m. Possible gas cylinder explosion. Residents trapped on upper floors.",
             "severity": SeverityEnum.critical, "status": StatusEnum.acknowledged,
             "category": EmergencyCategoryEnum.fire, "sub_type": EmergencySubTypeEnum.structural_fire,
             "region": RegionEnum.nairobi, "location": "Kibera, Mashimoni Village",
             "latitude": -1.3134, "longitude": 36.7854, "county": "Nairobi",
             "caller_phone": "+254745678000", "caller_name": "Amina Osman",
             "caller_channel": CallerChannelEnum.ussd,
             "casualty_count": 0, "entrapped": True, "fire_severity": "large", "hazard_present": True,
             "responder_type": ResponderTypeEnum.fire_brigade, "eta_minutes": 8.0,
             "source": "USSD *1233#", "source_id": "ussd-fire-001",
             "team": "Nairobi Fire Brigade",
             "created_at": now - timedelta(minutes=5),
             "acknowledged_at": now - timedelta(minutes=4),
             "response_time_seconds": 60},

            {"title": "Vehicle fire — Mombasa Road near Syokimau",
             "description": "Lorry engine caught fire on Mombasa Road. Driver escaped. Fire spreading to cargo area — possible fuel load.",
             "severity": SeverityEnum.high, "status": StatusEnum.on_scene,
             "category": EmergencyCategoryEnum.fire, "sub_type": EmergencySubTypeEnum.vehicle_fire,
             "region": RegionEnum.machakos, "location": "Mombasa Road, Syokimau",
             "latitude": -1.3833, "longitude": 36.9167, "county": "Machakos",
             "caller_phone": "+254756789000", "caller_channel": CallerChannelEnum.app,
             "casualty_count": 0, "entrapped": False, "fire_severity": "medium", "hazard_present": True,
             "responder_type": ResponderTypeEnum.fire_brigade, "eta_minutes": 0,
             "source": "Ajali App", "source_id": "app-fire-002",
             "team": "Nairobi Fire Brigade",
             "created_at": now - timedelta(minutes=18),
             "acknowledged_at": now - timedelta(minutes=17),
             "dispatched_at": now - timedelta(minutes=16),
             "arrived_at": now - timedelta(minutes=10),
             "response_time_seconds": 60,
             "dispatch_time_seconds": 120},

            {"title": "Chemical spill — Industrial Area warehouse",
             "description": "Chemical container ruptured at warehouse. Toxic fumes spreading. 2 workers hospitalized.",
             "severity": SeverityEnum.critical, "status": StatusEnum.active,
             "category": EmergencyCategoryEnum.fire, "sub_type": EmergencySubTypeEnum.chemical_spill,
             "region": RegionEnum.nairobi, "location": "Industrial Area, Likoni Road",
             "latitude": -1.3100, "longitude": 36.8300, "county": "Nairobi",
             "caller_channel": CallerChannelEnum.phone,
             "casualty_count": 2, "hazard_present": True,
             "source": "Voice Call", "source_id": "call-fire-003",
             "team": "Nairobi Fire Brigade",
             "created_at": now - timedelta(minutes=1)},

            # MEDICAL alerts
            {"title": "Cardiac arrest — Westlands shopping mall",
             "description": "Elderly male collapsed in mall food court. Bystander performing CPR. AED requested.",
             "severity": SeverityEnum.critical, "status": StatusEnum.dispatching,
             "category": EmergencyCategoryEnum.medical, "sub_type": EmergencySubTypeEnum.cardiac,
             "region": RegionEnum.nairobi, "location": "Westgate Mall, Westlands",
             "latitude": -1.2633, "longitude": 36.8083, "county": "Nairobi",
             "caller_phone": "+254767890000", "caller_name": "Dr. Patel",
             "caller_channel": CallerChannelEnum.app,
             "casualty_count": 1, "entrapped": False, "hazard_present": False,
             "responder_type": ResponderTypeEnum.ambulance, "eta_minutes": 5.0,
             "source": "Ajali App", "source_id": "app-medical-001",
             "team": "Nairobi Ambulance Unit",
             "created_at": now - timedelta(minutes=3),
             "dispatched_at": now - timedelta(minutes=1)},

            {"title": "Maternity emergency — Kibera dispensary",
             "description": "Pregnant woman in distress — heavy bleeding. Dispensary requesting urgent ambulance transfer to Kenyatta Hospital.",
             "severity": SeverityEnum.high, "status": StatusEnum.en_route,
             "category": EmergencyCategoryEnum.medical, "sub_type": EmergencySubTypeEnum.maternity,
             "region": RegionEnum.nairobi, "location": "Kibera Dispensary, Gatwekera",
             "latitude": -1.3140, "longitude": 36.7860, "county": "Nairobi",
             "caller_phone": "+254778901000", "caller_channel": CallerChannelEnum.phone,
             "casualty_count": 1, "hazard_present": False,
             "responder_type": ResponderTypeEnum.ambulance, "eta_minutes": 7.0,
             "source": "Voice Call", "source_id": "call-medical-002",
             "team": "Nairobi Ambulance Unit",
             "created_at": now - timedelta(minutes=10),
             "acknowledged_at": now - timedelta(minutes=9),
             "response_time_seconds": 60,
             "dispatched_at": now - timedelta(minutes=8),
             "dispatch_time_seconds": 120},

            {"title": "Drowning — Lake Victoria, Kisumu",
             "description": "Fisherman's boat capsized. 2 people in water. Community rescue underway. Need emergency medical.",
             "severity": SeverityEnum.high, "status": StatusEnum.active,
             "category": EmergencyCategoryEnum.medical, "sub_type": EmergencySubTypeEnum.drowning,
             "region": RegionEnum.kisumu, "location": "Lake Victoria, Dunga Beach",
             "latitude": -0.1667, "longitude": 34.7500, "county": "Kisumu",
             "caller_channel": CallerChannelEnum.ussd,
             "casualty_count": 2, "hazard_present": False,
             "responder_type": ResponderTypeEnum.community_responder,
             "source": "USSD *1233#", "source_id": "ussd-medical-003",
             "team": "Ruai Community Responders",
             "created_at": now - timedelta(minutes=6)},

            # SECURITY alerts
            {"title": "Armed robbery — Eastleigh shopping center",
             "description": "3 armed men holding up a shop. Gunshots reported. Civilians sheltering inside adjacent buildings.",
             "severity": SeverityEnum.critical, "status": StatusEnum.dispatching,
             "category": EmergencyCategoryEnum.security, "sub_type": EmergencySubTypeEnum.robbery,
             "region": RegionEnum.nairobi, "location": "Eastleigh, 12th Street Shopping Center",
             "latitude": -1.2767, "longitude": 36.8550, "county": "Nairobi",
             "caller_phone": "+254789012000", "caller_channel": CallerChannelEnum.sms,
             "casualty_count": 0, "hazard_present": True,
             "responder_type": ResponderTypeEnum.police, "eta_minutes": 4.0,
             "source": "SMS Alert", "source_id": "sms-security-001",
             "team": "Nairobi Police Response",
             "created_at": now - timedelta(minutes=3),
             "dispatched_at": now - timedelta(minutes=1)},

            {"title": "Home invasion — Karen estate",
             "description": "Family reports intruders broke into home. Residents locked in bedroom. Requesting immediate police.",
             "severity": SeverityEnum.high, "status": StatusEnum.acknowledged,
             "category": EmergencyCategoryEnum.security, "sub_type": EmergencySubTypeEnum.home_invasion,
             "region": RegionEnum.nairobi, "location": "Karen, Nairobi",
             "latitude": -1.3350, "longitude": 36.6900, "county": "Nairobi",
             "caller_phone": "+254790123000", "caller_name": "Anonymous",
             "caller_channel": CallerChannelEnum.ussd,
             "casualty_count": 0, "hazard_present": False,
             "responder_type": ResponderTypeEnum.police, "eta_minutes": 8.0,
             "source": "USSD *1233#", "source_id": "ussd-security-002",
             "team": "Nairobi Police Response",
             "created_at": now - timedelta(minutes=7),
             "acknowledged_at": now - timedelta(minutes=6),
             "response_time_seconds": 60},

            {"title": "Civil unrest — Garissa town center",
             "description": "Protest turning violent — property being damaged. Shops closing. Community members requesting police presence.",
             "severity": SeverityEnum.medium, "status": StatusEnum.active,
             "category": EmergencyCategoryEnum.security, "sub_type": EmergencySubTypeEnum.civil_unrest,
             "region": RegionEnum.garissa, "location": "Garissa Town Center",
             "latitude": 0.4676, "longitude": 39.6583, "county": "Garissa",
             "caller_channel": CallerChannelEnum.phone,
             "casualty_count": 0, "hazard_present": False,
             "responder_type": ResponderTypeEnum.police,
             "source": "Voice Call", "source_id": "call-security-003",
             "team": "Nairobi Police Response",
             "created_at": now - timedelta(minutes=20)},

            # RESOLVED alerts
            {"title": "Fender bender — Waiyaki Way",
             "description": "Minor collision — no injuries. Both drivers exchanging details.",
             "severity": SeverityEnum.low, "status": StatusEnum.resolved,
             "category": EmergencyCategoryEnum.accident, "sub_type": EmergencySubTypeEnum.road_collision,
             "region": RegionEnum.nairobi, "location": "Waiyaki Way, Near ABC Place",
             "latitude": -1.2583, "longitude": 36.7917, "county": "Nairobi",
             "caller_channel": CallerChannelEnum.app,
             "casualty_count": 0, "entrapped": False, "hazard_present": False,
             "responder_type": ResponderTypeEnum.police,
             "source": "Ajali App", "source_id": "app-accident-004",
             "team": "Nairobi Police Response",
             "created_at": now - timedelta(minutes=35),
             "resolved_at": now - timedelta(minutes=28),
             "resolution_time_seconds": 420},

            {"title": "Small kitchen fire — Kahawa estate",
             "description": "Cooking oil fire — extinguished by neighbours before fire arrival.",
             "severity": SeverityEnum.low, "status": StatusEnum.resolved,
             "category": EmergencyCategoryEnum.fire, "sub_type": EmergencySubTypeEnum.structural_fire,
             "region": RegionEnum.nairobi, "location": "Kahawa West Estate, House 47",
             "latitude": -1.2050, "longitude": 36.9150, "county": "Nairobi",
             "caller_channel": CallerChannelEnum.ussd,
             "casualty_count": 0, "fire_severity": "small", "hazard_present": False,
             "responder_type": ResponderTypeEnum.fire_brigade,
             "source": "USSD *1233#", "source_id": "ussd-fire-004",
             "team": "Nairobi Fire Brigade",
             "created_at": now - timedelta(minutes=45),
             "resolved_at": now - timedelta(minutes=38),
             "resolution_time_seconds": 420},

            {"title": "Severe allergic reaction — Village Market",
             "description": "Child having anaphylactic reaction at restaurant. EpiPen administered. Needs hospital transfer.",
             "severity": SeverityEnum.medium, "status": StatusEnum.resolved,
             "category": EmergencyCategoryEnum.medical, "sub_type": EmergencySubTypeEnum.trauma,
             "region": RegionEnum.nairobi, "location": "Village Market, Gigiri",
             "latitude": -1.2500, "longitude": 36.8070, "county": "Nairobi",
             "caller_channel": CallerChannelEnum.app,
             "casualty_count": 1, "hazard_present": False,
             "responder_type": ResponderTypeEnum.ambulance,
             "source": "Ajali App", "source_id": "app-medical-004",
             "team": "Nairobi Ambulance Unit",
             "created_at": now - timedelta(minutes=25),
             "resolved_at": now - timedelta(minutes=18),
             "resolution_time_seconds": 420},
        ]

        # Check count before seeding
        existing_count = await db.execute(select(func.count(Alert.id)))
        if (existing_count.scalar() or 0) < 5:
            for a in alerts_data:
                alert = Alert(**a)
                db.add(alert)
            await db.commit()
            logger.info("Seeded %d sample emergency alerts", len(alerts_data))
        else:
            logger.info("Alerts already exist, skipping seed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed())
