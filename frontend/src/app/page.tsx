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
  const [portfolio, setPortfolio] = useState<Record<string, unknown>>({});
  const [mode, setMode] = useState("paper");
  const [avatarStatus, setAvatarStatus] = useState<TraderAvatarStatus | null>(null);
  const [scanning, setScanning] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"events" | "recs">("events");
  const [chatRoleFilter, setChatRoleFilter] = useState<string | null>(null);
  const didInit = useRef(false);

  const load = useCallback(async () => {
    const [ev, rec, pos, port] = await Promise.all([api.events(), api.recs(), api.positions(), api.portfolio()]);
    setEvents(ev.events); setRecommendations(rec.recommendations); setPositions(pos.positions);
    setPortfolio(port); setMode(String(port.status ?? "paper"));
    if (!didInit.current && rec.recommendations.length > 0) { setActiveRec(rec.recommendations[0]); didInit.current = true; }
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
    if (type === "recommendation_update" || type === "role_message" || type === "role_query" || type === "summary_update") {
      if (p.recommendation_id === activeRecId && activeRecId) api.rec(activeRecId).then((d) => { setActiveRec(d.recommendation); setSummary(d.summary); setTimeline(d.timeline); }).catch(console.error);
      api.recs().then((d) => setRecommendations(d.recommendations)).catch(console.error);
    } else if (type === "position_update") { api.positions().then((d) => setPositions(d.positions)).catch(console.error); }
    else if (type === "market_event") { api.events().then((d) => setEvents(d.events)).catch(console.error); }
    else if (type === "voice_command") {
      const a = p.action as string;
      if (a === "navigate" && p.recommendation_id) { api.rec(p.recommendation_id as string).then((d) => { setActiveRec(d.recommendation); setSummary(d.summary); setTimeline(d.timeline); }).catch(console.error); toast(`Switching to ${p.symbol}`, "info"); }
      else if (a === "approve" || a === "execute") { toast(`Executed ${p.symbol}`, "success"); void load(); }
      else if (a === "reject") { toast(`Rejected ${p.symbol}`, "info"); void load(); }
      else if (a === "sell") { toast(`Sold ${p.symbol}`, "success"); void load(); }
      else if (a === "scan_complete") { toast(`Scan: ${p.count} candidates`, "success"); void load(); }
      else if (a === "show_events") setActiveTab("events");
      else if (a === "show_recommendations") setActiveTab("recs");
      else if (a === "open_settings") setSettingsOpen(true);
      else if (a === "close_settings") setSettingsOpen(false);
      else if (a === "open_help") setHelpOpen(true);
      else if (a === "close_help") setHelpOpen(false);
      else if (a === "filter_chat") setChatRoleFilter(p.value === "all" ? null : (p.value as string));
    } else if (type === "system" && p.type === "analysis_error") { toast(`Analysis failed: ${p.symbol}`, "error"); }
  }, [activeRecId]));

  const sortedTimeline = useMemo(() => [...timeline].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()), [timeline]);
  const hasContent = events.length > 0 || recommendations.length > 0;

  async function onScan() {
    setScanning(true);
    try { const r = await api.scan(); toast(`Scan: ${r.results?.length ?? 0} stocks`, "success"); await load(); }
    catch (err) { toast("Scan failed", "error"); } finally { setScanning(false); }
  }
  async function onSend(msg: string) {
    if (!activeRec) return;
    try { await api.discuss(activeRec.id, msg); const d = await api.rec(activeRec.id); setActiveRec(d.recommendation); setTimeline(d.timeline); setSummary(d.summary); }
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
      }} mode={mode} onScan={scanning ? undefined : onScan} onSettings={() => setSettingsOpen(true)} onHelp={() => setHelpOpen(true)} />

      {!hasContent ? (
        <EmptyState onScan={onScan} scanning={scanning} />
      ) : (
        <div className="workstation-body">
          {/* LEFT: News + Recommendations */}
          <div className="column">
            <InboxTabs events={events} recommendations={recommendations} activeSymbol={activeRec?.symbol}
              activeTab={activeTab} onTabChange={setActiveTab}
              onSelectEvent={(ev) => setActiveRec(recommendations.find((r) => r.symbol === ev.symbol) ?? null)}
              onSelectRecommendation={setActiveRec} />
          </div>

          {/* CENTER: Trade Panel + Avatar side by side, Chat below */}
          <div className="column">
            <div style={{ display: "flex", gap: 12, alignItems: "stretch" }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <TradePanel recommendation={activeRec} summary={summary}
                  onReady={async () => { if (activeRec) { await api.readyForApproval(activeRec.id); await load(); } }}
                  onApprove={onApprove}
                  onApproveAndExecute={async (shares) => {
                    if (!activeRec) return;
                    try { await api.readyForApproval(activeRec.id).catch(() => {}); await api.approve(activeRec.id, shares); await api.execute(activeRec.id);
                      toast(`Executed ${activeRec.direction} ${activeRec.symbol} — ${shares} sh`, "success"); await load();
                    } catch (err) { toast("Failed: " + (err instanceof Error ? err.message : ""), "error"); }
                  }}
                  onExecute={onExecute} onReject={onReject} />
              </div>
              <InlineAvatar recommendation={activeRec} avatarStatus={avatarStatus}
                onStart={async () => { if (!activeRec) return null; const s = await api.traderAvatarStart(activeRec.id); setAvatarStatus(s); return s; }}
                onStop={async () => { if (!activeRec) return; await api.traderAvatarStop(activeRec.id); setAvatarStatus(await api.traderAvatarStatus(activeRec.id)); }} />
            </div>
            <GroupChat messages={sortedTimeline} onSend={onSend} activeSymbol={activeRec?.symbol}
              roleFilter={chatRoleFilter} onRoleFilterChange={setChatRoleFilter} />
          </div>

          {/* RIGHT: Market Lists */}
          <div className="column">
            <MarketLists positions={positions} activeSymbol={activeRec?.symbol} onSell={onSell}
              onSelectSymbol={(sym) => { const rec = recommendations.find((r) => r.symbol === sym); if (rec) setActiveRec(rec); }} />
          </div>
        </div>
      )}

      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <HelpPanel open={helpOpen} onClose={() => setHelpOpen(false)} />
      <ToastContainer />
    </main>
  );
}

function EmptyState({ onScan, scanning }: { onScan: () => void; scanning: boolean }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 24, padding: 48 }}>
      <div style={{ width: 64, height: 64, borderRadius: 16, background: "linear-gradient(135deg, var(--accent), #60a5fa)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" /><polyline points="16 7 22 7 22 13" />
        </svg>
      </div>
      <div style={{ fontSize: 20, fontWeight: 600 }}>Trading Desk AI</div>
      <div style={{ color: "var(--text-soft)", maxWidth: 480, textAlign: "center", lineHeight: 1.7 }}>
        Multi-role AI trading desk. News and market data flow in automatically.
      </div>
      <button className="btn btn-accent" onClick={onScan} disabled={scanning}>{scanning ? "Scanning..." : "Scan Earnings"}</button>
    </div>
  );
}
