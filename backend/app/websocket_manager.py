import asyncio
import json
import logging
from typing import Dict, Set, List, Optional
from fastapi import WebSocket

logger = logging.getLogger("ajali.ws")


class ConnectionManager:
    """Manages WebSocket connections for real-time alert streaming."""

    def __init__(self):
        # {user_id: {ws1, ws2, ...}}
        self._connections: Dict[int, Set[WebSocket]] = {}
        # Subscriptions: {ws: {"severities": set, "categories": set, "regions": set}}
        self._subscriptions: Dict[WebSocket, dict] = {}

    def connect(self, ws: WebSocket, user_id: int):
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(ws)
        self._subscriptions[ws] = {
            "severities": set(),
            "categories": set(),
            "regions": set(),
        }
        logger.info("WS connected user=%d", user_id)

    def disconnect(self, ws: WebSocket, user_id: int):
        if user_id in self._connections:
            self._connections[user_id].discard(ws)
            if not self._connections[user_id]:
                del self._connections[user_id]
        self._subscriptions.pop(ws, None)
        logger.info("WS disconnected user=%d", user_id)

    def subscribe(self, ws: WebSocket, severities: Optional[List[str]] = None,
                  categories: Optional[List[str]] = None,
                  regions: Optional[List[str]] = None):
        sub = self._subscriptions.get(ws, {})
        if severities:
            sub["severities"] = set(severities)
        if categories:
            sub["categories"] = set(categories)
        if regions:
            sub["regions"] = set(regions)

    def _matches_subscription(self, ws: WebSocket, alert_data: dict) -> bool:
        sub = self._subscriptions.get(ws)
        if not sub:
            return True  # no filter = receive everything
        sev = alert_data.get("severity", "")
        cat = alert_data.get("category", "")
        reg = alert_data.get("region", "")

        if sub["severities"] and sev not in sub["severities"]:
            return False
        if sub["categories"] and cat not in sub["categories"]:
            return False
        if sub["regions"] and reg not in sub["regions"]:
            return False
        return True

    async def broadcast_alert(self, alert_data: dict):
        """Push an alert dict to all connected clients matching their subscriptions."""
        message = json.dumps({"type": "new_alert", "data": alert_data})
        stale = []
        for user_id, sockets in self._connections.items():
            for ws in sockets:
                try:
                    if self._matches_subscription(ws, alert_data):
                        await ws.send_text(message)
                except Exception:
                    stale.append((user_id, ws))
        for uid, ws in stale:
            self.disconnect(ws, uid)

    async def broadcast_event(self, event_type: str, data: dict):
        """Broadcast status change events (acknowledge, resolve, escalate)."""
        message = json.dumps({"type": event_type, "data": data})
        stale = []
        for user_id, sockets in self._connections.items():
            for ws in sockets:
                try:
                    await ws.send_text(message)
                except Exception:
                    stale.append((user_id, ws))
        for uid, ws in stale:
            self.disconnect(ws, uid)

    @property
    def active_connections(self) -> int:
        return sum(len(s) for s in self._connections.values())


# Singleton instance
ws_manager = ConnectionManager()


# ── WebSocket APIRouter ──────────────────────────────────
from fastapi import APIRouter, Depends, Query as WsQuery
from app.auth import decode_access_token

ws_router = APIRouter(tags=["WebSocket"])


@ws_router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket, token: str = WsQuery(None)):
    """Real-time emergency alert stream.
    Connect with: ws://host/api/v1/ws/alerts?token=<jwt>
    Send JSON to subscribe: {"severities":["critical"],"categories":["fire"],"regions":["nairobi"]}
    """
    payload = None
    if token:
        payload = decode_access_token(token)
    user_id = payload.user_id if payload and payload.user_id else 0
    user_id = int(user) if user else 0
    await websocket.accept()
    ws_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            ws_manager.subscribe(
                websocket,
                severities=data.get("severities"),
                categories=data.get("categories"),
                regions=data.get("regions"),
            )
    except Exception:
        pass
    finally:
        ws_manager.disconnect(websocket, user_id)