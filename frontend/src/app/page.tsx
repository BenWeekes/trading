"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Header } from "@/components/layout/Header";
import { InboxTabs } from "@/components/layout/InboxTabs";
import { TradePanel } from "@/components/trades/TradePanel";
import { GroupChat } from "@/components/roles/GroupChat";
import { AvatarAndPositions } from "@/components/trades/AvatarAndPositions";
import { useSSE } from "@/hooks/useSSE";
import { api, streamUrl } from "@/lib/api";
import { EventItem, Position, Recommendation, RoleMessage, Summary, TraderAvatarStatus } from "@/lib/types";

export default function Page() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [activeRec, setActiveRec] = useState<Recommendation | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [timeline, setTimeline] = useState<RoleMessage[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [portfolioValue, setPortfolioValue] = useState<number | undefined>();
  const [mode, setMode] = useState("paper");
  const [avatarStatus, setAvatarStatus] = useState<TraderAvatarStatus | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const didInit = useRef(false);

  const load = useCallback(async () => {
    const [ev, rec, pos, port] = await Promise.all([
      api.events(), api.recs(), api.positions(), api.portfolio(),
    ]);
    setEvents(ev.events);
    setRecommendations(rec.recommendations);
    setPositions(pos.positions);
    setPortfolioValue(Number(port.portfolio_value ?? 0));
    setMode(String(port.status ?? "paper"));
    if (!didInit.current && rec.recommendations.length > 0) {
      setActiveRec(rec.recommendations[0]);
      didInit.current = true;
    }
  }, []);

  useEffect(() => { load().catch(console.error); }, [load]);

  const activeRecId = activeRec?.id;
  useEffect(() => {
    if (!activeRecId) return;
    api.rec(activeRecId).then((d) => { setActiveRec(d.recommendation); setSummary(d.summary); setTimeline(d.timeline); }).catch(console.error);
    api.traderAvatarStatus(activeRecId).then(setAvatarStatus).catch(console.error);
  }, [activeRecId]);

  useSSE(streamUrl, useCallback((type: string, payload: unknown) => {
    const p = (typeof payload === "object" && payload) ? payload as Record<string, unknown> : {};

    // Targeted refresh based on event type
    if (type === "recommendation_update" || type === "role_message" || type === "role_query" || type === "summary_update") {
      if (p.recommendation_id === activeRecId && activeRecId) {
        api.rec(activeRecId).then((d) => { setActiveRec(d.recommendation); setSummary(d.summary); setTimeline(d.timeline); }).catch(console.error);
      }
      // Refresh rec list (lightweight)
      api.recs().then((d) => setRecommendations(d.recommendations)).catch(console.error);
    } else if (type === "position_update") {
      api.positions().then((d) => setPositions(d.positions)).catch(console.error);
    } else if (type === "market_event") {
      api.events().then((d) => setEvents(d.events)).catch(console.error);
    }
    // No full load() — only refetch what the event type implies
  }, [activeRecId]));

  useEffect(() => () => { if (debounceRef.current) clearTimeout(debounceRef.current); }, []);

  const sortedTimeline = useMemo(
    () => [...timeline].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()),
    [timeline],
  );

  const hasContent = events.length > 0 || recommendations.length > 0;

  // Handlers
  async function onScan() { await api.scan(); await load(); }
  async function onRandom() {
    const r = await api.randomEvent();
    setActiveRec(r.recommendation); didInit.current = true; await load();
  }
  async function onSend(msg: string) {
    if (!activeRec) {
      console.warn("No active recommendation — cannot send chat");
      return;
    }
    try {
      await api.discuss(activeRec.id, msg);
      const d = await api.rec(activeRec.id);
      setActiveRec(d.recommendation); setTimeline(d.timeline); setSummary(d.summary);
    } catch (err) {
      console.error("Chat send failed:", err);
    }
  }
  async function onApprove(shares: number) {
    if (!activeRec) return;
    await api.approve(activeRec.id, shares); await load();
  }
  async function onExecute() { if (activeRec) { await api.execute(activeRec.id); await load(); } }
  async function onReject() { if (activeRec) { await api.reject(activeRec.id, "User rejected"); await load(); } }
  async function onSell(tradeId: string, symbol: string, shares: number) {
    try {
      const r = await api.sellTrade(tradeId, shares);
      alert(`Sold ${r.shares_sold} sh of ${symbol}. P&L: $${r.pnl.toFixed(2)}`);
      await load();
    } catch (err) {
      alert("Sell failed: " + (err instanceof Error ? err.message : "Unknown error"));
    }
  }

  return (
    <main className="workstation">
      <Header portfolioValue={portfolioValue} mode={mode} onScan={onScan} onRandomEvent={onRandom} />
      {!hasContent ? (
        <EmptyState onScan={onScan} onRandom={onRandom} />
      ) : (
        <div className="workstation-body">
          {/* LEFT — Tabbed Inbox */}
          <div className="column">
            <InboxTabs
              events={events}
              recommendations={recommendations}
              activeSymbol={activeRec?.symbol}
              onSelectEvent={(ev) => {
                const rec = recommendations.find((r) => r.symbol === ev.symbol) ?? null;
                setActiveRec(rec);
              }}
              onSelectRecommendation={setActiveRec}
            />
          </div>

          {/* CENTER — Summary+Buy at top, Chat below */}
          <div className="column">
            <TradePanel
              recommendation={activeRec}
              summary={summary}
              onReady={async () => { if (activeRec) { await api.readyForApproval(activeRec.id); await load(); } }}
              onApprove={onApprove}
              onExecute={onExecute}
              onReject={onReject}
            />
            <GroupChat messages={sortedTimeline} onSend={onSend} activeSymbol={activeRec?.symbol} />
          </div>

          {/* RIGHT — Avatar + Positions */}
          <div className="column">
            <AvatarAndPositions
              positions={positions}
              activeSymbol={activeRec?.symbol}
              avatarStatus={avatarStatus}
              recommendation={activeRec}
              onSell={onSell}
              onAvatarStart={async () => {
                if (!activeRec) return null;
                const status = await api.traderAvatarStart(activeRec.id);
                setAvatarStatus(status);
                return status;
              }}
              onAvatarStop={async () => {
                if (!activeRec) return;
                await api.traderAvatarStop(activeRec.id);
                setAvatarStatus(await api.traderAvatarStatus(activeRec.id));
              }}
            />
          </div>
        </div>
      )}
    </main>
  );
}

function EmptyState({ onScan, onRandom }: { onScan: () => void; onRandom: () => void }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 24, padding: 48 }}>
      <div style={{ width: 64, height: 64, borderRadius: 16, background: "linear-gradient(135deg, var(--accent), #60a5fa)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28, fontWeight: 700, color: "#fff" }}>W</div>
      <div style={{ fontSize: 20, fontWeight: 600 }}>Weekes AATF Trading Workstation</div>
      <div style={{ color: "var(--text-soft)", maxWidth: 480, textAlign: "center", lineHeight: 1.7 }}>
        AI trading desk with Research, Quant Pricing, Risk, and Trader roles. Start by scanning for earnings or triggering a demo event.
      </div>
      <div style={{ display: "flex", gap: 12 }}>
        <button className="btn btn-accent" onClick={onScan}>Run Earnings Scan</button>
        <button className="btn btn-accent" onClick={onRandom}>Random Demo Event</button>
      </div>
    </div>
  );
}
