import { Recommendation } from "@/lib/types";

type Props = {
  recommendation?: Recommendation | null;
  onReady: () => void;
  onApprove: () => void;
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
  BUY: "var(--buy)",
  SELL: "var(--sell)",
  SHORT: "var(--warn)",
  COVER: "var(--accent)",
  PASS: "var(--text-muted)",
};

const STATUS_LABELS: Record<string, { label: string; className: string }> = {
  observing: { label: "Observing", className: "badge-muted" },
  under_discussion: { label: "Discussing", className: "badge-accent" },
  draft_recommendation: { label: "Draft", className: "badge-accent" },
  awaiting_user_feedback: { label: "Review & Discuss", className: "badge-warn" },
  awaiting_user_approval: { label: "Ready for Approval", className: "badge-warn" },
  approved: { label: "Approved", className: "badge-accent" },
  rejected: { label: "Rejected", className: "badge-danger" },
  submitted: { label: "Submitted", className: "badge-accent" },
  filled: { label: "Filled", className: "badge-accent" },
  closed: { label: "Closed", className: "badge-muted" },
};

export function RecommendationCard({ recommendation, onReady, onApprove, onExecute, onReject }: Props) {
  if (!recommendation) {
    return (
      <div className="panel">
        <div className="panel-header">Recommendation</div>
        <div className="panel-body" style={{ color: "var(--text-muted)", padding: 24, textAlign: "center" }}>
          Select an event or recommendation from the inbox to see details here.
        </div>
      </div>
    );
  }

  const action = recommendation.direction ?? "PASS";
  const actionColor = ACTION_COLORS[action] ?? "var(--text)";
  const status = STATUS_LABELS[recommendation.status] ?? { label: recommendation.status, className: "badge-muted" };
  const canReady = recommendation.status === "awaiting_user_feedback";
  const canApprove = recommendation.status === "awaiting_user_approval";
  const canExecute = recommendation.status === "approved";
  const canReject = ["awaiting_user_feedback", "awaiting_user_approval"].includes(recommendation.status);

  return (
    <div className="panel">
      <div className="panel-header">
        <span>Recommendation</span>
        <span className={`badge ${status.className}`}>{status.label}</span>
      </div>
      <div className="panel-body" style={{ display: "grid", gap: 14 }}>
        {/* Action + Symbol */}
        <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
          <span
            data-tooltip={ACTION_TOOLTIPS[action]}
            style={{ fontSize: 22, fontWeight: 700, color: actionColor }}
          >
            {action}
          </span>
          <span style={{ fontSize: 22, fontWeight: 700 }}>{recommendation.symbol}</span>
          {recommendation.conviction != null && (
            <span style={{ fontSize: 13, color: "var(--text-soft)", marginLeft: "auto" }}>
              Conviction {recommendation.conviction}/10
            </span>
          )}
        </div>

        {/* Thesis */}
        {recommendation.thesis && (
          <div style={{ fontSize: 13, color: "var(--text-soft)", lineHeight: 1.6, borderLeft: "2px solid var(--line)", paddingLeft: 12 }}>
            {recommendation.thesis}
          </div>
        )}

        {/* Price levels */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          <PriceLevel label="Entry" price={recommendation.entry_price} logic={recommendation.entry_logic} color="var(--text)" />
          <PriceLevel label="Target" price={recommendation.target_price} logic={recommendation.target_logic} color="var(--buy)" />
          <PriceLevel label="Stop" price={recommendation.stop_price} logic={recommendation.stop_logic} color="var(--sell)" />
        </div>

        {/* Action buttons */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", paddingTop: 4 }}>
          {canReady && <button className="btn btn-accent" onClick={onReady}>Ready for Approval</button>}
          {canApprove && <button className="btn btn-accent" onClick={onApprove}>Approve</button>}
          {canExecute && <button className="btn btn-warn" onClick={onExecute}>Execute</button>}
          {canReject && <button className="btn btn-danger" onClick={onReject}>Reject</button>}
          {!canReady && !canApprove && !canExecute && !canReject && (
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>No actions available in this state.</span>
          )}
        </div>
      </div>
    </div>
  );
}

function PriceLevel({ label, price, logic, color }: { label: string; price?: number | null; logic?: string | null; color: string }) {
  return (
    <div data-tooltip={logic ?? ""}>
      <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 600, color, fontVariantNumeric: "tabular-nums" }}>
        {price != null ? `$${price.toFixed(2)}` : "—"}
      </div>
      {logic && <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2, lineHeight: 1.4 }}>{logic}</div>}
    </div>
  );
}
