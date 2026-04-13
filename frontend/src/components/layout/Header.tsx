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
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
            <polyline points="16 7 22 7 22 13" />
          </svg>
        </div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600 }}>Trading Desk AI</div>
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
