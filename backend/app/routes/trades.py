from __future__ import annotations

from fastapi import APIRouter

from ..db.repositories import get_trade, list_executions, list_trades
from ..services.portfolio import get_portfolio_summary, get_positions


router = APIRouter(prefix="/api", tags=["trades"])


@router.get("/portfolio")
async def portfolio():
    return get_portfolio_summary()


@router.get("/positions")
async def positions():
    return {"positions": get_positions()}


@router.get("/trades")
async def trades():
    return {"trades": list_trades(), "executions": list_executions()}


@router.get("/trades/{trade_id}")
async def trade_detail(trade_id: str):
    return get_trade(trade_id)


@router.get("/executions")
async def executions():
    return {"executions": list_executions()}
