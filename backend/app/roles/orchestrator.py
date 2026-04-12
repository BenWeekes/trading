from __future__ import annotations

import asyncio
import re

from ..db.helpers import new_id, utcnow_iso
from ..db.repositories import (
    get_recommendation,
    get_role_thread,
    get_summary,
    insert_role_message,
    list_role_messages,
    upsert_recommendation,
    upsert_summary,
)
from ..services.event_bus import event_bus
from ..services.state_machine import ensure_transition
from .quant_pricing import QuantPricingRole
from .research import ResearchRole
from .risk import RiskRole
from .trader import TraderRole


class Orchestrator:
    def __init__(self) -> None:
        self.research = ResearchRole()
        self.risk = RiskRole()
        self.quant = QuantPricingRole()
        self.trader = TraderRole()

    async def analyze_event(self, recommendation: dict, event: dict, portfolio: dict) -> dict:
        ensure_transition(recommendation["status"], "under_discussion")
        recommendation["status"] = "under_discussion"
        recommendation["updated_at"] = utcnow_iso()
        upsert_recommendation(recommendation)

        base_context = {"symbol": recommendation["symbol"], "event": event, "portfolio": portfolio}
        research_msg, risk_msg, quant_msg = await asyncio.gather(
            self.research.respond(
                symbol=recommendation["symbol"],
                recommendation_id=recommendation["id"],
                prompt="Analyze the event as research.",
                context=base_context,
                sender="role:research",
            ),
            self.risk.respond(
                symbol=recommendation["symbol"],
                recommendation_id=recommendation["id"],
                prompt="Analyze the event as risk.",
                context=base_context,
                sender="role:risk",
            ),
            self.quant.respond(
                symbol=recommendation["symbol"],
                recommendation_id=recommendation["id"],
                prompt="Analyze the event as quant pricing.",
                context=base_context,
                sender="role:quant_pricing",
            ),
        )

        summary = {
            "id": new_id("summary"),
            "recommendation_id": recommendation["id"],
            "summary_text": f"{recommendation['symbol']} has a live bull/bear discussion underway.",
            "bull_case": research_msg["message_text"],
            "bear_case": risk_msg["message_text"],
            "key_disagreement": "Sizing and volatility tolerance.",
            "generated_by_model": "mock-v1",
            "last_updated": utcnow_iso(),
        }
        upsert_summary(summary)
        await event_bus.publish("summary_update", summary)

        await self._role_query(
            role=self.research,
            recommendation_id=recommendation["id"],
            symbol=recommendation["symbol"],
            question="What gives you confidence this event changes the thesis rather than just the headline?",
        )
        await self._role_query(
            role=self.quant,
            recommendation_id=recommendation["id"],
            symbol=recommendation["symbol"],
            question="Where is the cleanest entry zone and what price action would invalidate the setup?",
        )
        await self._role_query(
            role=self.risk,
            recommendation_id=recommendation["id"],
            symbol=recommendation["symbol"],
            question="What would make you reduce size or veto this trade right now?",
        )

        trader_context = {
            "symbol": recommendation["symbol"],
            "event": event,
            "portfolio": portfolio,
            "role_outputs": {
                "research": research_msg["structured_payload"],
                "risk": risk_msg["structured_payload"],
                "quant_pricing": quant_msg["structured_payload"],
            },
        }
        trader_msg = await self.trader.respond(
            symbol=recommendation["symbol"],
            recommendation_id=recommendation["id"],
            prompt="Synthesize the role outputs and make a trader recommendation.",
            context=trader_context,
            sender="role:trader",
        )

        ensure_transition(recommendation["status"], "draft_recommendation")
        recommendation["status"] = "draft_recommendation"
        ensure_transition(recommendation["status"], "awaiting_user_feedback")

        # Extract direction from structured payload or from the text
        payload = trader_msg["structured_payload"] or {}
        text = trader_msg["message_text"] or ""
        direction = payload.get("final_recommendation") or payload.get("action") or payload.get("direction")
        if not direction:
            direction = self._extract_direction_from_text(text)
        conviction = payload.get("conviction")
        if conviction is None:
            conviction = self._extract_conviction_from_text(text)

        recommendation.update(
            {
                "direction": direction,
                "status": "awaiting_user_feedback",
                "thesis": payload.get("thesis") or text[:300] or recommendation.get("thesis"),
                "entry_price": self._read_numeric(payload, "entry_price")
                or recommendation.get("entry_price"),
                "entry_logic": payload.get("entry_logic"),
                "target_price": self._read_numeric(payload, "target_price")
                or recommendation.get("target_price"),
                "target_logic": payload.get("target_logic"),
                "stop_price": self._read_numeric(payload, "stop_price")
                or recommendation.get("stop_price"),
                "stop_logic": payload.get("stop_logic"),
                "conviction": conviction,
                "supporting_roles": ["research", "quant_pricing"],
                "blocking_risks": ["Sizing caution"],
                "updated_at": utcnow_iso(),
            }
        )
        upsert_recommendation(recommendation)
        await event_bus.publish(
            "recommendation_update",
            {
                "id": recommendation["id"],
                "status": recommendation["status"],
                "symbol": recommendation["symbol"],
                "action": recommendation["direction"],
                "conviction": recommendation["conviction"],
            },
        )
        return get_recommendation(recommendation["id"]) or recommendation

    async def user_chat(self, role_name: str, recommendation_id: str, message: str) -> dict:
        recommendation = get_recommendation(recommendation_id)
        if not recommendation:
            raise ValueError("Recommendation not found")
        role_map = {
            "research": self.research,
            "risk": self.risk,
            "quant_pricing": self.quant,
            "trader": self.trader,
        }
        role = role_map[role_name]
        await self._insert_user_message(
            role=role,
            recommendation_id=recommendation_id,
            symbol=recommendation["symbol"],
            message=message,
        )
        if role_name == "trader":
            requested_roles = self._roles_needed_for_trader_follow_up(message, recommendation)
            if requested_roles:
                await asyncio.gather(
                    *[
                        self._role_query(
                            role=role_map[requested_role],
                            recommendation_id=recommendation_id,
                            symbol=recommendation["symbol"],
                            question=f"User asks: {message}. What is the {requested_role.replace('_', ' ')} answer?",
                        )
                        for requested_role in requested_roles
                    ]
                )
        context = {"symbol": recommendation["symbol"], "user_message": message}
        response = await role.respond(
            symbol=recommendation["symbol"],
            recommendation_id=recommendation_id,
            prompt=message,
            context=context,
            sender=f"role:{role_name}",
        )
        await event_bus.publish("role_message", response)
        if role_name == "trader" and recommendation["status"] == "awaiting_user_feedback":
            ensure_transition(recommendation["status"], "awaiting_user_approval")
            recommendation["status"] = "awaiting_user_approval"
            recommendation["updated_at"] = utcnow_iso()
            upsert_recommendation(recommendation)
            await event_bus.publish(
                "recommendation_update",
                {
                    "id": recommendation["id"],
                    "status": recommendation["status"],
                    "symbol": recommendation["symbol"],
                    "action": recommendation.get("direction"),
                    "conviction": recommendation.get("conviction"),
                    "recommendation_id": recommendation["id"],
                },
            )
        return response

    async def route_group_chat(self, recommendation_id: str, message: str) -> dict:
        stripped = message.strip()
        role_name = "trader"
        for candidate in ("research", "risk", "quant_pricing", "trader"):
            token = f"@{candidate}"
            if stripped.lower().startswith(token):
                role_name = candidate
                stripped = stripped[len(token):].strip() or f"Respond as {candidate}."
                break
        return await self.user_chat(role_name, recommendation_id, stripped)

    def timeline(self, recommendation_id: str) -> list[dict]:
        return list_role_messages(recommendation_id=recommendation_id)

    def summary(self, recommendation_id: str) -> dict | None:
        return get_summary(recommendation_id)

    def _roles_needed_for_trader_follow_up(self, message: str, recommendation: dict) -> list[str]:
        lowered = message.lower()
        if recommendation["status"] in {"under_discussion", "draft_recommendation"}:
            return ["research", "risk", "quant_pricing"]
        requested: list[str] = []
        if any(term in lowered for term in ("research", "guidance", "catalyst", "thesis", "narrative", "why")):
            requested.append("research")
        if any(term in lowered for term in ("risk", "size", "sizing", "portfolio", "overlap", "exposure", "veto")):
            requested.append("risk")
        if any(term in lowered for term in ("price", "entry", "stop", "target", "quant", "level", "levels")):
            requested.append("quant_pricing")
        if requested:
            return requested
        if re.search(r"\b(what do you think|summarize|recommend|consensus|what do the others think)\b", lowered):
            return ["research", "risk", "quant_pricing"]
        return []

    async def _role_query(self, *, role, recommendation_id: str, symbol: str, question: str) -> dict:
        thread = await role.ensure_thread(symbol, recommendation_id)
        query_message = {
            "id": new_id("msg"),
            "role_thread_id": thread["id"],
            "role": role.role_name,
            "sender": "role:trader",
            "symbol": symbol,
            "recommendation_id": recommendation_id,
            "message_text": question,
            "structured_payload": {"type": "role_query"},
            "stance": None,
            "confidence": None,
            "provider": None,
            "model_used": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "timestamp": utcnow_iso(),
        }
        insert_role_message(query_message)
        await event_bus.publish(
            "role_query",
            {
                "from_role": "trader",
                "to_role": role.role_name,
                "question": question,
                "recommendation_id": recommendation_id,
            },
        )
        await event_bus.publish("role_message", query_message)
        return await role.respond(
            symbol=symbol,
            recommendation_id=recommendation_id,
            prompt=question,
            context={"symbol": symbol, "question_from_trader": question},
            sender=f"role:{role.role_name}",
        )

    async def _insert_user_message(self, *, role, recommendation_id: str, symbol: str, message: str) -> dict:
        thread = get_role_thread(role.role_name, recommendation_id) or await role.ensure_thread(symbol, recommendation_id)
        user_message = {
            "id": new_id("msg"),
            "role_thread_id": thread["id"],
            "role": role.role_name,
            "sender": "user",
            "symbol": symbol,
            "recommendation_id": recommendation_id,
            "message_text": message,
            "structured_payload": {"type": "directed_user_message", "target_role": role.role_name},
            "stance": None,
            "confidence": None,
            "provider": None,
            "model_used": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "timestamp": utcnow_iso(),
        }
        insert_role_message(user_message)
        await event_bus.publish("role_message", user_message)
        return user_message

    @staticmethod
    def _extract_direction_from_text(text: str) -> str:
        """Parse BUY/SELL/SHORT/COVER/PASS from the trader's natural language response."""
        upper = text.upper()
        # Look for explicit action statements
        for action in ("BUY", "SHORT", "SELL", "COVER"):
            for pattern in (f"ACTION: **{action}", f"ACTION: {action}", f"RECOMMENDATION: {action}",
                           f"I RECOMMEND {action}", f"RECOMMEND {action}", f"MY CALL: {action}",
                           f"VERDICT: {action}", f"**{action}**"):
                if pattern in upper:
                    return action
        # Fallback: look for "BUY" or "SHORT" as standalone prominent words
        for action in ("BUY", "SHORT", "SELL", "COVER"):
            if f" {action} " in f" {upper} ":
                return action
        return "PASS"

    @staticmethod
    def _extract_conviction_from_text(text: str) -> int:
        """Parse conviction score like '7/10' or 'Conviction: 8' from text."""
        import re
        patterns = [
            r'conviction[:\s]*\**(\d+)\s*/\s*10',
            r'conviction[:\s]*\**(\d+)',
            r'(\d+)\s*/\s*10\s*conviction',
            r'(\d+)/10',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = int(match.group(1))
                if 1 <= val <= 10:
                    return val
        return 5

    @staticmethod
    def _read_numeric(payload: dict, key: str) -> float | None:
        value = payload.get(key)
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
