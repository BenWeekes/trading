from .base import BaseRole


class TraderRole(BaseRole):
    role_name = "trader"
    response_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "message_text": {"type": "string"},
            "final_recommendation": {"type": "string"},
            "conviction": {"type": "integer"},
            "size_proposal": {"type": "string"},
            "must_have_conditions": {"type": "array", "items": {"type": "string"}},
            "conditions_that_invalidate_trade": {"type": "array", "items": {"type": "string"}},
            "dissent_notes": {"type": "string"},
            "questions_for_user": {"type": "array", "items": {"type": "string"}},
            "approval_request_state": {"type": "string"},
            "thesis": {"type": "string"},
            "entry_price": {"type": "number"},
            "entry_logic": {"type": "string"},
            "target_price": {"type": "number"},
            "target_logic": {"type": "string"},
            "stop_price": {"type": "number"},
            "stop_logic": {"type": "string"},
        },
        "required": [
            "message_text",
            "final_recommendation",
            "conviction",
            "size_proposal",
            "must_have_conditions",
            "conditions_that_invalidate_trade",
            "dissent_notes",
            "questions_for_user",
            "approval_request_state",
            "thesis",
            "entry_price",
            "entry_logic",
            "target_price",
            "target_logic",
            "stop_price",
            "stop_logic",
        ],
    }
