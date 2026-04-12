import { Position } from "@/lib/types";

export function ActivePositionCard({ position }: { position?: Position | null }) {
  return (
    <div className="panel">
      <div className="panel-header">Active Position</div>
      <div className="panel-body">
        {position ? (
          <div style={{ display: "grid", gap: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong style={{ fontSize: 16 }}>{position.direction} {position.symbol}</strong>
              <span style={{ color: "var(--text-muted)", fontSize: 12 }}>{position.shares ?? 0} shares</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              <div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em" }}>Entry</div>
                <div style={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>${Number(position.entry_price ?? 0).toFixed(2)}</div>
              </div>
              <div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em" }}>Current</div>
                <div style={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>${Number(position.current_price ?? 0).toFixed(2)}</div>
              </div>
              <div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em" }}>P&L</div>
                <div style={{
                  fontWeight: 600, fontVariantNumeric: "tabular-nums",
                  color: (position.unrealized_pnl ?? 0) >= 0 ? "var(--buy)" : "var(--sell)",
                }}>
                  {(position.unrealized_pnl ?? 0) >= 0 ? "+" : ""}${Number(position.unrealized_pnl ?? 0).toFixed(2)}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div style={{ color: "var(--text-muted)", fontSize: 13 }}>No open position for this symbol.</div>
        )}
      </div>
    </div>
  );
}
