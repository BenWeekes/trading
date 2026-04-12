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

export function DeskInbox({
  events,
  recommendations,
  positions,
  activeSymbol,
  onSelectEvent,
  onSelectRecommendation,
  onSelectPosition,
}: Props) {
  return (
    <section
      style={{
        border: "1px solid var(--line)",
        borderRadius: 20,
        background: "var(--bg-panel)",
        padding: 16,
        display: "grid",
        gap: 16,
        minHeight: 0,
      }}
    >
      <InboxSection
        title="News and Events"
        empty="No events yet."
        items={events}
        renderItem={(event) => (
          <InboxButton
            key={event.id}
            active={Boolean(event.symbol && event.symbol === activeSymbol)}
            title={event.symbol ?? event.type.toUpperCase()}
            subtitle={event.headline}
            meta={new Date(event.timestamp).toLocaleTimeString()}
            detail={event.body_excerpt ?? event.source ?? ""}
            onClick={() => onSelectEvent(event)}
          />
        )}
      />

      <InboxSection
        title="Recommendations"
        empty="No recommendations yet."
        items={recommendations}
        renderItem={(recommendation) => (
          <InboxButton
            key={recommendation.id}
            active={recommendation.symbol === activeSymbol}
            title={`${recommendation.direction ?? "WATCH"} ${recommendation.symbol}`}
            subtitle={recommendation.thesis ?? recommendation.strategy_type}
            meta={recommendation.status.replace(/_/g, " ")}
            detail={`Conviction ${recommendation.conviction ?? "-"} / 10`}
            onClick={() => onSelectRecommendation(recommendation)}
          />
        )}
      />

      <InboxSection
        title="Open Positions"
        empty="No open paper positions."
        items={positions}
        renderItem={(position) => (
          <InboxButton
            key={position.id}
            active={position.symbol === activeSymbol}
            title={`${position.direction} ${position.symbol}`}
            subtitle={`$${Number(position.current_price ?? 0).toFixed(2)} current`}
            meta={`${position.shares ?? 0} sh`}
            detail={`PnL ${Number(position.unrealized_pnl ?? 0).toFixed(2)}`}
            onClick={() => onSelectPosition(position)}
          />
        )}
      />
    </section>
  );
}

function InboxSection<T>({
  title,
  items,
  empty,
  renderItem,
}: {
  title: string;
  items: T[];
  empty: string;
  renderItem: (item: T) => ReactNode;
}) {
  return (
    <div style={{ display: "grid", gap: 10, minHeight: 0 }}>
      <div style={{ fontSize: 12, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--text-soft)" }}>
        {title}
      </div>
      <div style={{ display: "grid", gap: 8, maxHeight: 220, overflowY: "auto", paddingRight: 4 }}>
        {items.length === 0 ? <div style={{ color: "var(--text-soft)", fontSize: 14 }}>{empty}</div> : items.map(renderItem)}
      </div>
    </div>
  );
}

function InboxButton({
  active,
  title,
  subtitle,
  meta,
  detail,
  onClick,
}: {
  active: boolean;
  title: string;
  subtitle: string;
  meta: string;
  detail: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        textAlign: "left",
        background: active ? "rgba(113, 217, 182, 0.12)" : "var(--bg-panel-soft)",
        border: `1px solid ${active ? "rgba(113, 217, 182, 0.45)" : "var(--line)"}`,
        borderRadius: 16,
        padding: 14,
        color: "inherit",
        cursor: "pointer",
        display: "grid",
        gap: 6,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <strong>{title}</strong>
        <span style={{ color: "var(--text-soft)", fontSize: 12 }}>{meta}</span>
      </div>
      <div style={{ fontSize: 14 }}>{subtitle}</div>
      <div style={{ color: "var(--text-soft)", fontSize: 12 }}>{detail}</div>
    </button>
  );
}
