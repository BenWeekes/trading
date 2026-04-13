type Props = {
  portfolioValue?: number;
  mode?: string;
  onScan?: () => void;
};

export function Header({ portfolioValue, mode, onScan }: Props) {
  return (
    <header style={{
      display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "14px 20px", borderBottom: "1px solid var(--line)",
      background: "linear-gradient(180deg, rgba(15, 25, 40, 0.95), rgba(8, 17, 31, 0.95))",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <div style={{
          width: 34, height: 34, borderRadius: 8,
          background: "linear-gradient(135deg, var(--accent), #60a5fa)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontWeight: 700, fontSize: 15, color: "#fff",
        }}>W</div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600 }}>AI Trading Platform</div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Multi-Role Trading Workstation</div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        {onScan && <button className="btn btn-accent" onClick={onScan}>Scan Earnings</button>}

        <div style={{ height: 20, width: 1, background: "var(--line)", margin: "0 4px" }} />

        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em" }}>Portfolio</div>
          <div style={{ fontSize: 18, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
            {typeof portfolioValue === "number" ? `$${portfolioValue.toLocaleString()}` : "..."}
          </div>
        </div>

        <span className="badge badge-accent" style={{ fontSize: 11, padding: "4px 10px" }}>
          {mode?.toUpperCase() ?? "PAPER"}
        </span>
      </div>
    </header>
  );
}
