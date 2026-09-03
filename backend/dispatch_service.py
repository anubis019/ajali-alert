import math
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_WEIGHTS = {
    "distance": 0.30,
    "availability": 0.20,
    "capability": 0.20,
    "equipment": 0.10,
    "workload": 0.10,
    "priority_bonus": 0.10,
}


class DispatchService:
    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        instance.weights = {**DEFAULT_WEIGHTS}
        return instance

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = {**DEFAULT_WEIGHTS, **(weights or {})}

    @staticmethod
    def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
        )
        return 2 * r * math.asin(math.sqrt(a))

    def estimate_eta(self, responder: Any, incident: Any, traffic_factor: float = 1.0) -> Tuple[int, float]:
        distance_km = self.haversine_km(
            incident.latitude,
            incident.longitude,
            responder.latitude,
            responder.longitude,
        )
        speed_kmh = {
            "ambulance": 45.0,
            "police": 50.0,
            "fire": 35.0,
            "community": 30.0,
        }.get(getattr(responder, "responder_type", "community"), 35.0)

        effective_speed = speed_kmh / traffic_factor
        eta_seconds = (distance_km / effective_speed) * 3600
        eta_seconds = max(eta_seconds, 30)
        return int(eta_seconds), distance_km

    def score_responder(
        self,
        incident: Any,
        responder: Any,
        traffic_factor: float = 1.0,
    ) -> Dict[str, Any]:
        eta_seconds, distance_km = self.estimate_eta(responder, incident, traffic_factor)
        max_dist = 25.0
        distance_score = max(0, 100 - (distance_km / max_dist) * 100)
        distance_score = min(100, distance_score)

        availability_map = {
            "AVAILABLE": 100,
            "ACKNOWLEDGED": 70,
            "ASSIGNED": 40,
            "EN_ROUTE": 20,
            "ON_SCENE": 10,
            "TRANSPORTING": 5,
            "AT_HOSPITAL": 0,
            "OFFLINE": 0,
            "UNAVAILABLE": 0,
        }
        availability_score = availability_map.get(getattr(responder, "status", "UNAVAILABLE"), 0)

        incident_type = getattr(incident, "type", None)
        incident_code = getattr(incident_type, "code", None)
        responder_capabilities = getattr(responder, "capabilities", []) or []
        capability_score = 100 if incident_code and incident_code in responder_capabilities else 50

        equipment_score = 100 if getattr(getattr(responder, "vehicle", None), "equipment", None) else 80

        active_assignments = 0
        workload_score = max(0, 100 - (active_assignments * 25))

        priority_bonus = 20 * (incident.priority - 3) if getattr(incident, "priority", 0) >= 4 else 0

        breakdown = {
            "distance": {
                "raw": round(distance_score, 2),
                "weighted": round(distance_score * self.weights["distance"], 2),
                "distance_km": round(distance_km, 2),
                "eta_seconds": eta_seconds,
            },
            "availability": {
                "raw": availability_score,
                "weighted": round(availability_score * self.weights["availability"], 2),
                "status": getattr(responder, "status", "UNAVAILABLE"),
            },
            "capability": {
                "raw": capability_score,
                "weighted": round(capability_score * self.weights["capability"], 2),
                "match": capability_score == 100,
            },
            "equipment": {
                "raw": equipment_score,
                "weighted": round(equipment_score * self.weights["equipment"], 2),
                "equipped": equipment_score == 100,
            },
            "workload": {
                "raw": workload_score,
                "weighted": round(workload_score * self.weights["workload"], 2),
                "active_assignments": active_assignments,
            },
            "priority_bonus": {
                "raw": priority_bonus,
                "weighted": round(priority_bonus * self.weights["priority_bonus"], 2),
                "incident_priority": incident.priority,
            },
        }

        total = (
            distance_score * self.weights["distance"]
            + availability_score * self.weights["availability"]
            + capability_score * self.weights["capability"]
            + equipment_score * self.weights["equipment"]
            + workload_score * self.weights["workload"]
            + priority_bonus * self.weights["priority_bonus"]
        )

        total = max(0, min(100, total))
        breakdown["total"] = round(total, 2)

        return {
            "score": round(total, 2),
            "breakdown": breakdown,
            "eta_seconds": eta_seconds,
            "distance_km": round(distance_km, 2),
            "responder": responder,
        }
