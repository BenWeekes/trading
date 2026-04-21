"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Header } from "@/components/layout/Header";
import { InboxTabs } from "@/components/layout/InboxTabs";
import { TradePanel } from "@/components/trades/TradePanel";
import { InlineAvatar } from "@/components/trades/InlineAvatar";
import { GroupChat } from "@/components/roles/GroupChat";
import { MarketLists } from "@/components/trades/MarketLists";
import { ToastContainer, toast } from "@/components/shared/Toast";
import { SettingsPanel } from "@/components/shared/SettingsPanel";
import { HelpPanel } from "@/components/shared/HelpPanel";
import { NewsReader } from "@/components/shared/NewsReader";
import { useSSE } from "@/hooks/useSSE";
import { api, streamUrl } from "@/lib/api";
import { DiscussionSubject, EventItem, Position, Recommendation, RoleMessage, Summary, TraderAvatarStatus } from "@/lib/types";

type ActiveSubjectPayload = {
  subject: DiscussionSubject;
  recommendation?: Recommendation | null;
  event?: EventItem | null;
  trade?: unknown;
  summary?: Summary | null;
  timeline: RoleMessage[];
};

export default function Page() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [activeRec, setActiveRec] = useState<Recommendation | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [timeline, setTimeline] = useState<RoleMessage[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [portfolio, setPortfolio] = useState<Record<string, unknown>>({});
  const [mode, setMode] = useState("paper");
  const [avatarStatus, setAvatarStatus] = useState<TraderAvatarStatus | null>(null);
  const [scanning, setScanning] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [helpScrollCommand, setHelpScrollCommand] = useState<{ direction: "up" | "down"; nonce: number } | null>(null);
  const [inboxScrollCommand, setInboxScrollCommand] = useState<{ direction: "up" | "down"; nonce: number } | null>(null);
  const [activeTab, setActiveTab] = useState<"earnings" | "ai" | "news">("earnings");
  const [activeMarketTab, setActiveMarketTab] = useState<"open" | "all" | "gainers" | "losers" | "active">("open");
  const [chatRoleFilter, setChatRoleFilter] = useState<string | null>(null);
  const [companyName, setCompanyName] = useState("");
  const [companyNames, setCompanyNames] = useState<Record<string, string>>({});
  const [activeSubject, setActiveSubject] = useState<ActiveSubjectPayload | null>(null);
  const didInit = useRef(false);
  const didScan = useRef(false);

  const applySubjectData = useCallback((data: ActiveSubjectPayload) => {
    setActiveSubject(data);
    if (data.recommendation) {
      setActiveRec(data.recommendation);
    }
    setSummary(data.summary ?? null);
    setTimeline(data.timeline);
  }, []);

  const load = useCallback(async () => {
    const [ev, rec, pos, port] = await Promise.all([api.events(), api.recs(), api.positions(), api.portfolio()]);
    setEvents(ev.events); setRecommendations(rec.recommendations); setPositions(pos.positions);
    setPortfolio(port); setMode(String(port.status ?? "paper"));
    if (!didInit.current && rec.recommendations.length > 0) { setActiveRec(rec.recommendations[0]); didInit.current = true; }
  }, []);

  useEffect(() => { load().catch(console.error); }, [load]);

  // Fetch company names from ticker cache
  useEffect(() => {
    const fetchNames = async () => {
      try {
        const r = await fetch(`${streamUrl.replace('/api/stream', '/api/ticker')}`);
        const d = await r.json();
        const names: Record<string, string> = {};
        for (const [sym, data] of Object.entries(d.prices || {})) {
          const name = (data as { name?: string }).name;
          if (name) names[sym] = name;
        }
        if (Object.keys(names).length > 0) setCompanyNames((prev) => ({ ...prev, ...names }));
      } catch { /* ignore */ }
    };
    fetchNames();
    const interval = setInterval(fetchNames, 30000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scan on first load if no recs exist
  useEffect(() => {
    if (didScan.current) return;
    didScan.current = true;
    const timer = setTimeout(async () => {
      try {
        const r = await api.recs();
        if (r.recommendations.length === 0) {
          await api.scan();
          await load();
        }
      } catch { /* ignore */ }
    }, 2000);
    return () => clearTimeout(timer);
  }, [load]);

  const activeRecId = activeRec?.id;
  const loadSubjectByRecommendation = useCallback(async (recommendationId: string) => {
    const data = await api.resolveSubject({ recommendation_id: recommendationId });
    applySubjectData(data);
    return data;
  }, [applySubjectData]);
  const loadSubjectByEvent = useCallback(async (eventId: string, linkedRecommendationId?: string) => {
    const data = await api.resolveSubject({ event_id: eventId, linked_recommendation_id: linkedRecommendationId });
    applySubjectData(data);
    return data;
  }, [applySubjectData]);
  const refreshActiveSubject = useCallback(async () => {
    if (!activeSubject?.subject?.id) return;
    const data = await api.subject(activeSubject.subject.id);
    applySubjectData(data);
  }, [activeSubject?.subject?.id, applySubjectData]);
  useEffect(() => {
    if (!activeRecId) return;
    if (!activeSubject) {
      loadSubjectByRecommendation(activeRecId).catch(console.error);
    }
  }, [activeRecId, activeSubject, loadSubjectByRecommendation]);
  useEffect(() => {
    if (!activeRecId) return;
    api.traderAvatarStatus(activeRecId).then(setAvatarStatus).catch(console.error);
    if (activeRec?.symbol) api.companyName(activeRec.symbol).then((d) => setCompanyName(d.name)).catch(() => {});
  }, [activeRecId, activeRec?.symbol]);

  useSSE(streamUrl, useCallback((type: string, payload: unknown) => {
    const p = (typeof payload === "object" && payload) ? payload as Record<string, unknown> : {};
    if (type === "recommendation_update" || type === "role_message" || type === "role_query" || type === "summary_update") {
      if (activeSubject?.subject?.id && (p.recommendation_id === activeRecId || p.discussion_subject_id === activeSubject.subject.id)) refreshActiveSubject().catch(console.error);
      api.recs().then((d) => setRecommendations(d.recommendations)).catch(console.error);
    } else if (type === "position_update") { api.positions().then((d) => setPositions(d.positions)).catch(console.error); }
    else if (type === "market_event") { api.events().then((d) => setEvents(d.events)).catch(console.error); }
    else if (type === "voice_command") {
      const a = p.action as string;
      if (a === "navigate" && p.recommendation_id) { loadSubjectByRecommendation(p.recommendation_id as string).catch(console.error); toast(`Switching to ${p.symbol}`, "info"); }
      else if (a === "approve" || a === "execute") { toast(`Executed ${p.symbol}`, "success"); void load(); }
      else if (a === "reject") { toast(`Rejected ${p.symbol}`, "info"); void load(); }
      else if (a === "sell") { toast(`Sold ${p.symbol}`, "success"); void load(); }
      else if (a === "scan_complete") { toast(`Scan: ${p.count} candidates`, "success"); void load(); }
      else if (a === "show_events" || a === "show_earnings") setActiveTab("earnings");
      else if (a === "show_recommendations" || a === "show_ai") setActiveTab("ai");
      else if (a === "show_news") setActiveTab("news");
      else if (a === "show_open") setActiveMarketTab("open");
      else if (a === "show_all") setActiveMarketTab("all");
      else if (a === "show_gainers") setActiveMarketTab("gainers");
      else if (a === "show_losers") setActiveMarketTab("losers");
      else if (a === "show_active") setActiveMarketTab("active");
      else if (a === "open_settings") setSettingsOpen(true);
      else if (a === "close_settings") setSettingsOpen(false);
      else if (a === "open_help") setHelpOpen(true);
      else if (a === "close_help") setHelpOpen(false);
      else if (a === "scroll_down") {
        if (helpOpen) setHelpScrollCommand({ direction: "down", nonce: Date.now() });
        else setInboxScrollCommand({ direction: "down", nonce: Date.now() });
      }
      else if (a === "scroll_up") {
        if (helpOpen) setHelpScrollCommand({ direction: "up", nonce: Date.now() });
        else setInboxScrollCommand({ direction: "up", nonce: Date.now() });
      }
      else if (a === "filter_chat") setChatRoleFilter(p.value === "all" ? null : (p.value as string));
      else if (a === "open_event" && p.event_id) {
        const eventId = p.event_id as string;
        const tab = (p.tab as "earnings" | "news" | undefined) ?? "news";
        setActiveTab(tab === "earnings" ? "earnings" : "news");
        loadSubjectByEvent(eventId).catch(console.error);
        if (p.symbol) toast(`Opened ${p.symbol}`, "info");
      }
    } else if (type === "system" && p.type === "analysis_error") { toast(`Analysis failed: ${p.symbol}`, "error"); }
  }, [activeRecId, activeSubject?.subject?.id, helpOpen, loadSubjectByEvent, loadSubjectByRecommendation, refreshActiveSubject]));

  const sortedTimeline = useMemo(() => [...timeline].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()), [timeline]);
  const hasContent = events.length > 0 || recommendations.length > 0;

  async function onScan() {
    setScanning(true);
    try { const r = await api.scan(); toast(`Scan: ${r.results?.length ?? 0} stocks`, "success"); await load(); }
    catch (err) { toast("Scan failed", "error"); } finally { setScanning(false); }
  }
  async function onSend(msg: string) {
    if (!activeSubject?.subject?.id) return;
    try { await api.discussSubject(activeSubject.subject.id, msg); await refreshActiveSubject(); }
    catch { toast("Chat failed", "error"); }
  }
  async function onApprove(shares: number) {
    if (!activeRec) return;
    try { await api.approve(activeRec.id, shares); toast(`Approved ${activeRec.symbol}`, "success"); await load(); }
    catch { toast("Approve failed", "error"); }
  }
  async function onExecute() { if (!activeRec) return; try { await api.execute(activeRec.id); toast(`Executed ${activeRec.symbol}`, "success"); await load(); } catch { toast("Execute failed", "error"); } }
  async function onReject() { if (!activeRec) return; try { await api.reject(activeRec.id, "rejected"); toast(`Rejected`, "info"); await load(); } catch { toast("Reject failed", "error"); } }
  async function onSell(tradeId: string, symbol: string, shares: number) {
    try { const r = await api.sellTrade(tradeId, shares); toast(`Closed ${r.shares_sold} sh of ${symbol}. P&L $${r.pnl.toFixed(2)}`, r.pnl >= 0 ? "success" : "error"); await load(); }
    catch { toast("Close failed", "error"); }
  }

  return (
    <main className="workstation">
      <Header portfolio={{
        portfolio_value: Number(portfolio.portfolio_value ?? 0), cash: Number(portfolio.cash ?? 0),
        unrealised_pnl: Number(portfolio.unrealised_pnl ?? portfolio.unrealized_pnl ?? 0),
        daily_change: Number(portfolio.daily_change ?? 0), daily_change_pct: Number(portfolio.daily_change_pct ?? 0),
        open_positions: Number(portfolio.open_positions ?? 0),
      }} mode={mode} onSettings={() => setSettingsOpen(true)} onHelp={() => setHelpOpen(true)} />


      {!hasContent ? (
        <EmptyState />
      ) : (
        <div className="workstation-body">
          {/* LEFT: News + Recommendations */}
          <div className="column">
            <InboxTabs events={events} recommendations={recommendations} companyNames={companyNames} activeSymbol={activeRec?.symbol}
              activeTab={activeTab} onTabChange={setActiveTab}
              scrollCommand={inboxScrollCommand}
              onSelectEvent={async (ev) => {
                const rec = recommendations.find((r) => r.symbol === ev.symbol);
                if (rec) { await loadSubjectByRecommendation(rec.id); return; }
                // No rec for this symbol — trigger a scan and re-read recommendations.
                if (ev.symbol) {
                  toast(`Analysing ${ev.symbol}...`, "info");
                  try {
                    await api.scan();
                    const fresh = await api.recs();
                    setRecommendations(fresh.recommendations);
                    const newRec = fresh.recommendations.find((r) => r.symbol === ev.symbol);
                    if (newRec) await loadSubjectByRecommendation(newRec.id);
                    else await loadSubjectByEvent(ev.id);
                  } catch { /* ignore */ }
                }
              }}
              onSelectRecommendation={(rec) => { void loadSubjectByRecommendation(rec.id); }}
              onSelectNews={async (ev) => {
                const matchingRec = ev.symbol ? recommendations.find((r) => r.symbol === ev.symbol) ?? null : null;
                const subjectData = await loadSubjectByEvent(ev.id, matchingRec?.id);
                if (subjectData?.subject?.id && ev.headline) {
                  try {
                    await api.discussSubject(subjectData.subject.id, `[System: User is reading news] ${ev.symbol ? ev.symbol + ": " : ""}${ev.headline}`);
                    const refreshed = await api.subject(subjectData.subject.id);
                    applySubjectData(refreshed);
                  } catch { /* ignore */ }
                }
              }} />
          </div>

          {/* CENTER: News or Trade Panel (top) + Avatar + Chat (bottom) */}
          <div className="column">
            <div style={{ display: "flex", gap: 12, minHeight: 320, maxHeight: 400, flexShrink: 0 }}>
              <div style={{ flex: 1, minWidth: 0, overflow: "auto" }}>
                {activeSubject?.subject?.subject_type === "news" ? (
                  <NewsReader event={activeSubject.event ?? null} onClose={() => { if (activeRec?.id) { void loadSubjectByRecommendation(activeRec.id); } else { setActiveSubject(null); } }} />
                ) : (
                  <TradePanel recommendation={activeSubject?.recommendation ?? activeRec} summary={activeSubject?.summary ?? summary} companyName={companyName}
                    onReady={async () => { if (activeRec) { await api.readyForApproval(activeRec.id); await load(); } }}
                    onApprove={onApprove}
                    onApproveAndExecute={async (shares) => {
                      if (!activeRec) return;
                      try { await api.readyForApproval(activeRec.id).catch(() => {}); await api.approve(activeRec.id, shares); await api.execute(activeRec.id);
                        toast(`Executed ${activeRec.direction} ${activeRec.symbol} — ${shares} sh`, "success"); await load();
                      } catch (err) { toast("Failed: " + (err instanceof Error ? err.message : ""), "error"); }
                    }}
                    onExecute={onExecute} onReject={onReject} />
                )}
              </div>
              <InlineAvatar recommendation={activeRec} avatarStatus={avatarStatus}
                onStart={async () => { if (!activeRec) return null; const s = await api.traderAvatarStart(activeRec.id); setAvatarStatus(s); return s; }}
                onStop={async () => { if (!activeRec) return; await api.traderAvatarStop(activeRec.id); setAvatarStatus(await api.traderAvatarStatus(activeRec.id)); }} />
            </div>
            <GroupChat
              messages={sortedTimeline}
              onSend={onSend}
              activeSymbol={activeSubject?.subject?.symbol ?? activeRec?.symbol}
              companyName={activeSubject?.event?.symbol ? (companyNames[activeSubject.event.symbol ?? ""] || "") : companyName}
              roleFilter={chatRoleFilter} onRoleFilterChange={setChatRoleFilter} />
          </div>

          {/* RIGHT: Market Lists */}
          <div className="column">
            <MarketLists positions={positions} activeSymbol={activeRec?.symbol} onSell={onSell}
              activeTab={activeMarketTab} onTabChange={setActiveMarketTab}
              onSelectSymbol={(sym) => { const rec = recommendations.find((r) => r.symbol === sym); if (rec) void loadSubjectByRecommendation(rec.id); }} />
          </div>
        </div>
      )}

      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <HelpPanel open={helpOpen} onClose={() => setHelpOpen(false)} scrollCommand={helpScrollCommand} />
      <ToastContainer />
    </main>
  );
}

function EmptyState() {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 24, padding: 48 }}>
      <div style={{ width: 64, height: 64, borderRadius: 16, background: "linear-gradient(135deg, var(--accent), #60a5fa)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" /><polyline points="16 7 22 7 22 13" />
        </svg>
      </div>
      <div style={{ fontSize: 20, fontWeight: 600 }}>Trading Desk AI</div>
      <div style={{ color: "var(--text-soft)", maxWidth: 480, textAlign: "center", lineHeight: 1.7 }}>
        Market news and earnings scan automatically. Earnings events, AI recommendations, and live prices will appear as they arrive.
      </div>
      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Start a voice call with the trader avatar to interact by voice.</div>
    </div>
  );
}
