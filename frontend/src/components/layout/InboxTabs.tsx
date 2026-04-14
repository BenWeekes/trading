"use client";

import { useState } from "react";
import { EventItem, Recommendation } from "@/lib/types";

type Props = {
  events: EventItem[];
  recommendations: Recommendation[];
  activeSymbol?: string | null;
  activeTab?: "events" | "recs";
  onTabChange?: (tab: "events" | "recs") => void;
  onSelectEvent: (event: EventItem) => void;
  onSelectRecommendation: (rec: Recommendation) => void;
};

function recForSymbol(recs: Recommendation[], symbol?: string | null): Recommendation | undefined {
  return symbol ? recs.find((r) => r.symbol === symbol) : undefined;
}

const PENDING = new Set(["awaiting_user_feedback", "awaiting_user_approval", "draft_recommendation", "under_discussion"]);

const DIR_COLORS: Record<string, string> = {
  BUY: "var(--buy)", SELL: "var(--sell)", SHORT: "var(--warn)", COVER: "var(--accent)", PASS: "var(--text-muted)",
};

export function InboxTabs({ events, recommendations, activeSymbol, activeTab: externalTab, onTabChange, onSelectEvent, onSelectRecommendation }: Props) {
  const [internalTab, setInternalTab] = useState<"events" | "recs">("events");
  const tab = externalTab ?? internalTab;
  const setTab = (t: "events" | "recs") => { setInternalTab(t); onTabChange?.(t); };
  const pendingCount = recommendations.filter((r) => PENDING.has(r.status) && r.direction && r.direction !== "PASS").length;

  // Dedupe events: show only the latest event per symbol
  const deduped = events.reduce<EventItem[]>((acc, ev) => {
    const key = ev.symbol ?? ev.id;
    if (!acc.find((e) => (e.symbol ?? e.id) === key)) acc.push(ev);
    return acc;
  }, []);

  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
      {/* Tab bar */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--line)" }}>
        <TabButton active={tab === "events"} onClick={() => setTab("events")} count={deduped.length}>
          Events
        </TabButton>
        <TabButton active={tab === "recs"} onClick={() => setTab("recs")} count={recommendations.filter((r) => r.direction && r.direction !== "PASS").length} badge={pendingCount || undefined}>
          Recommendations
        </TabButton>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "6px" }}>
        {tab === "events" ? (
          deduped.length === 0 ? (
            <Empty>No events yet. Run a scan or trigger a random event.</Empty>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {deduped.map((ev) => {
                const rec = recForSymbol(recommendations, ev.symbol);
                const dir = rec?.direction;
                const dirColor = DIR_COLORS[dir ?? ""] ?? "var(--text-muted)";
                return (
                  <InboxItem key={ev.id} active={ev.symbol === activeSymbol} onClick={() => onSelectEvent(ev)}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                      <strong style={{ fontSize: 13 }}>
                        {ev.symbol ?? ev.type.toUpperCase()}
                        {dir && <span style={{ color: dirColor, fontWeight: 600 }}>: {dir}</span>}
                      </strong>
                      <span style={{ fontSize: 10, color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                        {new Date(ev.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-soft)", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ev.headline}</div>
                  </InboxItem>
                );
              })}
            </div>
          )
        ) : (
          recommendations.filter((r) => r.direction && r.direction !== "PASS").length === 0 ? (
            <Empty>No actionable recommendations yet.</Empty>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {[...recommendations]
                .filter((r) => r.direction && r.direction !== "PASS")
                .sort((a, b) => (PENDING.has(a.status) ? 0 : 1) - (PENDING.has(b.status) ? 0 : 1))
                .map((rec) => (
                  <InboxItem key={rec.id} active={rec.symbol === activeSymbol} onClick={() => onSelectRecommendation(rec)}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                      <strong style={{ fontSize: 13 }}>
                        {rec.symbol}<span style={{ color: DIR_COLORS[rec.direction ?? ""] ?? "var(--text-muted)" }}>: {rec.direction ?? "WATCH"}</span>
                      </strong>
                      <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                        {rec.conviction ? `${rec.conviction}/10` : ""}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-soft)", marginTop: 2, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as const, overflow: "hidden" }}>
                      {rec.thesis ?? rec.strategy_type}
                    </div>
                  </InboxItem>
                ))}
            </div>
          )
        )}
      </div>
    </div>
  );
}

function TabButton({ active, onClick, count, badge, children }: {
  active: boolean; onClick: () => void; count: number; badge?: number; children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1, padding: "10px 12px", background: "transparent", border: "none",
        borderBottom: active ? "2px solid var(--accent)" : "2px solid transparent",
        color: active ? "var(--text)" : "var(--text-muted)",
        fontSize: 12, fontWeight: 600, cursor: "pointer",
        display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
      }}
    >
      {children}
      <span style={{ fontSize: 10, color: "var(--text-muted)" }}>({count})</span>
      {badge ? <span className="badge badge-warn" style={{ fontSize: 9, padding: "1px 5px" }}>{badge}</span> : null}
    </button>
  );
}

function InboxItem({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        textAlign: "left", width: "100%", padding: "10px 12px", borderRadius: 8,
        background: active ? "var(--accent-glow)" : "transparent",
        border: active ? "1px solid var(--accent-border)" : "1px solid transparent",
        color: "inherit", cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <div style={{ color: "var(--text-muted)", fontSize: 12, padding: 16, textAlign: "center" }}>{children}</div>;
}
