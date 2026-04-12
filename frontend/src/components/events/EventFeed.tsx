import { EventItem } from "@/lib/types";

type Props = {
  events: EventItem[];
  activeSymbol?: string | null;
  onSelect: (event: EventItem) => void;
};

export function EventFeed({ events, activeSymbol, onSelect }: Props) {
  return (
    <section style={{ display: "grid", gap: 12 }}>
      {events.map((event) => {
        const active = event.symbol && event.symbol === activeSymbol;
        return (
          <button
            key={event.id}
            onClick={() => onSelect(event)}
            style={{
              textAlign: "left",
              background: active ? "rgba(113, 217, 182, 0.12)" : "var(--bg-panel)",
              border: `1px solid ${active ? "rgba(113, 217, 182, 0.45)" : "var(--line)"}`,
              borderRadius: 18,
              padding: 16,
              color: "inherit",
              cursor: "pointer",
              boxShadow: "var(--shadow)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <strong>{event.symbol ?? event.type.toUpperCase()}</strong>
              <span style={{ color: "var(--text-soft)", fontSize: 12 }}>{new Date(event.timestamp).toLocaleTimeString()}</span>
            </div>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>{event.headline}</div>
            <div style={{ color: "var(--text-soft)", fontSize: 13 }}>{event.body_excerpt}</div>
          </button>
        );
      })}
    </section>
  );
}
