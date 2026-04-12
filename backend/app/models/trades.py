from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class OpenTrade(BaseModel):
    id: str
    recommendation_id: str | None = None
    symbol: str
    direction: str
    entry_price: float | None = None
    current_price: float | None = None
    shares: float | None = None
    unrealized_pnl: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    risk_state: str | None = None
    broker_order_id: str | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None


class ExecutionRecord(BaseModel):
    id: str
    recommendation_id: str | None = None
    trade_id: str | None = None
    order_type: str
    submitted_at: datetime
    filled_at: datetime | None = None
    fill_price: float | None = None
    fill_qty: float | None = None
    broker_order_id: str | None = None
    broker_response: dict | None = None
    status: str


class PortfolioSummary(BaseModel):
    cash: float = 0.0
    portfolio_value: float = 0.0
    buying_power: float = 0.0
    equity: float = 0.0
    last_equity: float = 0.0
    daily_change: float = 0.0
    daily_change_pct: float = 0.0
    status: str = "paper"
    currency: str = "USD"
