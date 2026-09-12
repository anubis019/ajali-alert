from __future__ import annotations

"""
Ajali Alert - AI / Intelligence Provider

Production-oriented AI provider abstraction with:
- OpenAI integration with graceful fallback
- Deterministic local intelligence when no API key is available
- Incident classification and severity assessment
- Duplicate/similarity detection
- Completeness checks
- Resource recommendations
- Hotspot analysis
- Demand forecasting
- Basic anomaly detection
- Operational summaries
- Role-aware assistant
- Structured JSON AI responses
- No API key or sensitive payload logging

The provider intentionally does NOT "train" a model from incident data.
For internal intelligence, pass approved incident/intel context to the
analysis methods or connect them to the Ajali Alert database/retrieval layer.
"""

import asyncio
import json
import logging
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:
    import openai
except Exception:  # pragma: no cover
    openai = None

logger = logging.getLogger("ajali.ai")

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "30"))
DEFAULT_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
MAX_CONTEXT_CHARS = int(os.getenv("AI_MAX_CONTEXT_CHARS", "12000"))


# ---------------------------------------------------------------------------
# Structured result models
# ---------------------------------------------------------------------------

@dataclass
class IncidentAnalysis:
    incident_type: str = "other"
    severity: str = "medium"
    priority: int = 3
    confidence: float = 0.50
    summary: str = ""
    risks: List[str] | None = None
    recommended_actions: List[str] | None = None
    recommended_resources: List[str] | None = None
    missing_information: List[str] | None = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        for key, value in data.items():
            if value is None:
                data[key] = []
        return data


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _lower(value: Any) -> str:
    return _safe_text(value).lower()


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _get(obj: Any, *names: str, default: Any = None) -> Any:
    """Read an attribute from an object or a key from a dictionary."""
    if obj is None:
        return default

    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]

        try:
            value = getattr(obj, name)
        except Exception:
            value = None

        if value is not None:
            return value

    return default


def _type_code(incident: Any) -> str:
    incident_type = _get(incident, "type", default=None)
    return _lower(
        _get(
            incident,
            "incident_type",
            "type_code",
            default=_get(incident_type, "code", default="other"),
        )
    ) or "other"


def _type_name(incident: Any) -> str:
    incident_type = _get(incident, "type", default=None)
    return _safe_text(
        _get(
            incident,
            "incident_type_name",
            "type_name",
            default=_get(incident_type, "name", default="Emergency"),
        ),
        "Emergency",
    )


def _description(incident: Any) -> str:
    return _safe_text(_get(incident, "description", "details", "report", default=""))


def _location(incident: Any) -> str:
    return _safe_text(
        _get(
            incident,
            "location_description",
            "location",
            "address",
            default="",
        )
    )


def _casualties(incident: Any) -> int:
    value = _get(incident, "casualty_count", "casualties", "victims", default=0)
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _coordinates(obj: Any) -> tuple[Optional[float], Optional[float]]:
    lat = _get(obj, "latitude", "lat", default=None)
    lon = _get(obj, "longitude", "lng", "lon", default=None)
    try:
        lat_f = float(lat)
        lon_f = float(lon)
        if -90 <= lat_f <= 90 and -180 <= lon_f <= 180:
            return lat_f, lon_f
    except (TypeError, ValueError):
        pass
    return None, None


def _incident_text(incident: Any) -> str:
    return " ".join(
        x for x in [
            _type_name(incident),
            _type_code(incident),
            _description(incident),
            _location(incident),
        ]
        if x
    )


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", _lower(text)))


def _similarity(a: str, b: str) -> float:
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return SequenceMatcher(None, _lower(a), _lower(b)).ratio()

    jaccard = len(ta & tb) / max(1, len(ta | tb))
    sequence = SequenceMatcher(None, _lower(a), _lower(b)).ratio()
    return round(0.55 * jaccard + 0.45 * sequence, 3)


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance without external dependencies."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value

    if not value:
        return None

    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _incident_datetime(incident: Any) -> Optional[datetime]:
    return _parse_datetime(
        _get(
            incident,
            "created_at",
            "reported_at",
            "incident_time",
            "occurred_at",
            "timestamp",
            default=None,
        )
    )


def _json_safe(value: Any) -> Any:
    """Convert common ORM/Pydantic-ish values into JSON-safe primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]

    if hasattr(value, "model_dump"):
        try:
            return _json_safe(value.model_dump())
        except Exception:
            pass

    if hasattr(value, "dict"):
        try:
            return _json_safe(value.dict())
        except Exception:
            pass

    return _safe_text(value)


def _trim_payload(payload: Any, max_chars: int = MAX_CONTEXT_CHARS) -> Any:
    safe = _json_safe(payload)
    raw = json.dumps(safe, ensure_ascii=False, default=str)

    if len(raw) <= max_chars:
        return safe

    # Keep the beginning because it normally contains the primary incident.
    return raw[:max_chars] + "\n...[context truncated]"


# ---------------------------------------------------------------------------
# Local deterministic intelligence
# ---------------------------------------------------------------------------

class MockAIProvider:
    """
    Local intelligence provider.

    This is deliberately useful rather than an empty mock. It allows Ajali
    Alert to operate when OpenAI is disabled/unavailable and is suitable for
    development, testing and basic offline operation.
    """

    RULES = [
        ("fire", ["fire", "flames", "smoke", "burning", "burnt", "explosion"], 0.94),
        (
            "medical",
            [
                "medical",
                "unconscious",
                "not breathing",
                "chest pain",
                "stroke",
                "seizure",
                "bleeding",
                "injury",
                "fainted",
            ],
            0.93,
        ),
        (
            "road_accident",
            ["accident", "crash", "collision", "overturned", "vehicle hit", "road crash"],
            0.92,
        ),
        (
            "security",
            ["robbery", "theft", "attack", "assault", "threat", "intruder", "break in"],
            0.90,
        ),
        (
            "flood",
            ["flood", "flooding", "water level", "washed away", "overflow"],
            0.90,
        ),
        (
            "hazard",
            ["gas leak", "chemical", "hazard", "toxic", "spill"],
            0.88,
        ),
    ]

    RESOURCE_MAP = {
        "fire": ["fire response unit", "fire extinguisher", "breathing apparatus"],
        "medical": ["ambulance", "paramedic team", "first-aid/trauma kit", "oxygen"],
        "road_accident": [
            "ambulance",
            "traffic/police support",
            "extrication tools",
            "trauma kit",
        ],
        "security": ["security/police unit", "patrol vehicle", "communications support"],
        "flood": ["rescue team", "rescue vehicle/boat where appropriate", "first-aid kit"],
        "hazard": ["hazmat-capable team", "protective equipment", "isolation/barrier equipment"],
        "other": ["assessment/responder unit", "first-aid kit"],
    }

    def _classify_text(self, text: str) -> tuple[str, float, List[str]]:
        text = _lower(text)
        scores: List[tuple[str, int, float]] = []

        for code, keywords, base_confidence in self.RULES:
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches:
                score = matches * base_confidence
                scores.append((code, matches, score))

        if not scores:
            return "other", 0.50, []

        scores.sort(key=lambda item: (item[1], item[2]), reverse=True)
        code, matches, score = scores[0]
        confidence = _clamp(0.65 + 0.07 * matches, 0.65, base_confidence)
        alternatives = [item[0] for item in scores[1:3]]
        return code, round(confidence, 2), alternatives

    def _severity(self, text: str, casualties: int = 0) -> tuple[str, int]:
        text = _lower(text)

        critical_words = (
            "not breathing",
            "unconscious",
            "trapped",
            "multiple casualties",
            "explosion",
            "building collapse",
            "active attack",
            "mass casualty",
        )

        high_words = (
            "severe bleeding",
            "heavy bleeding",
            "fire",
            "spreading",
            "serious injury",
            "armed",
            "collapsed",
        )

        if casualties >= 5 or any(k in text for k in critical_words):
            return "critical", 1
        if casualties >= 2 or any(k in text for k in high_words):
            return "high", 2
        if casualties == 1:
            return "high", 2
        if text:
            return "medium", 3
        return "low", 4

    async def analyze_incident(
        self,
        incident: Any,
        incident_type_list: Optional[list[dict]] = None,
    ) -> Dict[str, Any]:
        text = _incident_text(incident)
        code, confidence, alternatives = self._classify_text(text)
        severity, priority = self._severity(text, _casualties(incident))

        incident_type_list = incident_type_list or []
        matched = next(
            (x for x in incident_type_list if _lower(x.get("code")) == code),
            None,
        )

        missing = await self.check_completeness(incident)
        resources = self.RESOURCE_MAP.get(code, self.RESOURCE_MAP["other"])

        risks = []
        if severity in {"critical", "high"}:
            risks.append("Responder and public safety risk is elevated.")
        if not _location(incident):
            risks.append("Response may be delayed because the location is incomplete.")
        if _casualties(incident) > 0:
            risks.append("Casualty information should be verified by responders.")

        return IncidentAnalysis(
            incident_type=code,
            severity=severity,
            priority=priority,
            confidence=confidence,
            summary=f"Likely {code.replace('_', ' ')} incident assessed at {severity} severity.",
            risks=risks,
            recommended_actions=[
                "Verify the exact location.",
                "Confirm immediate threats and casualty count.",
                "Dispatch the appropriate response unit according to operational protocol.",
            ],
            recommended_resources=resources,
            missing_information=missing.get("missing_fields", []),
        ).to_dict() | {
            "suggested_type_id": matched.get("id") if matched else None,
            "alternative_types": alternatives,
        }

    async def categorize_incident(
        self,
        description: str,
        location: str,
        incident_type_list: list[dict],
    ) -> dict:
        text = f"{description or ''} {location or ''}"
        code, confidence, alternatives = self._classify_text(text)

        match = next(
            (i for i in incident_type_list if _lower(i.get("code")) == code),
            None,
        )

        if match is None and incident_type_list:
            # Never invent an ID.
            match = incident_type_list[0]
            confidence = min(confidence, 0.50)

        return {
            "suggested_type_id": match.get("id") if match else None,
            "suggested_type_code": code,
            "confidence": confidence,
            "alternative_types": alternatives,
        }

    async def assess_priority(self, incident: Any) -> Dict[str, Any]:
        severity, priority = self._severity(
            _incident_text(incident),
            _casualties(incident),
        )
        return {
            "priority": priority,
            "severity": severity,
            "confidence": 0.82,
            "rationale": "Priority estimated from incident type, reported keywords and casualty count.",
        }

    async def check_completeness(self, incident: Any) -> Dict[str, Any]:
        missing: List[str] = []
        questions: List[str] = []

        if not _location(incident):
            missing.append("location_description")
            questions.append("What is the exact location, landmark or address?")
        if not _description(incident):
            missing.append("description")
            questions.append("What happened and what is the current danger?")
        if _get(incident, "casualty_count", "casualties", default=None) is None:
            missing.append("casualty_count")
            questions.append("How many people are injured, trapped or affected?")
        lat, lon = _coordinates(incident)
        if lat is None or lon is None:
            missing.append("coordinates")
            questions.append("Can the location be shared using GPS coordinates?")

        return {
            "complete": not missing,
            "missing_fields": missing,
            "suggested_questions": questions,
        }

    async def detect_duplicate(self, incident: Any, db: Any) -> Dict[str, Any]:
        candidates = await _fetch_incidents(db)
        current_text = _incident_text(incident)
        current_lat, current_lon = _coordinates(incident)
        threshold = float(os.getenv("AI_DUPLICATE_THRESHOLD", "0.72"))

        results = []

        for candidate in candidates:
            if candidate is incident:
                continue

            similarity = _similarity(current_text, _incident_text(candidate))

            c_lat, c_lon = _coordinates(candidate)
            distance = None
            if (
                current_lat is not None
                and current_lon is not None
                and c_lat is not None
                and c_lon is not None
            ):
                distance = _distance_km(
                    current_lat, current_lon, c_lat, c_lon
                )

                # Nearby incidents receive a modest similarity boost.
                if distance <= 0.5:
                    similarity = min(1.0, similarity + 0.10)
                elif distance <= 2:
                    similarity = min(1.0, similarity + 0.04)

            if similarity >= threshold:
                results.append(
                    {
                        "incident_id": _get(candidate, "id", default=None),
                        "similarity": round(similarity, 3),
                        "distance_km": round(distance, 3) if distance is not None else None,
                        "type": _type_code(candidate),
                    }
                )

        results.sort(key=lambda x: x["similarity"], reverse=True)

        return {
            "similar_incidents": results[:20],
            "threshold": threshold,
        }

    async def hotspot_analysis(
        self,
        region_geojson: Dict,
        start_time: Any,
        end_time: Any,
        db: Any,
    ) -> Dict[str, Any]:
        incidents = await _fetch_incidents(db)
        start = _parse_datetime(start_time)
        end = _parse_datetime(end_time)

        filtered = []
        for incident in incidents:
            timestamp = _incident_datetime(incident)
            if start and timestamp and timestamp < start:
                continue
            if end and timestamp and timestamp > end:
                continue

            lat, lon = _coordinates(incident)
            if lat is None or lon is None:
                continue

            filtered.append(incident)

        # Approximate grid cells. 0.01 degrees is roughly ~1 km in latitude.
        grid_size = float(os.getenv("AI_HOTSPOT_GRID", "0.01"))
        cells: Dict[tuple[int, int], List[Any]] = defaultdict(list)

        for incident in filtered:
            lat, lon = _coordinates(incident)
            key = (
                math.floor(lat / grid_size),
                math.floor(lon / grid_size),
            )
            cells[key].append(incident)

        max_count = max((len(v) for v in cells.values()), default=0)
        hotspots = []

        for (lat_cell, lon_cell), cell_incidents in cells.items():
            count = len(cell_incidents)
            center_lat = (lat_cell + 0.5) * grid_size
            center_lon = (lon_cell + 0.5) * grid_size
            severity_values = []

            for incident in cell_incidents:
                severity, _ = self._severity(
                    _incident_text(incident),
                    _casualties(incident),
                )
                severity_values.append(
                    {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(severity, 1)
                )

            intensity = round(
                (count / max_count) * mean(severity_values) / 4
                if max_count else 0,
                3,
            )

            hotspots.append(
                {
                    "latitude": round(center_lat, 6),
                    "longitude": round(center_lon, 6),
                    "incident_count": count,
                    "intensity": intensity,
                    "average_severity_score": round(mean(severity_values), 2),
                }
            )

        hotspots.sort(key=lambda x: x["intensity"], reverse=True)

        return {
            "polygons": hotspots,
            "intensity": max((x["intensity"] for x in hotspots), default=0.0),
            "incident_count": len(filtered),
            "time_range": (start_time, end_time),
        }

    async def demand_forecast(
        self,
        region_geojson: Dict,
        horizon_hours: int,
        db: Any,
    ) -> Dict[str, Any]:
        incidents = await _fetch_incidents(db)
        now = datetime.now()
        hours = max(1, int(horizon_hours))

        counts = [0] * 24
        for incident in incidents:
            dt = _incident_datetime(incident)
            if not dt:
                continue

            age = (now - dt.replace(tzinfo=None)).total_seconds() / 3600
            if 0 <= age < 24:
                counts[int(age)] += 1

        baseline = mean(counts) if counts else 0.0

        # Simple weighted trend: recent hours matter more.
        weights = list(range(1, len(counts) + 1))
        weighted_avg = (
            sum(c * w for c, w in zip(reversed(counts), weights))
            / sum(weights)
            if counts
            else baseline
        )

        predicted_rate = max(0.0, weighted_avg)
        predictions = [
            {
                "hours_ahead": h,
                "predicted_incidents": round(predicted_rate, 2),
            }
            for h in range(1, hours + 1)
        ]

        spread = pstdev(counts) if len(counts) > 1 else 0.0

        return {
            "predicted_incidents": predictions,
            "confidence_interval": (
                round(max(0.0, predicted_rate - spread), 2),
                round(predicted_rate + spread, 2),
            ),
            "baseline_hourly_rate": round(baseline, 2),
            "method": "local weighted moving average",
        }

    async def recommend_resources(self, incident: Any, db: Any) -> Dict[str, Any]:
        code = _type_code(incident)
        severity, priority = self._severity(
            _incident_text(incident),
            _casualties(incident),
        )

        resources = list(self.RESOURCE_MAP.get(code, self.RESOURCE_MAP["other"]))

        if severity == "critical":
            resources.insert(0, "senior incident commander / supervisor")
        if _casualties(incident) >= 2 and "ambulance" not in resources:
            resources.insert(0, "additional medical/ambulance support")

        return {
            "recommended_responders": resources[:5],
            "recommended_vehicles": [],
            "recommended_equipment": resources,
            "priority": priority,
            "severity": severity,
            "rationale": (
                f"Recommendations are based on incident type '{code}', "
                f"severity '{severity}', and reported casualties."
            ),
        }

    async def summarize_report(self, incident: Any, db: Any) -> Dict[str, Any]:
        severity, priority = self._severity(
            _incident_text(incident),
            _casualties(incident),
        )

        summary = (
            f"{_type_name(incident)} reported at "
            f"{_location(incident) or 'an unspecified location'}. "
            f"Current local assessment: {severity} severity, priority {priority}."
        )

        key_points = [
            f"Incident type: {_type_name(incident)}",
            f"Priority: {priority}",
            f"Severity: {severity}",
            f"Casualties: {_casualties(incident)}",
        ]

        if _description(incident):
            key_points.append(f"Description: {_description(incident)[:500]}")

        return {
            "summary": summary,
            "key_points": key_points,
        }

    async def detect_anomaly(self, incident: Any, db: Any) -> Dict[str, Any]:
        incidents = await _fetch_incidents(db)
        now = datetime.now()

        hourly = Counter()
        for item in incidents:
            dt = _incident_datetime(item)
            if dt:
                age = (now - dt.replace(tzinfo=None)).total_seconds() / 3600
                if 0 <= age <= 24 * 7:
                    hourly[dt.replace(minute=0, second=0, microsecond=0)] += 1

        values = list(hourly.values())
        if len(values) < 4:
            return {
                "is_anomalous": False,
                "anomaly_type": "insufficient_baseline",
                "explanation": "Not enough historical data to establish a reliable pattern.",
                "severity": "low",
            }

        current_dt = _incident_datetime(incident)
        current_bucket = (
            current_dt.replace(minute=0, second=0, microsecond=0)
            if current_dt
            else now.replace(minute=0, second=0, microsecond=0)
        )
        current_count = hourly.get(current_bucket, 1)

        avg = mean(values)
        sd = pstdev(values)

        if sd == 0:
            anomalous = current_count > avg * 2 and current_count >= 3
            z = 0.0
        else:
            z = (current_count - avg) / sd
            anomalous = z >= 2.0

        return {
            "is_anomalous": anomalous,
            "anomaly_type": "incident_surge" if anomalous else "none",
            "explanation": (
                f"Current hourly count is {current_count}; baseline mean is "
                f"{avg:.2f} with standard deviation {sd:.2f}."
            ),
            "severity": "high" if anomalous else "low",
            "z_score": round(z, 2),
        }

    async def chat(
        self,
        message: str,
        incident_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_role: str = "citizen",
    ) -> str:
        text = _lower(message)
        context = context or {}

        status = _safe_text(context.get("status"))
        priority = _safe_text(context.get("priority"), "unknown")
        incident_type = _safe_text(context.get("type"), "emergency")
        location = _safe_text(context.get("location"), "the reported area")
        description = _safe_text(context.get("description"))

        if any(k in text for k in ("status", "summary", "summarize", "update")):
            if status:
                result = (
                    f"This case is currently {status}. Priority is {priority}. "
                    f"Incident type: {incident_type}. Location: {location}."
                )
                if description:
                    result += f" Report notes: {description}."
                return result
            return "No incident status is available. Select an incident or provide an incident ID."

        if any(k in text for k in ("what should i do", "what do i do", "help", "immediate")):
            if "fire" in text or "fire" in incident_type.lower():
                return (
                    "Move away from smoke and heat, evacuate if safe, alert people nearby, "
                    "and contact emergency responders. Do not re-enter an unsafe building."
                )
            if any(k in text for k in ("medical", "injury", "bleeding")):
                return (
                    "Contact emergency responders, check responsiveness and breathing if "
                    "safe to do so, control severe bleeding with direct pressure when appropriate, "
                    "and follow dispatcher instructions."
                )
            if any(k in text for k in ("accident", "crash", "collision")):
                return (
                    "Keep yourself away from traffic and other hazards, warn approaching traffic "
                    "if safe, contact responders, and avoid moving injured people unless there is "
                    "immediate danger."
                )

        if user_role in {"dispatcher", "supervisor", "admin"}:
            return (
                f"Operational assistant ready for incident {incident_id or 'selection'}. "
                "I can assess priority, identify missing information, compare similar incidents, "
                "recommend resources and summarize the case."
            )

        return (
            "I can assist with emergency reporting, incident status, classification and "
            "general safety guidance. For immediate danger, contact emergency services."
        )


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

async def _fetch_incidents(db: Any) -> List[Any]:
    """
    Best-effort adapter for common DB/session shapes.

    If your SQLAlchemy repository already has a dedicated incident service,
    pass that data to the intelligence methods instead. This helper does not
    assume a specific Ajali Alert ORM schema.
    """
    if db is None:
        return []

    # Custom repository/service adapters.
    for method_name in ("get_incidents", "list_incidents", "fetch_incidents"):
        method = getattr(db, method_name, None)
        if callable(method):
            try:
                result = method()
                if asyncio.iscoroutine(result):
                    result = await result
                return list(result or [])
            except Exception as exc:
                logger.debug("Incident adapter %s failed: %s", method_name, type(exc).__name__)

    # SQLAlchemy AsyncSession: only use if an Incident model has been attached
    # to the session by the application. We intentionally avoid importing an
    # application-specific model here.
    return []


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

class OpenAIProvider(MockAIProvider):
    """
    OpenAI-backed provider with local fallback.

    Subclassing MockAIProvider keeps every feature available if the AI API
    becomes unavailable.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
        self.timeout = timeout or DEFAULT_TIMEOUT
        self.max_retries = (
            DEFAULT_MAX_RETRIES if max_retries is None else max(0, max_retries)
        )
        self._client = None
        self._fallback = MockAIProvider()

    def _get_client(self):
        if self._client is None and self.api_key and openai is not None:
            try:
                self._client = openai.OpenAI(
                    api_key=self.api_key,
                    timeout=self.timeout,
                    max_retries=0,
                )
            except TypeError:
                # Compatibility with older OpenAI SDKs.
                self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    @staticmethod
    def _extract_json(content: str) -> Dict[str, Any]:
        text = (content or "").strip()

        # Markdown fenced JSON.
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)

        try:
            value = json.loads(text)
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            pass

        # Recover the first JSON object from a mixed response.
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                value = json.loads(text[start : end + 1])
                return value if isinstance(value, dict) else {}
            except json.JSONDecodeError:
                pass

        return {}

    def _chat_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> Optional[str]:
        client = self._get_client()
        if client is None:
            return None

        for attempt in range(self.max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                )
                return (
                    response.choices[0].message.content or ""
                ).strip()
            except Exception as exc:
                if attempt >= self.max_retries:
                    logger.warning(
                        "AI request failed after %d attempts: %s",
                        attempt + 1,
                        type(exc).__name__,
                    )
                    return None

                delay = 0.75 * (2**attempt)
                logger.info("AI request retrying in %.2fs", delay)
                # This function is synchronous, so use a short blocking sleep
                # only for the retry delay.
                import time
                time.sleep(delay)

        return None

    def _chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        schema_instruction = (
            "\nReturn ONLY valid JSON. Do not use Markdown. "
            "Do not include facts that are not present in the supplied context. "
            "If uncertain, use an empty list or a conservative confidence value."
        )

        content = self._chat_text(
            system_prompt + schema_instruction,
            user_prompt,
            temperature=0.1,
        )
        return self._extract_json(content or "")

    async def analyze_incident(
        self,
        incident: Any,
        incident_type_list: Optional[list[dict]] = None,
    ) -> Dict[str, Any]:
        fallback = await self._fallback.analyze_incident(
            incident,
            incident_type_list,
        )

        if not self.api_key or self._get_client() is None:
            return fallback

        payload = {
            "incident": {
                "id": _get(incident, "id", default=None),
                "type": _type_code(incident),
                "description": _description(incident),
                "location": _location(incident),
                "casualties": _casualties(incident),
                "priority": _get(incident, "priority", default=None),
                "status": _get(incident, "status", default=None),
            },
            "allowed_types": incident_type_list or [],
            "local_assessment": fallback,
        }

        system = (
            "You are Ajali Alert Intelligence Engine. Analyze emergency incidents "
            "for trained dispatch and supervisory staff. Be conservative: never invent "
            "location, casualties, resources, identities or operational facts. "
            "Use the local assessment as a baseline, not as unquestionable truth."
        )

        user = _trim_payload(payload)
        result = self._chat_json(
            system,
            (
                "Assess this incident and return JSON with exactly these useful fields: "
                "incident_type, severity, priority, confidence, summary, risks, "
                "recommended_actions, recommended_resources, missing_information."
                f"\n\nContext:\n{json.dumps(user, ensure_ascii=False, default=str)}"
            ),
        )

        if not result:
            return fallback

        return self._merge_analysis(fallback, result)

    @staticmethod
    def _merge_analysis(
        fallback: Dict[str, Any],
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        output = dict(fallback)

        if result.get("incident_type"):
            output["incident_type"] = _safe_text(result["incident_type"])
        if result.get("severity") in {"critical", "high", "medium", "low"}:
            output["severity"] = result["severity"]

        try:
            output["priority"] = int(result.get("priority", output["priority"]))
            output["priority"] = max(1, min(5, output["priority"]))
        except (TypeError, ValueError):
            pass

        try:
            output["confidence"] = round(
                _clamp(float(result.get("confidence", output["confidence"])), 0, 1),
                2,
            )
        except (TypeError, ValueError):
            pass

        for key in (
            "summary",
            "risks",
            "recommended_actions",
            "recommended_resources",
            "missing_information",
        ):
            if key in result:
                value = result[key]
                if key == "summary":
                    output[key] = _safe_text(value)
                elif isinstance(value, list):
                    output[key] = [_safe_text(v) for v in value if _safe_text(v)]

        return output

    async def categorize_incident(
        self,
        description: str,
        location: str,
        incident_type_list: list[dict],
    ) -> dict:
        fallback = await self._fallback.categorize_incident(
            description,
            location,
            incident_type_list,
        )

        if not self.api_key or self._get_client() is None:
            return fallback

        result = self._chat_json(
            (
                "You classify emergency incident reports for Ajali Alert. "
                "Select only one type from the supplied allowed types. "
                "Never invent an ID. Return confidence from 0 to 1."
            ),
            (
                "Return JSON with: suggested_type_id, suggested_type_code, "
                "confidence, alternative_types.\n\n"
                f"Description: {description}\n"
                f"Location: {location}\n"
                f"Allowed types: {json.dumps(incident_type_list, default=str)}"
            ),
        )

        if not result:
            return fallback

        allowed_ids = {
            str(item.get("id"))
            for item in incident_type_list
            if item.get("id") is not None
        }

        suggested_id = result.get("suggested_type_id")
        if suggested_id is not None and str(suggested_id) not in allowed_ids:
            result["suggested_type_id"] = fallback.get("suggested_type_id")

        try:
            result["confidence"] = round(
                _clamp(float(result.get("confidence", fallback["confidence"])), 0, 1),
                2,
            )
        except (TypeError, ValueError):
            result["confidence"] = fallback["confidence"]

        return {**fallback, **result}

    async def recommend_resources(self, incident: Any, db: Any) -> Dict[str, Any]:
        fallback = await self._fallback.recommend_resources(incident, db)

        if not self.api_key or self._get_client() is None:
            return fallback

        result = self._chat_json(
            (
                "You are a dispatch resource recommendation assistant. "
                "Recommend resource categories only. Do not invent the existence "
                "or availability of specific vehicles, responders or equipment."
            ),
            (
                "Return JSON with recommended_responders, recommended_vehicles, "
                "recommended_equipment and rationale.\n\n"
                f"Incident: {json.dumps(_trim_payload(_json_safe(incident)), default=str)}\n"
                f"Local baseline: {json.dumps(fallback, default=str)}"
            ),
        )

        if not result:
            return fallback

        for key in (
            "recommended_responders",
            "recommended_vehicles",
            "recommended_equipment",
        ):
            if not isinstance(result.get(key), list):
                result[key] = fallback[key]

        result["rationale"] = _safe_text(
            result.get("rationale"),
            fallback["rationale"],
        )
        return {**fallback, **result}

    async def summarize_report(self, incident: Any, db: Any) -> Dict[str, Any]:
        fallback = await self._fallback.summarize_report(incident, db)

        if not self.api_key or self._get_client() is None:
            return fallback

        result = self._chat_json(
            (
                "Summarize an Ajali Alert incident for an operational dashboard. "
                "Use only supplied facts. Do not speculate or expose unnecessary "
                "personal information."
            ),
            (
                "Return JSON with summary and key_points.\n\n"
                f"Incident: {json.dumps(_trim_payload(_json_safe(incident)), default=str)}"
            ),
        )

        if not result:
            return fallback

        if not isinstance(result.get("key_points"), list):
            result["key_points"] = fallback["key_points"]

        result["summary"] = _safe_text(result.get("summary"), fallback["summary"])
        return {**fallback, **result}

    def chat(
        self,
        message: str,
        incident_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_role: str = "citizen",
    ) -> str:
        fallback = self._fallback.chat(
            message,
            incident_id=incident_id,
            context=context,
            user_role=user_role,
        )

        if not self.api_key or self._get_client() is None:
            return fallback

        system_prompt = (
            "You are Hermes, the Ajali Alert operational AI assistant. "
            "You assist authorized users with emergency incident workflows. "
            "Use only supplied context. Do not claim to have dispatched units, "
            "contacted authorities, accessed hidden databases, or verified facts "
            "unless the application explicitly provides that result. "
            "For citizens, give concise general safety guidance and encourage "
            "contacting emergency services for immediate danger. "
            "For dispatchers and supervisors, focus on triage, missing data, "
            "incident status and resource categories."
        )

        payload = {
            "incident_id": incident_id,
            "user_role": user_role,
            "context": context or {},
            "message": message,
        }

        response = self._chat_text(
            system_prompt,
            (
                "Answer the user's message using this context. "
                "Keep the response concise and actionable.\n\n"
                f"{json.dumps(_trim_payload(payload), ensure_ascii=False, default=str)}"
            ),
            temperature=0.2,
        )

        return response or fallback


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def get_ai_provider() -> Any:
    """
    Select OpenAI when configured, otherwise use local intelligence.

    Environment variables:
      OPENAI_API_KEY
      OPENAI_MODEL
      OPENAI_TIMEOUT
      OPENAI_MAX_RETRIES
      AI_DUPLICATE_THRESHOLD
      AI_HOTSPOT_GRID
    """
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key and openai is not None:
        return OpenAIProvider(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL"),
        )

    if not api_key:
        logger.info("OPENAI_API_KEY not configured; using local AI provider.")
    elif openai is None:
        logger.warning("OpenAI SDK unavailable; using local AI provider.")

    return MockAIProvider()


__all__ = [
    "IncidentAnalysis",
    "MockAIProvider",
    "OpenAIProvider",
    "get_ai_provider",
]
