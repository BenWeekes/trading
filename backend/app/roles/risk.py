from .base import BaseRole


class RiskRole(BaseRole):
    role_name = "risk"
    response_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "message_text": {"type": "string"},
            "top_risks": {"type": "array", "items": {"type": "string"}},
            "portfolio_overlap": {"type": "array", "items": {"type": "string"}},
            "position_size_recommendation": {"type": "number"},
            "max_portfolio_risk": {"type": "number"},
            "event_blackout_issues": {"type": "array", "items": {"type": "string"}},
            "liquidity_gap_concerns": {"type": "string"},
            "reject_or_reduce": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": [
            "message_text",
            "top_risks",
            "portfolio_overlap",
            "position_size_recommendation",
            "max_portfolio_risk",
            "event_blackout_issues",
            "liquidity_gap_concerns",
            "reject_or_reduce",
            "confidence",
        ],
    }
