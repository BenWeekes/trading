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
    appid: str = ""
    token: str = ""
    uid: int = 0
    agent_uid: str = ""
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
            s = self._sessions[recommendation_id]
            return {
                **self.config(),
                "session": {
                    "recommendation_id": s.recommendation_id,
                    "channel": s.channel,
                    "agent_id": s.agent_id,
                    "profile": s.profile,
                    "appid": s.appid,
                    "token": s.token,
                    "uid": s.uid,
                    "agent_uid": s.agent_uid,
                    "started_at": s.started_at,
                },
            }
        return {**self.config(), "session": None}

    async def start(self, recommendation_id: str, channel: str | None = None) -> dict:
        """Two-phase start: get tokens first, then start agent."""
        settings = get_settings()
        final_channel = channel or f"trader-{re.sub(r'[^a-z0-9]', '', recommendation_id.lower())[:18]}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Phase 1: Get tokens only (connect=false)
            token_resp = await client.get(
                f"{settings.agora_backend_url.rstrip('/')}/start-agent",
                params={
                    "channel": final_channel,
                    "profile": settings.agora_profile,
                    "connect": "false",
                },
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()

            # Phase 2: Start agent (connect=true, default)
            agent_resp = await client.get(
                f"{settings.agora_backend_url.rstrip('/')}/start-agent",
                params={
                    "channel": token_data.get("channel", final_channel),
                    "profile": settings.agora_profile,
                },
            )
            agent_resp.raise_for_status()
            agent_data = agent_resp.json()

        # Extract agent_id
        response_body = agent_data.get("agent_response", {}).get("response", "")
        agent_id = ""
        match = re.search(r'"agent_id"\s*:\s*"([^"]+)"', response_body)
        if match:
            agent_id = match.group(1)

        session = AvatarSession(
            recommendation_id=recommendation_id,
            channel=token_data.get("channel", final_channel),
            agent_id=agent_id,
            profile=settings.agora_profile,
            appid=token_data.get("appid", ""),
            token=token_data.get("token", ""),
            uid=int(token_data.get("uid", 0)),
            agent_uid=str(token_data.get("agent", {}).get("uid", "")),
        )
        self._sessions[recommendation_id] = session
        return self.session_status(recommendation_id)

    async def speak(self, recommendation_id: str, text: str, priority: str = "APPEND") -> dict:
        session = self._sessions.get(recommendation_id)
        if not session:
            raise RuntimeError("No active trader avatar session")
        settings = get_settings()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.agora_backend_url.rstrip('/')}/speak",
                json={"agent_id": session.agent_id, "text": text, "priority": priority, "profile": session.profile},
            )
            resp.raise_for_status()
        return {"session": self.session_status(recommendation_id)["session"], "speak_result": resp.json()}

    async def stop(self, recommendation_id: str) -> dict:
        session = self._sessions.get(recommendation_id)
        if not session:
            return {"stopped": False, "session": None}
        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(
                    f"{settings.agora_backend_url.rstrip('/')}/hangup-agent",
                    params={"agent_id": session.agent_id, "profile": session.profile},
                )
                resp.raise_for_status()
        except Exception:
            pass
        self._sessions.pop(recommendation_id, None)
        return {"stopped": True, "session": None}


trader_avatar_bridge = TraderAvatarBridge()
