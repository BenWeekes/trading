type Props = {
  portfolioValue?: number;
  mode?: string;
};

export function Header({ portfolioValue, mode }: Props) {
  return (
    <header
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "20px 28px",
        borderBottom: "1px solid var(--line)",
      }}
    >
      <div>
        <div style={{ fontSize: 12, letterSpacing: "0.14em", color: "var(--text-soft)", textTransform: "uppercase" }}>
          Weekes AATF
        </div>
        <div style={{ fontSize: 28, fontWeight: 700 }}>Trading Workstation</div>
      </div>
      <div style={{ display: "flex", gap: 18, alignItems: "center" }}>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 12, color: "var(--text-soft)", textTransform: "uppercase" }}>Portfolio</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>
            {typeof portfolioValue === "number" ? `$${portfolioValue.toLocaleString()}` : "Loading"}
          </div>
        </div>
        <div
          style={{
            padding: "10px 12px",
            borderRadius: 999,
            border: "1px solid var(--line)",
            background: "rgba(113, 217, 182, 0.08)",
            color: "var(--accent)",
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          {mode?.toUpperCase() ?? "PAPER"}
        </div>
      </div>
    </header>
  );
}
