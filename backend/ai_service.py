from __future__ import annotations

import os
from typing import Any, Dict, Optional


try:
    import openai
except Exception:  # pragma: no cover - optional dependency
    openai = None


class MockAIProvider:
    async def categorize_incident(self, description: str, location: str, incident_type_list: list[dict]) -> dict:
        text = (description or "").lower()
        for item in incident_type_list:
            code = item.get("code", "")
            if any(keyword in text for keyword in ["accident", "crash", "collision"]) and code == "road_accident":
                return {"suggested_type_id": item.get("id"), "confidence": 0.82, "alternative_types": []}
            if any(keyword in text for keyword in ["medical", "injury", "bleeding", "chest pain"]) and code == "medical":
                return {"suggested_type_id": item.get("id"), "confidence": 0.91, "alternative_types": []}
            if any(keyword in text for keyword in ["fire", "smoke", "burn"]) and code == "fire":
                return {"suggested_type_id": item.get("id"), "confidence": 0.9, "alternative_types": []}
            if any(keyword in text for keyword in ["theft", "robbery", "threat", "security"]) and code == "security":
                return {"suggested_type_id": item.get("id"), "confidence": 0.88, "alternative_types": []}
        fallback = incident_type_list[0] if incident_type_list else {} 
        return {"suggested_type_id": fallback.get("id"), "confidence": 0.5, "alternative_types": []}

    async def detect_duplicate(self, incident: Any, db: Any) -> Dict[str, Any]:
        return {"similar_incidents": [], "threshold": 0.8}

    async def hotspot_analysis(self, region_geojson: Dict, start_time: Any, end_time: Any, db: Any) -> Dict[str, Any]:
        return {"polygons": [], "intensity": 0.0, "time_range": (start_time, end_time)}

    async def demand_forecast(self, region_geojson: Dict, horizon_hours: int, db: Any) -> Dict[str, Any]:
        return {"predicted_incidents": [], "confidence_interval": (0.0, 0.0)}

    async def recommend_resources(self, incident: Any, db: Any) -> Dict[str, Any]:
        incident_type = getattr(getattr(incident, "type", None), "code", "other")
        equipment = ["trauma kit"]
        if incident_type == "fire":
            equipment = ["fire extinguisher", "breathing apparatus"]
        elif incident_type == "medical":
            equipment = ["defibrillator", "oxygen kit"]
        return {
            "recommended_responders": [],
            "recommended_vehicles": [],
            "recommended_equipment": equipment,
            "rationale": "Based on type and priority." 
        }

    async def summarize_report(self, incident: Any, db: Any) -> Dict[str, Any]:
        type_name = getattr(getattr(incident, "type", None), "name", "Emergency")
        return {
            "summary": f"{type_name} report recorded in {incident.location_description or 'the reported area'}.",
            "key_points": [f"Priority: {incident.priority}", f"Casualties: {incident.casualty_count}"]
        }

    async def check_completeness(self, incident: Any) -> Dict[str, Any]:
        missing = []
        if not getattr(incident, "location_description", ""):
            missing.append("location_description")
        if getattr(incident, "casualty_count", None) is None:
            missing.append("casualty_count")
        if not getattr(incident, "description", ""):
            missing.append("description")
        return {"missing_fields": missing, "suggested_questions": []}

    async def detect_anomaly(self, incident: Any, db: Any) -> Dict[str, Any]:
        return {
            "is_anomalous": False,
            "anomaly_type": "none",
            "explanation": "No unusual pattern detected.",
            "severity": "low",
        }

    def chat(
        self,
        message: str,
        incident_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_role: str = "citizen",
    ) -> str:
        text = (message or "").lower()
        context = context or {}
        status = context.get("status")
        priority = context.get("priority", "")
        incident_type = (context.get("type") or "emergency").lower()
        location = (context.get("location") or "the reported area").lower()
        description = (context.get("description") or "").lower()

        if ("status" in text or "summary" in text or "summarize" in text) and status:
            summary = (
                f"This case is currently {status}. "
                f"Priority is level {priority}. "
                f"Incident type: {incident_type}. "
                f"Location: {location}. "
            )
            if description:
                summary += f"Report notes: {description}."
            return summary

        if "status" in text and status:
            return f"This incident is currently in {status} status and priority level {priority}."

        if "fire" in text:
            return "For a fire emergency, move away from smoke and heat, call emergency services immediately, and if safe, evacuate the area. If someone is trapped, alert responders and keep a safe distance."

        if "medical" in text or "injury" in text:
            return "For a medical emergency, check for breathing and responsiveness, call emergency services, and keep the patient warm and still until responders arrive."

        if user_role == "dispatcher":
            return (
                "Dispatcher summary: I can prioritize resource assignment, flag missing details, "
                f"and confirm current status for this {incident_type} case in {location}. "
                "Please ask for a quick summary or dispatch guidance."
            )

        return "I can help with emergency reporting, live status checks, and general safety guidance. For immediate danger, call emergency services right away."


class OpenAIProvider:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def chat(
        self,
        message: str,
        incident_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_role: str = "citizen",
    ) -> str:
        if not self.api_key or openai is None:
            return MockAIProvider().chat(message, incident_id=incident_id, context=context, user_role=user_role)

        system_prompt = (
            "You are an emergency-response assistant for Ajali Alert. "
            "Reply briefly, calmly, and operationally. If there is a real incident, use the provided status, "
            "location, type, and description. Prioritize dispatch safety and triage: identify likely urgency, "
            "suggest the right responder type, ask for missing critical facts, and recommend immediate actions "
            "for the dispatcher. Keep guidance practical and do not offer unverified medical advice."
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self._build_contextual_prompt(message, incident_id, context, user_role)},
            ],
            "temperature": 0.3,
        }
        try:
            response = openai.OpenAI(api_key=self.api_key).chat.completions.create(**payload)
            return response.choices[0].message.content.strip() or "I’m not able to answer that right now."
        except Exception:
            return MockAIProvider().chat(message, incident_id=incident_id, context=context, user_role=user_role)

    def _build_contextual_prompt(
        self,
        message: str,
        incident_id: Optional[str],
        context: Optional[Dict[str, Any]],
        user_role: str,
    ) -> str:
        context = context or {}
        summary = (
            f"Incident ID: {incident_id or 'not provided'}\n"
            f"User role: {user_role}\n"
            f"Status: {context.get('status', 'unknown')}\n"
            f"Priority: {context.get('priority', 'unknown')}\n"
            f"Type: {context.get('type', 'unknown')}\n"
            f"Location: {context.get('location', 'unknown')}\n"
            f"Description: {context.get('description', 'unknown')}\n"
            f"Message: {message}"
        )
        return summary


def get_ai_provider() -> Any:
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"), model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    return MockAIProvider()
