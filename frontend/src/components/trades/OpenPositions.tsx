import { Position } from "@/lib/types";

export function OpenPositions({ positions }: { positions: Position[] }) {
  return (
    <section style={{ border: "1px solid var(--line)", borderRadius: 20, background: "var(--bg-panel)", padding: 16, display: "grid", gap: 12 }}>
      <div style={{ fontSize: 12, color: "var(--text-soft)", letterSpacing: "0.14em", textTransform: "uppercase", marginBottom: 12 }}>
        Open Positions
      </div>
      <div style={{ display: "grid", gap: 10, maxHeight: 280, overflowY: "auto", paddingRight: 4 }}>
        {positions.length === 0 ? (
          <div style={{ color: "var(--text-soft)" }}>No open paper positions.</div>
        ) : (
          positions.map((position) => (
            <div key={position.id} style={{ display: "flex", justifyContent: "space-between", padding: 12, borderRadius: 14, background: "var(--bg-panel-soft)" }}>
              <div>
                <strong>{position.symbol}</strong>
                <div style={{ color: "var(--text-soft)", fontSize: 13 }}>{position.direction}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div>${Number(position.current_price ?? 0).toFixed(2)}</div>
                <div style={{ color: "var(--text-soft)", fontSize: 13 }}>{position.shares ?? 0} sh</div>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
