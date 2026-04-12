"use client";

import { useState } from "react";
import { Position, Recommendation, TraderAvatarStatus } from "@/lib/types";

type Props = {
  positions: Position[];
  activeSymbol?: string | null;
  avatarStatus?: TraderAvatarStatus | null;
  recommendation?: Recommendation | null;
  onSell: (symbol: string, shares: number) => void;
  onAvatarStart: () => void;
  onAvatarStop: () => void;
};

export function AvatarAndPositions({ positions, activeSymbol, avatarStatus, recommendation, onSell, onAvatarStart, onAvatarStop }: Props) {
  const session = avatarStatus?.session;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Avatar area */}
      <div className="panel">
        <div className="panel-header">
          <span>Trader Avatar</span>
          <span style={{ fontSize: 10, color: session ? "var(--accent)" : "var(--text-muted)" }}>
            {session ? "Live" : "Offline"}
          </span>
        </div>
        <div style={{ background: "#060d18", minHeight: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
          {session ? (
            <div id="avatar-container" style={{ width: "100%", height: 200, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent)", fontSize: 14 }}>
              Avatar session active on {session.channel}
            </div>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: 13, textAlign: "center", padding: 20 }}>
              Trader avatar will appear here when a voice session is started.
            </div>
          )}
        </div>
        <div style={{ padding: "10px 16px", display: "flex", gap: 8, borderTop: "1px solid var(--line)" }}>
          <button className="btn btn-accent" onClick={onAvatarStart} disabled={!!session}>
            Start Call
          </button>
          <button className="btn btn-danger" onClick={onAvatarStop} disabled={!session}>
            Stop Call
          </button>
          {recommendation && (
            <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: "auto", alignSelf: "center" }}>
              {recommendation.symbol} — {recommendation.status.replace(/_/g, " ")}
            </span>
          )}
        </div>
      </div>

      {/* Position List (Portfolio) */}
      <div className="panel">
        <div className="panel-header">
          <span>Portfolio</span>
          <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{positions.length} position{positions.length !== 1 ? "s" : ""}</span>
        </div>
        <div style={{ maxHeight: 400, overflowY: "auto" }}>
          {positions.length === 0 ? (
            <div style={{ padding: 20, color: "var(--text-muted)", fontSize: 13, textAlign: "center" }}>
              No open positions. Approve and execute a trade to see positions here.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column" }}>
              {positions.map((pos) => (
                <PositionRow
                  key={pos.id}
                  position={pos}
                  active={pos.symbol === activeSymbol}
                  onSell={onSell}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PositionRow({ position, active, onSell }: { position: Position; active: boolean; onSell: (symbol: string, shares: number) => void }) {
  const [sellShares, setSellShares] = useState(position.shares ?? 0);
  const [showSell, setShowSell] = useState(false);
  const pnl = position.unrealized_pnl ?? 0;
  const pnlColor = pnl >= 0 ? "var(--buy)" : "var(--sell)";
  const totalShares = position.shares ?? 0;

  return (
    <div style={{
      padding: "10px 16px", borderBottom: "1px solid var(--line)",
      background: active ? "var(--accent-glow)" : "transparent",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <strong style={{ fontSize: 14 }}>{position.symbol}</strong>
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 8 }}>{totalShares} sh @ ${Number(position.entry_price ?? 0).toFixed(2)}</span>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 14, fontWeight: 600, fontVariantNumeric: "tabular-nums", color: pnlColor }}>
            {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>${Number(position.current_price ?? 0).toFixed(2)}</div>
        </div>
      </div>

      {/* Sell controls */}
      {!showSell ? (
        <button
          onClick={() => setShowSell(true)}
          style={{ marginTop: 6, fontSize: 11, color: "var(--sell)", background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}
        >
          Sell...
        </button>
      ) : (
        <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="number" value={sellShares} min={1} max={totalShares}
            onChange={(e) => setSellShares(Math.min(Number(e.target.value), totalShares))}
            style={{ width: 60, padding: "4px 8px", borderRadius: 6, border: "1px solid var(--line)", background: "var(--bg)", color: "var(--text)", fontSize: 12, textAlign: "center" }}
          />
          <button className="btn btn-danger" style={{ fontSize: 11, padding: "4px 10px" }} onClick={() => { onSell(position.symbol, sellShares); setShowSell(false); }}>
            Sell {sellShares} sh
          </button>
          {sellShares < totalShares && (
            <button className="btn" style={{ fontSize: 11, padding: "4px 10px" }} onClick={() => { onSell(position.symbol, totalShares); setShowSell(false); }}>
              Sell All
            </button>
          )}
          <button style={{ fontSize: 11, color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer" }} onClick={() => setShowSell(false)}>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
