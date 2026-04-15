type PortfolioData = {
  portfolio_value?: number;
  cash?: number;
  unrealised_pnl?: number;
  daily_change?: number;
  daily_change_pct?: number;
  open_positions?: number;
};

type Props = {
  portfolio?: PortfolioData;
  mode?: string;
  onScan?: () => void;
  onSettings?: () => void;
  onHelp?: () => void;
};

export function Header({ portfolio, mode, onScan, onSettings, onHelp }: Props) {
  const value = portfolio?.portfolio_value;
  const cash = portfolio?.cash;
  const pnl = portfolio?.daily_change ?? 0;
  const pnlPct = portfolio?.daily_change_pct ?? 0;
  const pnlColor = pnl >= 0 ? "var(--buy)" : "var(--sell)";

  return (
    <header style={{
      display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "12px 20px", borderBottom: "1px solid var(--line)",
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
        {onSettings && <button className="btn" onClick={onSettings}>Settings</button>}
        {onHelp && <button className="btn" onClick={onHelp}>Help</button>}

        <div style={{ height: 24, width: 1, background: "var(--line)", margin: "0 6px" }} />

        {/* Portfolio summary */}
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <Stat label="Portfolio" value={value != null ? `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "..."} />
          <Stat label="Cash" value={cash != null ? `$${cash.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "..."} />
          <Stat label="P&L" value={`${pnl >= 0 ? "+" : ""}$${Math.abs(pnl).toLocaleString(undefined, { maximumFractionDigits: 0 })}`} valueColor={pnlColor} sub={`${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(1)}%`} />
        </div>

        <span className="badge badge-accent" style={{ fontSize: 11, padding: "4px 10px" }}>
          {mode?.toUpperCase() ?? "PAPER"}
        </span>
      </div>
    </header>
  );
}

function Stat({ label, value, valueColor, sub }: { label: string; value: string; valueColor?: string; sub?: string }) {
  return (
    <div style={{ textAlign: "right" }}>
      <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
      <div style={{ fontSize: 15, fontWeight: 700, fontVariantNumeric: "tabular-nums", color: valueColor }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: valueColor ?? "var(--text-muted)" }}>{sub}</div>}
    </div>
  );
}
