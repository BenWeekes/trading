"use client";

import { useEffect, useRef, useState } from "react";
import { EventItem, Recommendation } from "@/lib/types";

type TabId = "earnings" | "ai" | "news";

type Props = {
  events: EventItem[];
  recommendations: Recommendation[];
  companyNames?: Record<string, string>;
  activeSymbol?: string | null;
  activeTab?: TabId;
  onTabChange?: (tab: TabId) => void;
  onSelectEvent: (event: EventItem) => void;
  onSelectRecommendation: (rec: Recommendation) => void;
  onSelectNews?: (event: EventItem) => void;
  scrollCommand?: { direction: "up" | "down"; nonce: number } | null;
};

const PENDING = new Set(["awaiting_user_feedback", "awaiting_user_approval", "draft_recommendation", "under_discussion"]);
const DIR_COLORS: Record<string, string> = {
  BUY: "var(--buy)", SELL: "var(--sell)", SHORT: "var(--warn)", COVER: "var(--accent)", PASS: "var(--text-muted)",
};

function dedupeBySymbol(items: Recommendation[]) {
  const seen = new Set<string>();
  const out: Recommendation[] = [];
  for (const item of items) {
    if (seen.has(item.symbol)) continue;
    seen.add(item.symbol);
    out.push(item);
  }
  return out;
}

export function InboxTabs({ events, recommendations, companyNames = {}, activeSymbol, activeTab: externalTab, onTabChange, onSelectEvent, onSelectRecommendation, onSelectNews, scrollCommand }: Props) {
  const [internalTab, setInternalTab] = useState<TabId>("earnings");
  const scrollRef = useRef<HTMLDivElement>(null);
  const tab = externalTab ?? internalTab;
  const setTab = (t: TabId) => { setInternalTab(t); onTabChange?.(t); };

  useEffect(() => {
    if (!scrollCommand || !scrollRef.current) return;
    scrollRef.current.scrollBy({ top: scrollCommand.direction === "down" ? 240 : -240, behavior: "smooth" });
  }, [scrollCommand]);

  // Split events
  const earningsEvents = events.filter((e) => e.type === "earnings");
  const newsEvents = events.filter((e) => e.type !== "earnings" && e.type !== "price_alert");

  // AI recs — actionable only
  const aiRecs = dedupeBySymbol(recommendations.filter((r) => r.direction && r.direction !== "PASS"));
  const pendingCount = aiRecs.filter((r) => PENDING.has(r.status)).length;

  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
      {/* Tab bar */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--line)" }}>
        <TabBtn active={tab === "earnings"} onClick={() => setTab("earnings")} count={earningsEvents.length}>Earnings</TabBtn>
        <TabBtn active={tab === "ai"} onClick={() => setTab("ai")} count={aiRecs.length} badge={pendingCount || undefined}>AI</TabBtn>
        <TabBtn active={tab === "news"} onClick={() => setTab("news")} count={newsEvents.length}>News</TabBtn>
      </div>

      {/* Content */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: "6px" }}>
        {tab === "earnings" && (
          earningsEvents.length === 0 ? (
            <Empty>Earnings events appear here automatically when stocks report. No scan needed.</Empty>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {earningsEvents.map((ev) => {
                const rec = recommendations.find((r) => r.symbol === ev.symbol);
                const dir = rec?.direction;
                return (
                  <InboxItem key={ev.id} active={ev.symbol === activeSymbol} onClick={() => onSelectEvent(ev)}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                      <div>
                        <strong style={{ fontSize: 13 }}>
                          {ev.symbol ?? ev.type.toUpperCase()}
                          {dir && <span style={{ color: DIR_COLORS[dir] ?? "var(--text-muted)" }}>: {dir}</span>}
                        </strong>
                        {ev.symbol && companyNames[ev.symbol] && (
                          <div style={{ fontSize: 9, color: "var(--text-muted)" }}>{companyNames[ev.symbol]}</div>
                        )}
                      </div>
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
        )}

        {tab === "ai" && (
          aiRecs.length === 0 ? (
            <Empty>AI recommendations appear here after earnings analysis completes.</Empty>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {[...aiRecs]
                .sort((a, b) => (PENDING.has(a.status) ? 0 : 1) - (PENDING.has(b.status) ? 0 : 1))
                .map((rec) => (
                  <InboxItem key={rec.id} active={rec.symbol === activeSymbol} onClick={() => onSelectRecommendation(rec)}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                      <div>
                        <strong style={{ fontSize: 13 }}>
                          {rec.symbol}<span style={{ color: DIR_COLORS[rec.direction ?? ""] ?? "var(--text-muted)" }}>: {rec.direction ?? "?"}</span>
                        </strong>
                        {companyNames[rec.symbol] && (
                          <div style={{ fontSize: 9, color: "var(--text-muted)" }}>{companyNames[rec.symbol]}</div>
                        )}
                      </div>
                      <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{rec.conviction ? `${rec.conviction}/10` : ""}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-soft)", marginTop: 2, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as const, overflow: "hidden" }}>
                      {rec.thesis ?? rec.strategy_type}
                    </div>
                  </InboxItem>
                ))}
            </div>
          )
        )}

        {tab === "news" && (
          newsEvents.length === 0 ? (
            <Empty>Market news and alerts stream in automatically.</Empty>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {newsEvents.map((ev) => (
                <button key={ev.id} onClick={() => onSelectNews?.(ev)} style={{
                  textAlign: "left", width: "100%", padding: "8px 12px", borderRadius: 8,
                  background: "transparent", border: "none", borderBottom: "1px solid var(--line)",
                  color: "inherit", cursor: "pointer",
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                    <div>
                      <span style={{ fontSize: 12, fontWeight: 600 }}>{ev.symbol ?? ev.type}</span>
                      {ev.symbol && companyNames[ev.symbol] && (
                        <div style={{ fontSize: 9, color: "var(--text-muted)" }}>{companyNames[ev.symbol]}</div>
                      )}
                    </div>
                    <span style={{ fontSize: 10, color: "var(--text-muted)", whiteSpace: "nowrap" }}>{ev.source}</span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-soft)", marginTop: 2 }}>{ev.headline}</div>
                </button>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  );
}

function TabBtn({ active, onClick, count, badge, children }: {
  active: boolean; onClick: () => void; count: number; badge?: number; children: React.ReactNode;
}) {
  return (
    <button onClick={onClick} style={{
      flex: 1, padding: "8px 4px", background: "transparent", border: "none",
      borderBottom: active ? "2px solid var(--accent)" : "2px solid transparent",
      color: active ? "var(--text)" : "var(--text-muted)",
      fontSize: 11, fontWeight: 600, cursor: "pointer",
      display: "flex", alignItems: "center", justifyContent: "center", gap: 4,
    }}>
      {children}
      <span style={{ fontSize: 10, color: "var(--text-muted)" }}>({count})</span>
      {badge ? <span className="badge badge-warn" style={{ fontSize: 9, padding: "1px 5px" }}>{badge}</span> : null}
    </button>
  );
}

function InboxItem({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{
      textAlign: "left", width: "100%", padding: "8px 12px", borderRadius: 8,
      background: active ? "var(--accent-glow)" : "transparent",
      border: active ? "1px solid var(--accent-border)" : "1px solid transparent",
      color: "inherit", cursor: "pointer",
    }}>
      {children}
    </button>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <div style={{ color: "var(--text-muted)", fontSize: 12, padding: 16, textAlign: "center" }}>{children}</div>;
}
