from __future__ import annotations

import re
from dataclasses import dataclass, field

import httpx

from ..config import get_settings
from ..db.helpers import utcnow_iso


@dataclass
class AvatarSession:
    recommendation_id: str
    channel: str
    agent_id: str
    profile: str
    started_at: str = field(default_factory=utcnow_iso)


class TraderAvatarBridge:
    def __init__(self) -> None:
        self._sessions: dict[str, AvatarSession] = {}

    def config(self) -> dict:
        settings = get_settings()
        return {
            "enabled": settings.agora_enabled,
            "backend_url": settings.agora_backend_url,
            "client_url": settings.agora_avatar_client_url,
            "profile": settings.agora_profile,
        }

    def session_status(self, recommendation_id: str | None = None) -> dict:
        if recommendation_id and recommendation_id in self._sessions:
            session = self._sessions[recommendation_id]
            return {
                **self.config(),
                "session": {
                    "recommendation_id": session.recommendation_id,
                    "channel": session.channel,
                    "agent_id": session.agent_id,
                    "profile": session.profile,
                    "started_at": session.started_at,
                },
            }
        return {**self.config(), "session": None}

    async def start(self, recommendation_id: str, channel: str | None = None) -> dict:
        settings = get_settings()
        final_channel = channel or f"trader-{re.sub(r'[^a-z0-9]', '', recommendation_id.lower())[:18]}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{settings.agora_backend_url.rstrip('/')}/start-agent",
                params={"channel": final_channel, "profile": settings.agora_profile},
            )
            response.raise_for_status()
            payload = response.json()
        response_body = payload.get("agent_response", {}).get("response", "")
        agent_id_match = re.search(r'"agent_id":"([^"]+)"', response_body)
        if not agent_id_match:
            raise RuntimeError("Agora backend did not return an agent_id")
        session = AvatarSession(
            recommendation_id=recommendation_id,
            channel=payload.get("channel", final_channel),
            agent_id=agent_id_match.group(1),
            profile=settings.agora_profile,
        )
        self._sessions[recommendation_id] = session
        return self.session_status(recommendation_id)

    async def speak(self, recommendation_id: str, text: str, priority: str = "APPEND") -> dict:
        session = self._sessions.get(recommendation_id)
        if not session:
            raise RuntimeError("No active trader avatar session for this recommendation")
        settings = get_settings()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.agora_backend_url.rstrip('/')}/speak",
                json={
                    "agent_id": session.agent_id,
                    "text": text,
                    "priority": priority,
                    "profile": session.profile,
                },
            )
            response.raise_for_status()
            payload = response.json()
        return {"session": self.session_status(recommendation_id)["session"], "speak_result": payload}

    async def stop(self, recommendation_id: str) -> dict:
        session = self._sessions.get(recommendation_id)
        if not session:
            return {"stopped": False, "session": None}
        settings = get_settings()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{settings.agora_backend_url.rstrip('/')}/hangup-agent",
                params={"agent_id": session.agent_id, "profile": session.profile},
            )
            response.raise_for_status()
            payload = response.json()
        self._sessions.pop(recommendation_id, None)
        return {"stopped": True, "result": payload, "session": None}


trader_avatar_bridge = TraderAvatarBridge()
