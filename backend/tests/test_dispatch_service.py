from datetime import datetime

from dispatch_service import DispatchService


def test_recommendations_rank_closer_viable_responder():
    incident = type(
        "Incident",
        (),
        {
            "id": "inc-1",
            "incident_number": "AJL-2026-000001",
            "priority": 4,
            "description": "Car crash with injuries",
            "latitude": -1.2864,
            "longitude": 36.8172,
            "type": type("Type", (), {"code": "medical"})(),
        },
    )

    responder_a = type(
        "Responder",
        (),
        {
            "id": "r1",
            "responder_type": "ambulance",
            "status": "AVAILABLE",
            "latitude": -1.2833,
            "longitude": 36.8167,
            "capabilities": ["medical"],
            "vehicle": type("Vehicle", (), {"equipment": ["oxygen", "defibrillator"]})(),
        },
    )

    responder_b = type(
        "Responder",
        (),
        {
            "id": "r2",
            "responder_type": "police",
            "status": "AVAILABLE",
            "latitude": -1.3100,
            "longitude": 36.8500,
            "capabilities": ["security"],
            "vehicle": type("Vehicle", (), {"equipment": []})(),
        },
    )

    service = DispatchService.__new__(DispatchService)
    score_a = service.score_responder(incident, responder_a)
    score_b = service.score_responder(incident, responder_b)

    assert score_a["score"] > score_b["score"]
