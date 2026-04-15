"use client";

import { useEffect, useState } from "react";
import { Recommendation, Summary } from "@/lib/types";

type Props = {
  recommendation?: Recommendation | null;
  summary?: Summary | null;
  companyName?: string;
  onReady: () => void;
  onApprove: (shares: number) => void;
  onApproveAndExecute: (shares: number) => void;
  onExecute: () => void;
  onReject: () => void;
};

const ACTION_COLORS: Record<string, string> = {
  BUY: "var(--buy)", SELL: "var(--sell)", SHORT: "var(--warn)", COVER: "var(--accent)", PASS: "var(--text-muted)",
};

const ACTION_TIPS: Record<string, string> = {
  BUY: "Open or add to a long position", SELL: "Reduce or close a long", SHORT: "Open a short position",
  COVER: "Close a short position", PASS: "No action — best move is to wait",
};

export function TradePanel({ recommendation, summary, companyName, onReady, onApprove, onApproveAndExecute, onExecute, onReject }: Props) {
  const rec = recommendation;
  const [shares, setShares] = useState(rec?.position_size_shares ?? 10);

  // Reset shares when recommendation changes
  const recId = rec?.id;
  useEffect(() => { setShares(rec?.position_size_shares ?? 10); }, [recId]);

  if (!rec) {
    return (
      <div className="panel" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <div className="panel-header">Analysis</div>
        <div className="panel-body" style={{ color: "var(--text-muted)", textAlign: "center", padding: 24, flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div>
            <div style={{ fontSize: 24, opacity: 0.3, marginBottom: 8 }}>📊</div>
            <div>Select a stock from the news feed or market lists to see the AI analysis.</div>
          </div>
        </div>
      </div>
    );
  }

  const action = rec.direction ?? "PASS";
  const color = ACTION_COLORS[action] ?? "var(--text)";
  const isFeedback = rec.status === "awaiting_user_feedback";
  const isApproval = rec.status === "awaiting_user_approval";
  const canReady = isFeedback;  // Must click Ready before Approve
  const canApprove = isApproval;
  const canExecute = rec.status === "approved";
  const canReject = isFeedback || isApproval;
  const hasSummary = summary?.bull_case || summary?.bear_case;

  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <div className="panel-header" style={{ gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span data-tooltip={ACTION_TIPS[action]} style={{ color, fontWeight: 700, fontSize: 14 }}>{action}</span>
          <span style={{ fontWeight: 700, fontSize: 14 }}>{rec.symbol}</span>
          {companyName && <span style={{ color: "var(--text-muted)", fontWeight: 400, fontSize: 11 }}>{companyName}</span>}
          {rec.conviction != null && (
            <span style={{ color: "var(--text-muted)", fontWeight: 400, fontSize: 12 }}>Conviction {rec.conviction}/10</span>
          )}
        </div>
        <StatusBadge status={rec.status} />
      </div>

      <div className="panel-body" style={{ display: "grid", gap: 10, flex: 1, overflowY: "auto" }}>
        {/* Bull / Bear / Disagreement — truncated with expand */}
        {hasSummary && (
          <div style={{ display: "grid", gap: 2, fontSize: 12, padding: "8px 10px", background: "var(--bg-panel-soft)", borderRadius: 8 }}>
            {summary!.bull_case && <TruncatedLine label="Bull" color="var(--buy)" text={summary!.bull_case} />}
            {summary!.bear_case && <TruncatedLine label="Bear" color="var(--sell)" text={summary!.bear_case} />}
            {summary!.key_disagreement && <TruncatedLine label="Disagree" color="var(--warn)" text={summary!.key_disagreement} />}
          </div>
        )}

        {/* Thesis */}
        {rec.thesis && (
          <div style={{ fontSize: 13, color: "var(--text-soft)", lineHeight: 1.5, borderLeft: "2px solid var(--line)", paddingLeft: 10 }}>
            {rec.thesis}
          </div>
        )}

        {/* Price levels */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          <Level label="Entry" price={rec.entry_price} logic={rec.entry_logic} color="var(--text)" />
          <Level label="Target" price={rec.target_price} logic={rec.target_logic} color="var(--buy)" />
          <Level label="Stop" price={rec.stop_price} logic={rec.stop_logic} color="var(--sell)" />
        </div>

        {/* Action row: shares + buttons on same line */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", paddingTop: 4, borderTop: "1px solid var(--line)" }}>
          {(canReady || canApprove) && action !== "PASS" && (
            <>
              <input
                type="number" value={shares} onChange={(e) => setShares(Number(e.target.value))} min={1}
                style={{ width: 60, padding: "5px 8px", borderRadius: 6, border: "1px solid var(--line)", background: "var(--bg)", color: "var(--text)", fontSize: 13, fontWeight: 600, textAlign: "center" }}
              />
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                {rec.entry_price ? `~$${(shares * rec.entry_price).toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "sh"}
              </span>
            </>
          )}
          {canReady && <button className="btn btn-accent" style={{ fontSize: 11 }} onClick={() => onApproveAndExecute(shares)}>Approve & Execute</button>}
          {canApprove && <button className="btn btn-accent" style={{ fontSize: 11 }} onClick={() => { onApprove(shares); setTimeout(onExecute, 500); }}>Approve & Execute</button>}
          {canExecute && <button className="btn btn-warn" style={{ fontSize: 11 }} onClick={onExecute}>Execute</button>}
          {canReject && <button className="btn btn-danger" style={{ fontSize: 11 }} onClick={onReject}>Reject</button>}
        </div>
      </div>
    </div>
  );
}

function Level({ label, price, logic, color }: { label: string; price?: number | null; logic?: string | null; color: string }) {
  return (
    <div data-tooltip={logic ?? ""}>
      <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
      <div style={{ fontSize: 15, fontWeight: 600, color, fontVariantNumeric: "tabular-nums" }}>{price != null ? `$${price.toFixed(2)}` : "\u2014"}</div>
      {logic && <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 1, lineHeight: 1.3 }}>{logic}</div>}
    </div>
  );
}

function TruncatedLine({ label, color, text }: { label: string; color: string; text: string }) {
  const short = text.length > 80;
  return (
    <details style={{ fontSize: 12 }}>
      <summary style={{ cursor: short ? "pointer" : "default", listStyle: short ? undefined : "none" }}>
        <span style={{ color, fontWeight: 600 }}>{label}:</span>{" "}
        <span style={{ color: "var(--text-soft)" }}>{short ? text.slice(0, 80) + "..." : text}</span>
      </summary>
      {short && <div style={{ color: "var(--text-soft)", padding: "4px 0 4px 16px" }}>{text}</div>}
    </details>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    observing: { label: "Observing", cls: "badge-muted" },
    under_discussion: { label: "Analysing", cls: "badge-accent" },
    draft_recommendation: { label: "Draft", cls: "badge-accent" },
    awaiting_user_feedback: { label: "Review", cls: "badge-warn" },
    awaiting_user_approval: { label: "Approve?", cls: "badge-warn" },
    approved: { label: "Approved", cls: "badge-accent" },
    rejected: { label: "Rejected", cls: "badge-danger" },
    submitted: { label: "Submitted", cls: "badge-accent" },
    filled: { label: "Filled", cls: "badge-accent" },
    closed: { label: "Closed", cls: "badge-muted" },
  };
  const s = map[status] ?? { label: status, cls: "badge-muted" };
  return <span className={`badge ${s.cls}`}>{s.label}</span>;
}
