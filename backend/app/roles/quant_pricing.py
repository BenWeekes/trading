from .base import BaseRole


class QuantPricingRole(BaseRole):
    role_name = "quant_pricing"
    response_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "message_text": {"type": "string"},
            "fair_value_estimate": {"type": "number"},
            "signal_strength": {"type": "string"},
            "expected_move_context": {"type": "string"},
            "entry_zone": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"low": {"type": "number"}, "high": {"type": "number"}},
                "required": ["low", "high"],
            },
            "stop_level": {"type": "number"},
            "target_zone": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"low": {"type": "number"}, "high": {"type": "number"}},
                "required": ["low", "high"],
            },
            "volatility_notes": {"type": "string"},
            "tactical_execution_notes": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": [
            "message_text",
            "fair_value_estimate",
            "signal_strength",
            "expected_move_context",
            "entry_zone",
            "stop_level",
            "target_zone",
            "volatility_notes",
            "tactical_execution_notes",
            "confidence",
        ],
    }
