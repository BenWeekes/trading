from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..adapters.fmp import FMPClient
from ..services.market_poller import get_poll_stats, get_ticker_prices, poll_all
from ..services.market_pulse import get_pulse_data
from ..db.helpers import new_id, utcnow_iso
from ..db.repositories import get_trade, insert_execution, list_executions, list_trades, update_trade
from ..services.event_bus import event_bus
from ..services.exit_manager import check_exits
from ..services.portfolio import get_portfolio_summary, get_positions

_fmp = FMPClient()


router = APIRouter(prefix="/api", tags=["trades"])


@router.get("/portfolio")
async def portfolio():
    return get_portfolio_summary()


@router.get("/positions")
async def positions(refresh_prices: bool = False):
    pos_list = get_positions()
    if refresh_prices and pos_list:
        # Fetch live quotes for open positions
        for pos in pos_list:
            symbol = pos.get("symbol")
            if not symbol:
                continue
            try:
                quote = await _fmp.quote(symbol)
                if quote and quote.get("price"):
                    live_price = float(quote["price"])
                    entry = float(pos.get("entry_price") or live_price)
                    direction = (pos.get("direction") or "BUY").upper()
                    if direction in ("SHORT",):
                        pnl = (entry - live_price) * float(pos.get("shares") or 0)
                    else:
                        pnl = (live_price - entry) * float(pos.get("shares") or 0)
                    pos["current_price"] = live_price
                    pos["unrealized_pnl"] = round(pnl, 2)
                    # Update in DB too
                    if pos.get("id"):
                        update_trade(pos["id"], current_price=live_price, unrealized_pnl=round(pnl, 2))
            except Exception:
                pass
    return {"positions": pos_list}


@router.get("/trades")
async def trades():
    return {"trades": list_trades(), "executions": list_executions()}


@router.get("/trades/{trade_id}")
async def trade_detail(trade_id: str):
    return get_trade(trade_id)


@router.get("/executions")
async def executions():
    return {"executions": list_executions()}


@router.post("/poll-market")
async def poll_market_data():
    """Test FMP data polling — fetches all available data sources and returns summary."""
    return await poll_all()


@router.get("/market-pulse")
async def market_pulse():
    """Live market pulse — gainers, losers, most active with direction colors."""
    return get_pulse_data()


@router.get("/company-name")
async def company_name(symbol: str = ""):
    """Get company name for a symbol from ticker cache or FMP."""
    prices = get_ticker_prices()
    if symbol in prices and prices[symbol].get("name"):
        return {"symbol": symbol, "name": prices[symbol]["name"]}
    # Fallback: live FMP call
    quote = await _fmp.quote(symbol)
    return {"symbol": symbol, "name": quote.get("name", symbol) if quote else symbol}


@router.get("/ticker")
async def ticker():
    """Get all cached stock prices from the market ticker."""
    return {"prices": get_ticker_prices()}


@router.get("/poll-stats")
async def poll_stats():
    """Get background poller statistics — API call count, rate, budget usage."""
    return get_poll_stats()


@router.post("/check-exits")
async def check_exits_endpoint():
    """Check all open positions for stop/target/max-hold exits."""
    closed = await check_exits()
    return {"closed": closed, "checked": len(list_trades(open_only=True)) + len(closed)}


@router.post("/trades/{trade_id}/sell")
async def sell_trade(trade_id: str, payload: dict):
    """Close or partially close a paper trade."""
    trade = get_trade(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.get("closed_at"):
        raise HTTPException(status_code=400, detail="Trade is already closed")

    sell_shares = float(payload.get("shares", trade.get("shares", 0)))
    total_shares = float(trade.get("shares", 0))
    if sell_shares <= 0 or sell_shares > total_shares:
        raise HTTPException(status_code=400, detail=f"Invalid shares: must be 1-{total_shares}")

    now = utcnow_iso()
    exit_price = float(trade.get("current_price") or trade.get("entry_price") or 0)
    entry_price = float(trade.get("entry_price") or 0)
    direction = (trade.get("direction") or "BUY").upper()

    # P&L depends on direction: longs profit when price rises, shorts profit when price falls
    if direction in ("SHORT", "SELL"):
        pnl = (entry_price - exit_price) * sell_shares if entry_price else 0
    else:
        pnl = (exit_price - entry_price) * sell_shares if entry_price else 0

    # Determine exit action name
    exit_action = "cover" if direction in ("SHORT", "SELL") else "sell"

    if sell_shares >= total_shares:
        update_trade(
            trade_id,
            closed_at=now,
            exit_price=exit_price,
            exit_reason="manual",
            pnl_dollars=round(pnl, 2),
            pnl_percent=round((pnl / (entry_price * total_shares)) * 100, 2) if entry_price else 0,
            risk_state="closed",
        )
    else:
        remaining = total_shares - sell_shares
        update_trade(trade_id, shares=remaining)

    insert_execution({
        "id": new_id("exec"),
        "recommendation_id": trade.get("recommendation_id"),
        "trade_id": trade_id,
        "order_type": f"paper_{exit_action}",
        "submitted_at": now,
        "filled_at": now,
        "fill_price": exit_price,
        "fill_qty": sell_shares,
        "broker_order_id": new_id("broker"),
        "broker_response": {"paper": True, "action": exit_action, "direction": direction},
        "status": "filled",
    })

    await event_bus.publish("position_update", {
        "symbol": trade["symbol"],
        "action": exit_action,
        "direction": direction,
        "shares_closed": sell_shares,
    })

    updated = get_trade(trade_id)
    return {"trade": updated, "pnl": round(pnl, 2), "shares_sold": sell_shares}
