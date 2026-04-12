"use client";

import { useState } from "react";
import { Recommendation, Summary } from "@/lib/types";

type Props = {
  recommendation?: Recommendation | null;
  summary?: Summary | null;
  onReady: () => void;
  onApprove: (shares: number) => void;
  onExecute: () => void;
  onReject: () => void;
};

const ACTION_TOOLTIPS: Record<string, string> = {
  BUY: "Open or add to a long position",
  SELL: "Reduce or close an existing long position",
  SHORT: "Open or add to a short position",
  COVER: "Reduce or close a short position",
  PASS: "No trade — the best action is no action right now",
};

const ACTION_COLORS: Record<string, string> = {
  BUY: "var(--buy)", SELL: "var(--sell)", SHORT: "var(--warn)",
  COVER: "var(--accent)", PASS: "var(--text-muted)",
};

const STATUS_MAP: Record<string, { label: string; cls: string }> = {
  observing: { label: "Observing", cls: "badge-muted" },
  under_discussion: { label: "Roles Analysing", cls: "badge-accent" },
  draft_recommendation: { label: "Draft", cls: "badge-accent" },
  awaiting_user_feedback: { label: "Review & Discuss", cls: "badge-warn" },
  awaiting_user_approval: { label: "Approve or Reject", cls: "badge-warn" },
  approved: { label: "Approved", cls: "badge-accent" },
  rejected: { label: "Rejected", cls: "badge-danger" },
  submitted: { label: "Submitted", cls: "badge-accent" },
  filled: { label: "Filled", cls: "badge-accent" },
  closed: { label: "Closed", cls: "badge-muted" },
};

export function RecommendationCard({ recommendation, summary, onReady, onApprove, onExecute, onReject }: Props) {
  const suggestedShares = recommendation?.position_size_shares ?? recommendation?.conviction ?? 10;
  const [editShares, setEditShares] = useState<number>(suggestedShares);

  // Reset shares when recommendation changes
  const recId = recommendation?.id;

  if (!recommendation) {
    return (
      <div className="panel">
        <div className="panel-header">Recommendation</div>
        <div className="panel-body" style={{ color: "var(--text-muted)", padding: 24, textAlign: "center" }}>
          Select an event or recommendation to see the analysis here.
        </div>
      </div>
    );
  }

  const action = recommendation.direction ?? "PASS";
  const actionColor = ACTION_COLORS[action] ?? "var(--text)";
  const status = STATUS_MAP[recommendation.status] ?? { label: recommendation.status, cls: "badge-muted" };
  const canApprove = ["awaiting_user_feedback", "awaiting_user_approval"].includes(recommendation.status);
  const canExecute = recommendation.status === "approved";
  const canReject = ["awaiting_user_feedback", "awaiting_user_approval"].includes(recommendation.status);
  const hasSummary = summary?.bull_case || summary?.bear_case;

  return (
    <div className="panel">
      {/* Header */}
      <div className="panel-header">
        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span data-tooltip={ACTION_TOOLTIPS[action]} style={{ color: actionColor, fontWeight: 700, fontSize: 14, letterSpacing: 0 }}>
            {action}
          </span>
          <span style={{ fontWeight: 700, fontSize: 14, letterSpacing: 0 }}>{recommendation.symbol}</span>
        </span>
        <span className={`badge ${status.cls}`}>{status.label}</span>
      </div>

      <div className="panel-body" style={{ display: "grid", gap: 12 }}>
        {/* Conviction */}
        {recommendation.conviction != null && (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em" }}>Conviction</span>
            <ConvictionBar value={recommendation.conviction} />
            <span style={{ fontSize: 13, fontWeight: 600 }}>{recommendation.conviction}/10</span>
          </div>
        )}

        {/* Summary (bull/bear/disagreement) */}
        {hasSummary && (
          <div style={{ display: "grid", gap: 6, fontSize: 12, padding: "8px 10px", background: "var(--bg-panel-soft)", borderRadius: 8 }}>
            <div><span style={{ color: "var(--buy)", fontWeight: 600 }}>Bull:</span> <span style={{ color: "var(--text-soft)" }}>{summary!.bull_case}</span></div>
            <div><span style={{ color: "var(--sell)", fontWeight: 600 }}>Bear:</span> <span style={{ color: "var(--text-soft)" }}>{summary!.bear_case}</span></div>
            {summary!.key_disagreement && (
              <div><span style={{ color: "var(--warn)", fontWeight: 600 }}>Disagreement:</span> <span style={{ color: "var(--text-soft)" }}>{summary!.key_disagreement}</span></div>
            )}
          </div>
        )}

        {/* Thesis */}
        {recommendation.thesis && (
          <div style={{ fontSize: 13, color: "var(--text-soft)", lineHeight: 1.6, borderLeft: "2px solid var(--line)", paddingLeft: 10 }}>
            {recommendation.thesis}
          </div>
        )}

        {/* Price levels */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          <PriceLevel label="Entry" price={recommendation.entry_price} logic={recommendation.entry_logic} color="var(--text)" />
          <PriceLevel label="Target" price={recommendation.target_price} logic={recommendation.target_logic} color="var(--buy)" />
          <PriceLevel label="Stop" price={recommendation.stop_price} logic={recommendation.stop_logic} color="var(--sell)" />
        </div>

        {/* Editable shares for approval */}
        {canApprove && action !== "PASS" && (
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0" }}>
            <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em" }}>Shares</span>
            <input
              type="number"
              value={editShares}
              onChange={(e) => setEditShares(Number(e.target.value))}
              min={1}
              style={{
                width: 80, padding: "6px 10px", borderRadius: 8,
                border: "1px solid var(--line)", background: "var(--bg)",
                color: "var(--text)", fontSize: 14, fontWeight: 600,
                textAlign: "center", fontVariantNumeric: "tabular-nums",
              }}
            />
            {recommendation.entry_price && (
              <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                ~ ${(editShares * recommendation.entry_price).toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </span>
            )}
          </div>
        )}

        {/* Action buttons */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {canApprove && <button className="btn btn-accent" onClick={() => onApprove(editShares)}>Approve ({editShares} sh)</button>}
          {canExecute && <button className="btn btn-warn" onClick={onExecute}>Execute Order</button>}
          {canReject && <button className="btn btn-danger" onClick={onReject}>Reject</button>}
        </div>
      </div>
    </div>
  );
}

function PriceLevel({ label, price, logic, color }: { label: string; price?: number | null; logic?: string | null; color: string }) {
  return (
    <div data-tooltip={logic ?? ""}>
      <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 1 }}>{label}</div>
      <div style={{ fontSize: 15, fontWeight: 600, color, fontVariantNumeric: "tabular-nums" }}>
        {price != null ? `$${price.toFixed(2)}` : "\u2014"}
      </div>
      {logic && <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 1, lineHeight: 1.3 }}>{logic}</div>}
    </div>
  );
}

function ConvictionBar({ value }: { value: number }) {
  return (
    <div style={{ display: "flex", gap: 2, flex: 1 }}>
      {Array.from({ length: 10 }, (_, i) => (
        <div key={i} style={{
          flex: 1, height: 6, borderRadius: 2,
          background: i < value
            ? value >= 7 ? "var(--buy)" : value >= 4 ? "var(--warn)" : "var(--sell)"
            : "var(--bg-panel-soft)",
        }} />
      ))}
    </div>
  );
}
