"use client";

import { useState } from "react";
import { Position } from "@/lib/types";

type Props = {
  position?: Position | null;
  onSell?: (symbol: string, shares: number) => void;
};

export function ActivePositionCard({ position, onSell }: Props) {
  const totalShares = position?.shares ?? 0;
  const [sellShares, setSellShares] = useState<number>(totalShares);

  if (!position) {
    return (
      <div className="panel">
        <div className="panel-header">Position</div>
        <div className="panel-body" style={{ color: "var(--text-muted)", fontSize: 13 }}>
          No open position for this symbol.
        </div>
      </div>
    );
  }

  const pnl = position.unrealized_pnl ?? 0;
  const pnlColor = pnl >= 0 ? "var(--buy)" : "var(--sell)";

  return (
    <div className="panel">
      <div className="panel-header">
        <span>{position.direction} {position.symbol}</span>
        <span style={{ fontWeight: 600, color: pnlColor, fontSize: 12 }}>
          {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
        </span>
      </div>
      <div className="panel-body" style={{ display: "grid", gap: 10 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          <div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Entry</div>
            <div style={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>${Number(position.entry_price ?? 0).toFixed(2)}</div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Current</div>
            <div style={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>${Number(position.current_price ?? 0).toFixed(2)}</div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Shares</div>
            <div style={{ fontWeight: 600 }}>{totalShares}</div>
          </div>
        </div>

        {/* Sell controls */}
        {onSell && totalShares > 0 && (
          <div style={{ borderTop: "1px solid var(--line)", paddingTop: 10, display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="number"
              value={sellShares}
              onChange={(e) => setSellShares(Math.min(Number(e.target.value), totalShares))}
              min={1}
              max={totalShares}
              style={{
                width: 70, padding: "6px 8px", borderRadius: 8,
                border: "1px solid var(--line)", background: "var(--bg)",
                color: "var(--text)", fontSize: 13, textAlign: "center",
              }}
            />
            <button className="btn btn-danger" onClick={() => onSell(position.symbol, sellShares)} style={{ fontSize: 12 }}>
              Sell {sellShares} sh
            </button>
            {sellShares < totalShares && (
              <button className="btn" onClick={() => { setSellShares(totalShares); onSell(position.symbol, totalShares); }} style={{ fontSize: 12 }}>
                Sell All
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
