from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import get_settings


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    symbol TEXT,
    headline TEXT NOT NULL,
    body_excerpt TEXT,
    source TEXT,
    importance INTEGER DEFAULT 3,
    linked_recommendation_ids TEXT,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_symbol ON events(symbol);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);

CREATE TABLE IF NOT EXISTS recommendations (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    direction TEXT,
    status TEXT NOT NULL DEFAULT 'observing',
    strategy_type TEXT NOT NULL,
    thesis TEXT,
    entry_price REAL,
    entry_logic TEXT,
    stop_price REAL,
    stop_logic TEXT,
    target_price REAL,
    target_logic TEXT,
    position_size_shares REAL,
    position_size_dollars REAL,
    time_horizon TEXT,
    conviction INTEGER,
    supporting_roles TEXT,
    blocking_risks TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_recs_status ON recommendations(status);
CREATE INDEX IF NOT EXISTS idx_recs_symbol ON recommendations(symbol);

CREATE TABLE IF NOT EXISTS discussion_subjects (
    id TEXT PRIMARY KEY,
    subject_type TEXT NOT NULL,
    symbol TEXT,
    event_id TEXT,
    recommendation_id TEXT,
    trade_id TEXT,
    headline TEXT,
    summary TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id),
    FOREIGN KEY (trade_id) REFERENCES trades(id)
);

CREATE INDEX IF NOT EXISTS idx_subjects_type ON discussion_subjects(subject_type);
CREATE INDEX IF NOT EXISTS idx_subjects_symbol ON discussion_subjects(symbol);
CREATE INDEX IF NOT EXISTS idx_subjects_rec ON discussion_subjects(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_subjects_event ON discussion_subjects(event_id);
CREATE INDEX IF NOT EXISTS idx_subjects_trade ON discussion_subjects(trade_id);

CREATE TABLE IF NOT EXISTS role_threads (
    id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    symbol TEXT NOT NULL,
    recommendation_id TEXT,
    discussion_subject_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id),
    FOREIGN KEY (discussion_subject_id) REFERENCES discussion_subjects(id)
);

CREATE INDEX IF NOT EXISTS idx_threads_rec ON role_threads(recommendation_id);

CREATE TABLE IF NOT EXISTS role_messages (
    id TEXT PRIMARY KEY,
    role_thread_id TEXT NOT NULL,
    role TEXT NOT NULL,
    sender TEXT NOT NULL,
    symbol TEXT,
    recommendation_id TEXT,
    discussion_subject_id TEXT,
    message_text TEXT NOT NULL,
    structured_payload TEXT,
    stance TEXT,
    confidence REAL,
    provider TEXT,
    model_used TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (role_thread_id) REFERENCES role_threads(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_thread ON role_messages(role_thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_rec ON role_messages(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_messages_symbol ON role_messages(symbol);

CREATE TABLE IF NOT EXISTS shared_summaries (
    id TEXT PRIMARY KEY,
    recommendation_id TEXT NOT NULL,
    summary_text TEXT,
    bull_case TEXT,
    bear_case TEXT,
    key_disagreement TEXT,
    generated_by_model TEXT,
    last_updated TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id)
);

CREATE TABLE IF NOT EXISTS approval_records (
    id TEXT PRIMARY KEY,
    recommendation_id TEXT NOT NULL,
    status TEXT NOT NULL,
    reviewer_notes TEXT,
    requested_at TEXT NOT NULL,
    approved_at TEXT,
    rejected_at TEXT,
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id)
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    recommendation_id TEXT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_price REAL,
    current_price REAL,
    shares REAL,
    unrealized_pnl REAL,
    stop_price REAL,
    target_price REAL,
    exit_price REAL,
    exit_reason TEXT,
    pnl_dollars REAL,
    pnl_percent REAL,
    risk_state TEXT,
    broker_order_id TEXT,
    opened_at TEXT,
    closed_at TEXT,
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id)
);

CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_open ON trades(closed_at);

CREATE TABLE IF NOT EXISTS executions (
    id TEXT PRIMARY KEY,
    recommendation_id TEXT,
    trade_id TEXT,
    order_type TEXT,
    submitted_at TEXT NOT NULL,
    filled_at TEXT,
    fill_price REAL,
    fill_qty REAL,
    broker_order_id TEXT,
    broker_response TEXT,
    status TEXT NOT NULL,
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id),
    FOREIGN KEY (trade_id) REFERENCES trades(id)
);

CREATE TABLE IF NOT EXISTS role_configs (
    role_name TEXT PRIMARY KEY,
    provider TEXT NOT NULL DEFAULT 'mock',
    default_model TEXT NOT NULL,
    escalation_model TEXT,
    system_prompt_version TEXT NOT NULL DEFAULT 'v1',
    demo_prompt_version TEXT NOT NULL DEFAULT 'demo_v1',
    tool_permissions TEXT,
    cost_budget_per_day REAL DEFAULT 5.0,
    max_tokens_per_call INTEGER DEFAULT 4096,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cost_log (
    id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    recommendation_id TEXT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS strategy_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _db_path() -> Path:
    settings = get_settings()
    path = settings.sqlite_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db() -> None:
    with sqlite3.connect(_db_path()) as conn:
        conn.executescript(SCHEMA)
        _ensure_column(conn, "role_threads", "discussion_subject_id", "TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_threads_subject ON role_threads(discussion_subject_id)")
        _ensure_column(conn, "role_messages", "discussion_subject_id", "TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_subject ON role_messages(discussion_subject_id)")
        conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, column_def: str) -> None:
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")


@contextmanager
def get_conn():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = _dict_factory
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
