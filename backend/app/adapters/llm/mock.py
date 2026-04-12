from __future__ import annotations

from .base import LLMResponse


class MockProvider:
    async def complete(
        self,
        *,
        role: str,
        prompt: str,
        context: dict,
        model: str | None = None,
        schema: dict | None = None,
    ) -> LLMResponse:
        symbol = context.get("symbol", "UNKNOWN")
        event = context.get("event", {})
        importance = event.get("importance", 3)
        if role == "research":
            payload = {
                "thesis_summary": f"{symbol} looks fundamentally supported after the event.",
                "beat_quality": "REVENUE_DRIVEN",
                "guidance_change": "RAISED" if importance >= 4 else "MAINTAINED",
                "catalysts": ["Follow-through buying", "Positive guidance"],
                "counterpoints": ["Gap risk after the open"],
                "confidence": 0.73,
            }
            text = f"Research sees a credible post-event thesis in {symbol}, with follow-through most likely if guidance holds."
        elif role == "risk":
            payload = {
                "top_risks": ["Gap reversal", "Portfolio concentration"],
                "portfolio_overlap": ["Large-cap tech"],
                "position_size_recommendation": 0.75,
                "max_portfolio_risk": 0.02,
                "event_blackout_issues": [],
                "liquidity_gap_concerns": "Monitor opening volatility.",
                "reject_or_reduce": "reduce",
            }
            text = f"Risk is not vetoing {symbol}, but wants disciplined sizing because post-event volatility can be sharp."
        elif role == "quant_pricing":
            payload = {
                "fair_value_estimate": 112.5,
                "signal_strength": "STRONG" if importance >= 4 else "MODERATE",
                "expected_move_context": "Move is above average but still tradeable.",
                "entry_zone": {"low": 108.0, "high": 110.5},
                "stop_level": 104.0,
                "target_zone": {"low": 116.0, "high": 120.0},
                "volatility_notes": "Expect noisy opening price action.",
                "tactical_execution_notes": "Avoid chasing the first spike.",
            }
            text = f"Quant pricing likes the setup in {symbol}, but prefers an entry zone rather than blindly lifting the open."
        elif role == "trader":
            role_outputs = context.get("role_outputs", {})
            research = role_outputs.get("research", {})
            risk = role_outputs.get("risk", {})
            quant = role_outputs.get("quant_pricing", {})
            action = "BUY"
            if risk.get("reject_or_reduce") == "reject":
                action = "PASS"
            payload = {
                "final_recommendation": action,
                "conviction": 7,
                "size_proposal": "Standard paper size reduced for volatility." if risk else "Standard paper size.",
                "must_have_conditions": ["Price stays inside entry zone", "Risk regime does not worsen"],
                "conditions_that_invalidate_trade": ["Opening reversal below stop logic", "Macro shock"],
                "dissent_notes": "Risk wants caution on sizing.",
                "questions_for_user": ["Do you want to act immediately or wait for a better entry?"],
                "approval_request_state": "awaiting_user_approval",
                "thesis": research.get("thesis_summary", f"{symbol} remains interesting."),
                "entry_price": 109.5,
                "entry_logic": "Use the quant entry zone instead of chasing the initial move.",
                "target_price": 118.0,
                "target_logic": "Target the upper edge of the quant zone if momentum continues.",
                "stop_price": 104.0,
                "stop_logic": "Use the quant stop level and respect risk sizing.",
            }
            text = f"Trader sees a {action} candidate in {symbol}. Research is constructive, quant likes the level structure, and risk wants disciplined sizing."
        else:
            payload = {}
            text = f"{role} has no response."

        return LLMResponse(
            text=text,
            structured_payload=payload,
            provider="mock",
            model=model or "mock-v1",
            input_tokens=200,
            output_tokens=120,
            cost_usd=0.0,
        )
