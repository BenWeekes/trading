from __future__ import annotations

from datetime import datetime

from ..database import get_conn
from .helpers import dump_json, load_json


def insert_event(record: dict) -> None:
    with get_conn() as conn:
        duplicate = conn.execute(
            """
            SELECT id FROM events
            WHERE type = ?
              AND COALESCE(symbol, '') = COALESCE(?, '')
              AND headline = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (
                record["type"],
                record.get("symbol"),
                record["headline"],
            ),
        ).fetchone()
        if duplicate and duplicate["id"] != record["id"]:
            conn.execute("DELETE FROM events WHERE id = ?", (duplicate["id"],))
        conn.execute(
            """
            INSERT OR REPLACE INTO events (
                id, type, symbol, headline, body_excerpt, source,
                importance, linked_recommendation_ids, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["type"],
                record.get("symbol"),
                record["headline"],
                record.get("body_excerpt"),
                record.get("source"),
                record.get("importance", 3),
                dump_json(record.get("linked_recommendation_ids", [])),
                record["timestamp"],
            ),
        )


def list_events(limit: int = 50, event_type: str | None = None) -> list[dict]:
    query = "SELECT * FROM events"
    params: list = []
    if event_type:
        query += " WHERE type = ?"
        params.append(event_type)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    for row in rows:
        row["linked_recommendation_ids"] = load_json(row.get("linked_recommendation_ids"), [])
    return rows


def get_event(event_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if row:
        row["linked_recommendation_ids"] = load_json(row.get("linked_recommendation_ids"), [])
    return row


def upsert_recommendation(record: dict) -> None:
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM recommendations WHERE id = ?", (record["id"],)
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE recommendations
                SET symbol = ?, direction = ?, status = ?, strategy_type = ?, thesis = ?,
                    entry_price = ?, entry_logic = ?, stop_price = ?, stop_logic = ?,
                    target_price = ?, target_logic = ?, position_size_shares = ?,
                    position_size_dollars = ?, time_horizon = ?, conviction = ?,
                    supporting_roles = ?, blocking_risks = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    record["symbol"],
                    record.get("direction"),
                    record["status"],
                    record.get("strategy_type", "PEAD"),
                    record.get("thesis"),
                    record.get("entry_price"),
                    record.get("entry_logic"),
                    record.get("stop_price"),
                    record.get("stop_logic"),
                    record.get("target_price"),
                    record.get("target_logic"),
                    record.get("position_size_shares"),
                    record.get("position_size_dollars"),
                    record.get("time_horizon"),
                    record.get("conviction"),
                    dump_json(record.get("supporting_roles", [])),
                    dump_json(record.get("blocking_risks", [])),
                    record["updated_at"],
                    record["id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO recommendations (
                    id, symbol, direction, status, strategy_type, thesis, entry_price,
                    entry_logic, stop_price, stop_logic, target_price, target_logic,
                    position_size_shares, position_size_dollars, time_horizon, conviction,
                    supporting_roles, blocking_risks, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["symbol"],
                    record.get("direction"),
                    record["status"],
                    record.get("strategy_type", "PEAD"),
                    record.get("thesis"),
                    record.get("entry_price"),
                    record.get("entry_logic"),
                    record.get("stop_price"),
                    record.get("stop_logic"),
                    record.get("target_price"),
                    record.get("target_logic"),
                    record.get("position_size_shares"),
                    record.get("position_size_dollars"),
                    record.get("time_horizon"),
                    record.get("conviction"),
                    dump_json(record.get("supporting_roles", [])),
                    dump_json(record.get("blocking_risks", [])),
                    record["created_at"],
                    record["updated_at"],
                ),
            )


def list_recommendations(limit: int = 20, status: str | None = None) -> list[dict]:
    query = "SELECT * FROM recommendations"
    params: list = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    for row in rows:
        row["supporting_roles"] = load_json(row.get("supporting_roles"), [])
        row["blocking_risks"] = load_json(row.get("blocking_risks"), [])
    return rows


def get_recommendation(rec_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM recommendations WHERE id = ?", (rec_id,)).fetchone()
    if row:
        row["supporting_roles"] = load_json(row.get("supporting_roles"), [])
        row["blocking_risks"] = load_json(row.get("blocking_risks"), [])
    return row


def upsert_discussion_subject(record: dict) -> None:
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM discussion_subjects WHERE id = ?", (record["id"],)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE discussion_subjects
                SET subject_type = ?, symbol = ?, event_id = ?, recommendation_id = ?, trade_id = ?,
                    headline = ?, summary = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    record["subject_type"],
                    record.get("symbol"),
                    record.get("event_id"),
                    record.get("recommendation_id"),
                    record.get("trade_id"),
                    record.get("headline"),
                    record.get("summary"),
                    record.get("status", "active"),
                    record["updated_at"],
                    record["id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO discussion_subjects (
                    id, subject_type, symbol, event_id, recommendation_id, trade_id,
                    headline, summary, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["subject_type"],
                    record.get("symbol"),
                    record.get("event_id"),
                    record.get("recommendation_id"),
                    record.get("trade_id"),
                    record.get("headline"),
                    record.get("summary"),
                    record.get("status", "active"),
                    record["created_at"],
                    record["updated_at"],
                ),
            )


def get_discussion_subject(subject_id: str) -> dict | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM discussion_subjects WHERE id = ?", (subject_id,)).fetchone()


def find_discussion_subject(
    *,
    subject_type: str,
    symbol: str | None = None,
    event_id: str | None = None,
    recommendation_id: str | None = None,
    trade_id: str | None = None,
) -> dict | None:
    query = "SELECT * FROM discussion_subjects WHERE subject_type = ?"
    params: list = [subject_type]
    if event_id:
        query += " AND event_id = ?"
        params.append(event_id)
    if recommendation_id:
        query += " AND recommendation_id = ?"
        params.append(recommendation_id)
    if trade_id:
        query += " AND trade_id = ?"
        params.append(trade_id)
    if symbol:
        query += " AND symbol = ?"
        params.append(symbol)
    query += " ORDER BY updated_at DESC LIMIT 1"
    with get_conn() as conn:
        return conn.execute(query, params).fetchone()


def list_discussion_subjects(limit: int = 50, subject_type: str | None = None) -> list[dict]:
    query = "SELECT * FROM discussion_subjects"
    params: list = []
    if subject_type:
        query += " WHERE subject_type = ?"
        params.append(subject_type)
    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return conn.execute(query, params).fetchall()


def create_role_thread(record: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO role_threads (id, role, symbol, recommendation_id, discussion_subject_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["role"],
                record["symbol"],
                record.get("recommendation_id"),
                record.get("discussion_subject_id"),
                record["created_at"],
            ),
        )


def get_role_thread(role: str, recommendation_id: str | None = None, discussion_subject_id: str | None = None) -> dict | None:
    with get_conn() as conn:
        if discussion_subject_id is not None:
            return conn.execute(
                """
                SELECT * FROM role_threads
                WHERE role = ? AND discussion_subject_id = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (role, discussion_subject_id),
            ).fetchone()
        return conn.execute(
            """
            SELECT * FROM role_threads
            WHERE role = ? AND recommendation_id = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (role, recommendation_id),
        ).fetchone()


def list_role_threads(role: str | None = None, recommendation_id: str | None = None, discussion_subject_id: str | None = None) -> list[dict]:
    query = "SELECT * FROM role_threads WHERE 1=1"
    params: list = []
    if role:
        query += " AND role = ?"
        params.append(role)
    if recommendation_id:
        query += " AND recommendation_id = ?"
        params.append(recommendation_id)
    if discussion_subject_id:
        query += " AND discussion_subject_id = ?"
        params.append(discussion_subject_id)
    query += " ORDER BY created_at DESC"
    with get_conn() as conn:
        return conn.execute(query, params).fetchall()


def insert_role_message(record: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO role_messages (
                id, role_thread_id, role, sender, symbol, recommendation_id, discussion_subject_id,
                message_text, structured_payload, stance, confidence, provider,
                model_used, input_tokens, output_tokens, cost_usd, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["role_thread_id"],
                record["role"],
                record["sender"],
                record.get("symbol"),
                record.get("recommendation_id"),
                record.get("discussion_subject_id"),
                record["message_text"],
                dump_json(record.get("structured_payload", {})),
                record.get("stance"),
                record.get("confidence"),
                record.get("provider"),
                record.get("model_used"),
                record.get("input_tokens", 0),
                record.get("output_tokens", 0),
                record.get("cost_usd", 0.0),
                record["timestamp"],
            ),
        )


def list_role_messages(
    role: str | None = None,
    recommendation_id: str | None = None,
    discussion_subject_id: str | None = None,
    thread_id: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM role_messages WHERE 1=1"
    params: list = []
    if role:
        query += " AND role = ?"
        params.append(role)
    if recommendation_id:
        query += " AND recommendation_id = ?"
        params.append(recommendation_id)
    if discussion_subject_id:
        query += " AND discussion_subject_id = ?"
        params.append(discussion_subject_id)
    if thread_id:
        query += " AND role_thread_id = ?"
        params.append(thread_id)
    query += " ORDER BY timestamp ASC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    for row in rows:
        row["structured_payload"] = load_json(row.get("structured_payload"), {})
    return rows


def upsert_summary(record: dict) -> None:
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM shared_summaries WHERE recommendation_id = ?",
            (record["recommendation_id"],),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE shared_summaries
                SET summary_text = ?, bull_case = ?, bear_case = ?, key_disagreement = ?,
                    generated_by_model = ?, last_updated = ?
                WHERE recommendation_id = ?
                """,
                (
                    record.get("summary_text"),
                    record.get("bull_case"),
                    record.get("bear_case"),
                    record.get("key_disagreement"),
                    record.get("generated_by_model"),
                    record["last_updated"],
                    record["recommendation_id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO shared_summaries (
                    id, recommendation_id, summary_text, bull_case, bear_case,
                    key_disagreement, generated_by_model, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["recommendation_id"],
                    record.get("summary_text"),
                    record.get("bull_case"),
                    record.get("bear_case"),
                    record.get("key_disagreement"),
                    record.get("generated_by_model"),
                    record["last_updated"],
                ),
            )


def get_summary(recommendation_id: str) -> dict | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM shared_summaries WHERE recommendation_id = ?",
            (recommendation_id,),
        ).fetchone()


def insert_approval(record: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO approval_records (
                id, recommendation_id, status, reviewer_notes, requested_at, approved_at, rejected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["recommendation_id"],
                record["status"],
                record.get("reviewer_notes"),
                record["requested_at"],
                record.get("approved_at"),
                record.get("rejected_at"),
            ),
        )


def list_approvals(recommendation_id: str) -> list[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM approval_records WHERE recommendation_id = ? ORDER BY requested_at ASC",
            (recommendation_id,),
        ).fetchall()


def insert_trade(record: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO trades (
                id, recommendation_id, symbol, direction, entry_price, current_price, shares,
                unrealized_pnl, stop_price, target_price, exit_price, exit_reason, pnl_dollars,
                pnl_percent, risk_state, broker_order_id, opened_at, closed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record.get("recommendation_id"),
                record["symbol"],
                record["direction"],
                record.get("entry_price"),
                record.get("current_price"),
                record.get("shares"),
                record.get("unrealized_pnl"),
                record.get("stop_price"),
                record.get("target_price"),
                record.get("exit_price"),
                record.get("exit_reason"),
                record.get("pnl_dollars"),
                record.get("pnl_percent"),
                record.get("risk_state"),
                record.get("broker_order_id"),
                record.get("opened_at"),
                record.get("closed_at"),
            ),
        )


def update_trade(trade_id: str, **fields) -> None:
    if not fields:
        return
    assignments = ", ".join(f"{key} = ?" for key in fields.keys())
    params = list(fields.values()) + [trade_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE trades SET {assignments} WHERE id = ?", params)


def list_trades(limit: int = 100, open_only: bool = False) -> list[dict]:
    query = "SELECT * FROM trades"
    params: list = []
    if open_only:
        query += " WHERE closed_at IS NULL"
    query += " ORDER BY opened_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return conn.execute(query, params).fetchall()


def get_trade(trade_id: str) -> dict | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()


def insert_execution(record: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO executions (
                id, recommendation_id, trade_id, order_type, submitted_at, filled_at,
                fill_price, fill_qty, broker_order_id, broker_response, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record.get("recommendation_id"),
                record.get("trade_id"),
                record["order_type"],
                record["submitted_at"],
                record.get("filled_at"),
                record.get("fill_price"),
                record.get("fill_qty"),
                record.get("broker_order_id"),
                dump_json(record.get("broker_response", {})),
                record["status"],
            ),
        )


def list_executions(limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM executions ORDER BY submitted_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    for row in rows:
        row["broker_response"] = load_json(row.get("broker_response"), {})
    return rows


def upsert_role_config(record: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO role_configs (
                role_name, provider, default_model, escalation_model, system_prompt_version,
                demo_prompt_version, tool_permissions, cost_budget_per_day, max_tokens_per_call, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["role_name"],
                record["provider"],
                record["default_model"],
                record.get("escalation_model"),
                record.get("system_prompt_version", "v1"),
                record.get("demo_prompt_version", "demo_v1"),
                dump_json(record.get("tool_permissions", [])),
                record.get("cost_budget_per_day", 5.0),
                record.get("max_tokens_per_call", 4096),
                record["updated_at"],
            ),
        )


def list_role_configs() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM role_configs ORDER BY role_name ASC").fetchall()
    for row in rows:
        row["tool_permissions"] = load_json(row.get("tool_permissions"), [])
    return rows


def get_role_config(role_name: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM role_configs WHERE role_name = ?",
            (role_name,),
        ).fetchone()
    if row:
        row["tool_permissions"] = load_json(row.get("tool_permissions"), [])
    return row


def insert_cost(record: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO cost_log (
                id, role, recommendation_id, provider, model, input_tokens, output_tokens, cost_usd, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["role"],
                record.get("recommendation_id"),
                record["provider"],
                record["model"],
                record["input_tokens"],
                record["output_tokens"],
                record["cost_usd"],
                record["timestamp"],
            ),
        )


def list_costs() -> list[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM cost_log ORDER BY timestamp DESC LIMIT 500"
        ).fetchall()


# ── Strategy Settings ──

def get_all_strategy_settings() -> dict[str, str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM strategy_settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


def get_strategy_setting(key: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM strategy_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_strategy_setting(key: str, value: str) -> None:
    from .helpers import utcnow_iso
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO strategy_settings (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, utcnow_iso()),
        )
