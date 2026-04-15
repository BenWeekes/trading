"use client";

import { EventItem } from "@/lib/types";

type Props = {
  event: EventItem | null;
  onClose: () => void;
};

export function NewsReader({ event, onClose }: Props) {
  if (!event) return null;

  const typeColors: Record<string, string> = {
    news: "var(--accent)", macro: "var(--warn)", price_alert: "var(--sell)", earnings: "var(--buy)",
  };

  return (
    <div className="panel" style={{ flexShrink: 0 }}>
      <div className="panel-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="badge" style={{
            background: `${typeColors[event.type] ?? "var(--text-muted)"}20`,
            color: typeColors[event.type] ?? "var(--text-muted)",
          }}>{event.type}</span>
          {event.symbol && <strong>{event.symbol}</strong>}
          <span style={{ color: "var(--text-muted)", fontSize: 11 }}>{event.source}</span>
        </div>
        <button className="btn" onClick={onClose} style={{ fontSize: 10, padding: "2px 8px" }}>✕</button>
      </div>
      <div className="panel-body" style={{ maxHeight: 120, overflowY: "auto" }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>{event.headline}</div>
        {event.body_excerpt && (
          <div style={{ fontSize: 13, color: "var(--text-soft)", lineHeight: 1.6 }}>{event.body_excerpt}</div>
        )}
        <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 6 }}>
          {new Date(event.timestamp).toLocaleString()}
        </div>
      </div>
    </div>
  );
}
