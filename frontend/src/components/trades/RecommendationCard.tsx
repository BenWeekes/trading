import { Recommendation } from "@/lib/types";

type Props = {
  recommendation?: Recommendation | null;
  onReady: () => void;
  onApprove: () => void;
  onExecute: () => void;
  onReject: () => void;
};

const TOOLTIP_TEXT: Record<string, string> = {
  BUY: "BUY opens or adds to a long position.",
  SELL: "SELL reduces or closes an existing long position.",
  SHORT: "SHORT opens or adds to a short position.",
  COVER: "COVER reduces or closes a short position.",
  PASS: "PASS means no trade should be taken now.",
};

export function RecommendationCard({ recommendation, onReady, onApprove, onExecute, onReject }: Props) {
  if (!recommendation) {
    return (
      <section style={{ border: "1px solid var(--line)", borderRadius: 20, background: "var(--bg-panel)", padding: 16 }}>
        No active recommendation selected.
      </section>
    );
  }

  const action = recommendation.direction ?? "PASS";
  const canReady = recommendation.status === "awaiting_user_feedback";
  const canApprove = recommendation.status === "awaiting_user_approval";
  const canExecute = recommendation.status === "approved";
  const canReject = recommendation.status === "awaiting_user_feedback" || recommendation.status === "awaiting_user_approval";
  return (
    <section style={{ border: "1px solid var(--line)", borderRadius: 20, background: "var(--bg-panel)", padding: 18, display: "grid", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <strong style={{ fontSize: 20 }}>{action} {recommendation.symbol}</strong>
        <span title={TOOLTIP_TEXT[action]} style={{ color: "var(--text-soft)", fontSize: 12, cursor: "help" }}>
          {action}
        </span>
      </div>
      <div>{recommendation.thesis ?? "No thesis yet."}</div>
      <div style={{ display: "grid", gap: 8, fontSize: 14 }}>
        <div title={recommendation.entry_logic ?? ""}>Entry: {recommendation.entry_price ?? "-"} </div>
        <div title={recommendation.stop_logic ?? ""}>Stop: {recommendation.stop_price ?? "-"} </div>
        <div title={recommendation.target_logic ?? ""}>Target: {recommendation.target_price ?? "-"} </div>
        <div>Conviction: {recommendation.conviction ?? "-"}/10</div>
        <div>Status: {recommendation.status}</div>
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {canReady ? (
          <button onClick={onReady} style={buttonStyle("var(--accent)")}>Ready for Approval</button>
        ) : null}
        <button onClick={onApprove} disabled={!canApprove} style={buttonStyle("var(--accent)", !canApprove)}>Approve</button>
        <button onClick={onExecute} disabled={!canExecute} style={buttonStyle("var(--warn)", !canExecute)}>Execute</button>
        <button onClick={onReject} disabled={!canReject} style={buttonStyle("var(--danger)", !canReject)}>Reject</button>
      </div>
    </section>
  );
}

function buttonStyle(color: string, disabled = false) {
  return {
    border: `1px solid ${color}`,
    background: "transparent",
    color,
    borderRadius: 12,
    padding: "10px 14px",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.45 : 1,
  } as const;
}
