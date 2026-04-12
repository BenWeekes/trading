import { ReactNode } from "react";
import { EventItem, Position, Recommendation } from "@/lib/types";

type Props = {
  events: EventItem[];
  recommendations: Recommendation[];
  positions: Position[];
  activeSymbol?: string | null;
  onSelectEvent: (event: EventItem) => void;
  onSelectRecommendation: (recommendation: Recommendation) => void;
  onSelectPosition: (position: Position) => void;
};

const PENDING_STATUSES = new Set(["awaiting_user_feedback", "awaiting_user_approval", "draft_recommendation", "under_discussion"]);

export function DeskInbox({
  events, recommendations, positions, activeSymbol,
  onSelectEvent, onSelectRecommendation, onSelectPosition,
}: Props) {
  const pendingCount = recommendations.filter((r) => PENDING_STATUSES.has(r.status)).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Events */}
      <InboxSection title="Events" count={events.length} maxHeight={240}>
        {events.length === 0 ? (
          <Empty>No events yet.</Empty>
        ) : (
          events.map((ev) => (
            <InboxItem
              key={ev.id}
              active={Boolean(ev.symbol && ev.symbol === activeSymbol)}
              onClick={() => onSelectEvent(ev)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <strong style={{ fontSize: 13 }}>{ev.symbol ?? ev.type.toUpperCase()}</strong>
                <span style={{ fontSize: 10, color: "var(--text-muted)", whiteSpace: "nowrap" }}>{new Date(ev.timestamp).toLocaleTimeString()}</span>
              </div>
              <div style={{ fontSize: 12, marginTop: 2 }}>{ev.headline}</div>
            </InboxItem>
          ))
        )}
      </InboxSection>

      {/* Recommendations */}
      <InboxSection title="Recommendations" count={recommendations.length} badge={pendingCount > 0 ? `${pendingCount} pending` : undefined} maxHeight={240}>
        {recommendations.length === 0 ? (
          <Empty>No recommendations yet.</Empty>
        ) : (
          recommendations
            .sort((a, b) => {
              const aP = PENDING_STATUSES.has(a.status) ? 0 : 1;
              const bP = PENDING_STATUSES.has(b.status) ? 0 : 1;
              return aP - bP;
            })
            .map((rec) => (
              <InboxItem
                key={rec.id}
                active={rec.symbol === activeSymbol}
                onClick={() => onSelectRecommendation(rec)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <strong style={{ fontSize: 13 }}>{rec.direction ?? "WATCH"} {rec.symbol}</strong>
                  <span className={`badge ${PENDING_STATUSES.has(rec.status) ? "badge-warn" : "badge-muted"}`}>
                    {rec.status.replace(/_/g, " ")}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: "var(--text-soft)", marginTop: 2 }}>
                  {rec.thesis ? (rec.thesis.length > 60 ? rec.thesis.slice(0, 60) + "..." : rec.thesis) : rec.strategy_type}
                </div>
              </InboxItem>
            ))
        )}
      </InboxSection>

      {/* Positions */}
      <InboxSection title="Open Positions" count={positions.length} maxHeight={180}>
        {positions.length === 0 ? (
          <Empty>No open paper positions.</Empty>
        ) : (
          positions.map((pos) => (
            <InboxItem
              key={pos.id}
              active={pos.symbol === activeSymbol}
              onClick={() => onSelectPosition(pos)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                <strong style={{ fontSize: 13 }}>{pos.symbol}</strong>
                <span style={{
                  fontSize: 12, fontWeight: 600, fontVariantNumeric: "tabular-nums",
                  color: (pos.unrealized_pnl ?? 0) >= 0 ? "var(--buy)" : "var(--sell)",
                }}>
                  {(pos.unrealized_pnl ?? 0) >= 0 ? "+" : ""}${Number(pos.unrealized_pnl ?? 0).toFixed(2)}
                </span>
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 1 }}>
                {pos.shares} sh @ ${Number(pos.entry_price ?? 0).toFixed(2)}
              </div>
            </InboxItem>
          ))
        )}
      </InboxSection>
    </div>
  );
}

function InboxSection({ title, count, badge, maxHeight, children }: {
  title: string; count: number; badge?: string; maxHeight: number; children: ReactNode;
}) {
  return (
    <div className="panel">
      <div className="panel-header">
        <span>{title} <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>({count})</span></span>
        {badge && <span className="badge badge-warn">{badge}</span>}
      </div>
      <div style={{ maxHeight, overflowY: "auto", padding: "8px 8px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {children}
        </div>
      </div>
    </div>
  );
}

function InboxItem({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        textAlign: "left", width: "100%",
        background: active ? "rgba(113, 217, 182, 0.1)" : "transparent",
        border: active ? "1px solid rgba(113, 217, 182, 0.3)" : "1px solid transparent",
        borderRadius: 10, padding: "10px 12px",
        color: "inherit", cursor: "pointer",
        transition: "background 0.1s",
      }}
      onMouseEnter={(e) => { if (!active) (e.currentTarget.style.background = "var(--bg-panel-soft)"); }}
      onMouseLeave={(e) => { if (!active) (e.currentTarget.style.background = "transparent"); }}
    >
      {children}
    </button>
  );
}

function Empty({ children }: { children: ReactNode }) {
  return <div style={{ color: "var(--text-muted)", fontSize: 12, padding: "12px 8px" }}>{children}</div>;
}
