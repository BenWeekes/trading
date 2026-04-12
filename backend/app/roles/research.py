from .base import BaseRole


class ResearchRole(BaseRole):
    role_name = "research"
    response_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "message_text": {"type": "string"},
            "thesis_summary": {"type": "string"},
            "beat_quality": {"type": "string"},
            "guidance_change": {"type": "string"},
            "catalysts": {"type": "array", "items": {"type": "string"}},
            "counterpoints": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"},
        },
        "required": [
            "message_text",
            "thesis_summary",
            "beat_quality",
            "guidance_change",
            "catalysts",
            "counterpoints",
            "confidence",
        ],
    }
