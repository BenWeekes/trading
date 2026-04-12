from __future__ import annotations

from ..db.helpers import new_id, utcnow_iso


def demo_scenarios() -> list[dict]:
    now = utcnow_iso()
    return [
        {
            "id": new_id("evt"),
            "type": "earnings",
            "symbol": "NVDA",
            "headline": "NVDA beats EPS by 8% and raises guidance",
            "body_excerpt": "Strong data center demand, upbeat next-quarter outlook.",
            "source": "Mock",
            "timestamp": now,
            "importance": 5,
            "linked_recommendation_ids": [],
        },
        {
            "id": new_id("evt"),
            "type": "macro",
            "symbol": "SPY",
            "headline": "Fed minutes signal rates may stay higher for longer",
            "body_excerpt": "Market reprices growth exposure after hawkish tone.",
            "source": "Mock",
            "timestamp": now,
            "importance": 4,
            "linked_recommendation_ids": [],
        },
    ]
