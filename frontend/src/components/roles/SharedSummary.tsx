import { Summary } from "@/lib/types";

export function SharedSummary({ summary, symbol }: { summary?: Summary | null; symbol?: string | null }) {
  const hasSummary = summary?.bull_case || summary?.bear_case;

  return (
    <div className="panel" style={{
      background: "linear-gradient(180deg, rgba(18, 37, 61, 0.95), var(--bg-panel))",
    }}>
      <div className="panel-header">
        <span>Summary {symbol ? `\u2014 ${symbol}` : ""}</span>
        {hasSummary && summary?.key_disagreement && (
          <span className="badge badge-warn">Disagreement</span>
        )}
      </div>
      <div className="panel-body" style={{ display: "grid", gap: 8, fontSize: 13 }}>
        <div>
          <span style={{ color: "var(--buy)", fontWeight: 600, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em" }}>Bull: </span>
          <span style={{ color: "var(--text-soft)" }}>{summary?.bull_case ?? "Waiting for role analysis."}</span>
        </div>
        <div>
          <span style={{ color: "var(--sell)", fontWeight: 600, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em" }}>Bear: </span>
          <span style={{ color: "var(--text-soft)" }}>{summary?.bear_case ?? "Waiting for role analysis."}</span>
        </div>
        {summary?.key_disagreement && (
          <div style={{ borderTop: "1px solid var(--line)", paddingTop: 8, marginTop: 2 }}>
            <span style={{ color: "var(--warn)", fontWeight: 600, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em" }}>Key disagreement: </span>
            <span style={{ color: "var(--text-soft)" }}>{summary.key_disagreement}</span>
          </div>
        )}
      </div>
    </div>
  );
}
