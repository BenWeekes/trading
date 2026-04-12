import { Position } from "@/lib/types";

export function ActivePositionCard({ position }: { position?: Position | null }) {
  return (
    <section style={{ border: "1px solid var(--line)", borderRadius: 20, background: "var(--bg-panel)", padding: 16, display: "grid", gap: 10 }}>
      <div style={{ fontSize: 12, color: "var(--text-soft)", letterSpacing: "0.14em", textTransform: "uppercase" }}>
        Active Position
      </div>
      {position ? (
        <>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <strong style={{ fontSize: 18 }}>{position.direction} {position.symbol}</strong>
            <span style={{ color: "var(--text-soft)", fontSize: 13 }}>{position.shares ?? 0} sh</span>
          </div>
          <div style={{ display: "grid", gap: 6, fontSize: 14 }}>
            <div>Entry: ${Number(position.entry_price ?? 0).toFixed(2)}</div>
            <div>Current: ${Number(position.current_price ?? 0).toFixed(2)}</div>
            <div>PnL: ${Number(position.unrealized_pnl ?? 0).toFixed(2)}</div>
          </div>
        </>
      ) : (
        <div style={{ color: "var(--text-soft)", fontSize: 14 }}>No open position for the active symbol.</div>
      )}
    </section>
  );
}
