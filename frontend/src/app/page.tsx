"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Header } from "@/components/layout/Header";
import { InboxTabs } from "@/components/layout/InboxTabs";
import { TradePanel } from "@/components/trades/TradePanel";
import { GroupChat } from "@/components/roles/GroupChat";
import { AvatarAndPositions } from "@/components/trades/AvatarAndPositions";
import { ToastContainer, toast } from "@/components/shared/Toast";
import { SettingsPanel } from "@/components/shared/SettingsPanel";
import { HelpPanel } from "@/components/shared/HelpPanel";
import { MarketPulse } from "@/components/shared/MarketPulse";
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
  const [pulseOpen, setPulseOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"events" | "recs">("events");
  const [chatRoleFilter, setChatRoleFilter] = useState<string | null>(null);
  const didInit = useRef(false);

  const load = useCallback(async () => {
    const [ev, rec, pos, port] = await Promise.all([
      api.events(), api.recs(), api.positions(), api.portfolio(),
    ]);
    setEvents(ev.events);
    setRecommendations(rec.recommendations);
    setPositions(pos.positions);
    setPortfolio(port);
    setMode(String(port.status ?? "paper"));
    if (!didInit.current && rec.recommendations.length > 0) {
      setActiveRec(rec.recommendations[0]);
      didInit.current = true;
    }
  }, []);

  useEffect(() => { load().catch(console.error); }, [load]);

  // Refresh prices + check exits every 60 seconds
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        // Check for auto-exits (stop/target/max hold)
        const exits = await fetch(`${streamUrl.replace('/api/stream', '/api/check-exits')}`, { method: "POST" }).then(r => r.json()).catch(() => null);
        if (exits?.closed?.length) {
          for (const c of exits.closed) {
            toast(`Auto-exit ${c.symbol}: ${c.reason} — P&L $${c.pnl.toFixed(2)}`, c.pnl >= 0 ? "success" : "error");
          }
        }
        // Refresh positions with live prices
        const d = await api.positions(true);
        setPositions(d.positions);
        // Refresh portfolio totals
        const p = await api.portfolio();
        setPortfolio(p);
      } catch { /* ignore */ }
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  const activeRecId = activeRec?.id;
  useEffect(() => {
    if (!activeRecId) return;
    api.rec(activeRecId).then((d) => { setActiveRec(d.recommendation); setSummary(d.summary); setTimeline(d.timeline); }).catch(console.error);
    api.traderAvatarStatus(activeRecId).then(setAvatarStatus).catch(console.error);
  }, [activeRecId]);

  useSSE(streamUrl, useCallback((type: string, payload: unknown) => {
    const p = (typeof payload === "object" && payload) ? payload as Record<string, unknown> : {};
    if (type === "recommendation_update" || type === "role_message" || type === "role_query" || type === "summary_update") {
      if (p.recommendation_id === activeRecId && activeRecId) {
        api.rec(activeRecId).then((d) => { setActiveRec(d.recommendation); setSummary(d.summary); setTimeline(d.timeline); }).catch(console.error);
      }
      api.recs().then((d) => setRecommendations(d.recommendations)).catch(console.error);
    } else if (type === "position_update") {
      api.positions().then((d) => setPositions(d.positions)).catch(console.error);
    } else if (type === "market_event") {
      api.events().then((d) => setEvents(d.events)).catch(console.error);
    } else if (type === "voice_command") {
      const action = p.action as string;
      if (action === "navigate" && p.recommendation_id) {
        api.rec(p.recommendation_id as string).then((d) => {
          setActiveRec(d.recommendation); setSummary(d.summary); setTimeline(d.timeline);
        }).catch(console.error);
        toast(`Switching to ${p.symbol}`, "info");
      } else if (action === "approve" || action === "execute") {
        toast(`Executed ${p.symbol}`, "success");
        void load();
      } else if (action === "reject") {
        toast(`Rejected ${p.symbol}`, "info");
        void load();
      } else if (action === "sell") {
        toast(`Sold ${p.symbol}`, "success");
        void load();
      } else if (action === "scan_complete") {
        toast(`Scan: ${p.count} candidates`, "success");
        void load();
      } else if (action === "show_events") {
        setActiveTab("events");
      } else if (action === "show_recommendations") {
        setActiveTab("recs");
      } else if (action === "open_settings") {
        setSettingsOpen(true);
      } else if (action === "close_settings") {
        setSettingsOpen(false);
      } else if (action === "open_help") {
        setHelpOpen(true);
      } else if (action === "close_help") {
        setHelpOpen(false);
      } else if (action === "open_market_pulse") {
        setPulseOpen(true);
      } else if (action === "close_market_pulse") {
        setPulseOpen(false);
      } else if (action === "filter_chat") {
        setChatRoleFilter(p.value === "all" ? null : (p.value as string));
      } else if (action === "mute" || action === "unmute") {
        // handled by avatar component
      } else if (action === "end_call") {
        // handled by avatar component
      }
    } else if (type === "system") {
      if (p.type === "analysis_error") {
        toast(`Analysis failed for ${p.symbol}: ${p.error}`, "error");
      }
    }
  }, [activeRecId]));

  const sortedTimeline = useMemo(
    () => [...timeline].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()),
    [timeline],
  );

  const hasContent = events.length > 0 || recommendations.length > 0;

  async function onScan() {
    setScanning(true);
    try {
      const result = await api.scan();
      const count = result.results?.length ?? 0;
      toast(`Scan complete — ${count} stock${count !== 1 ? "s" : ""} found. Analysis running in background.`, "success");
      await load();
    } catch (err) {
      toast("Scan failed: " + (err instanceof Error ? err.message : "Unknown error"), "error");
    } finally {
      setScanning(false);
    }
  }

  async function onSend(msg: string) {
    if (!activeRec) return;
    try {
      await api.discuss(activeRec.id, msg);
      const d = await api.rec(activeRec.id);
      setActiveRec(d.recommendation); setTimeline(d.timeline); setSummary(d.summary);
    } catch (err) {
      toast("Chat failed: " + (err instanceof Error ? err.message : "Unknown error"), "error");
    }
  }

  async function onApprove(shares: number) {
    if (!activeRec) return;
    try {
      await api.approve(activeRec.id, shares);
      toast(`Approved ${activeRec.direction} ${activeRec.symbol} — ${shares} shares`, "success");
      await load();
    } catch (err) {
      toast("Approve failed: " + (err instanceof Error ? err.message : "Unknown error"), "error");
    }
  }

  async function onExecute() {
    if (!activeRec) return;
    try {
      await api.execute(activeRec.id);
      toast(`Executed ${activeRec.direction} ${activeRec.symbol}`, "success");
      await load();
    } catch (err) {
      toast("Execute failed: " + (err instanceof Error ? err.message : "Unknown error"), "error");
    }
  }

  async function onReject() {
    if (!activeRec) return;
    try {
      await api.reject(activeRec.id, "User rejected");
      toast(`Rejected ${activeRec.symbol}`, "info");
      await load();
    } catch (err) {
      toast("Reject failed: " + (err instanceof Error ? err.message : "Unknown error"), "error");
    }
  }

  async function onSell(tradeId: string, symbol: string, shares: number) {
    try {
      const r = await api.sellTrade(tradeId, shares);
      toast(`Closed ${r.shares_sold} sh of ${symbol}. P&L: $${r.pnl.toFixed(2)}`, r.pnl >= 0 ? "success" : "error");
      await load();
    } catch (err) {
      toast("Close failed: " + (err instanceof Error ? err.message : "Unknown error"), "error");
    }
  }

  return (
    <main className="workstation">
      <Header portfolio={{
        portfolio_value: Number(portfolio.portfolio_value ?? 0),
        cash: Number(portfolio.cash ?? 0),
        unrealised_pnl: Number(portfolio.unrealised_pnl ?? portfolio.unrealized_pnl ?? 0),
        daily_change: Number(portfolio.daily_change ?? 0),
        daily_change_pct: Number(portfolio.daily_change_pct ?? 0),
        open_positions: Number(portfolio.open_positions ?? 0),
      }} mode={mode} onScan={scanning ? undefined : onScan} onSettings={() => setSettingsOpen(true)} onHelp={() => setHelpOpen(true)} onMarketPulse={() => setPulseOpen(true)} />
      {!hasContent ? (
        <EmptyState onScan={onScan} scanning={scanning} />
      ) : (
        <div className="workstation-body">
          <div className="column">
            <InboxTabs
              events={events}
              recommendations={recommendations}
              activeSymbol={activeRec?.symbol}
              activeTab={activeTab}
              onTabChange={setActiveTab}
              onSelectEvent={(ev) => { setActiveRec(recommendations.find((r) => r.symbol === ev.symbol) ?? null); }}
              onSelectRecommendation={setActiveRec}
            />
          </div>
          <div className="column">
            <TradePanel
              recommendation={activeRec}
              summary={summary}
              onReady={async () => { if (activeRec) { await api.readyForApproval(activeRec.id); await load(); } }}
              onApprove={onApprove}
              onApproveAndExecute={async (shares) => {
                if (!activeRec) return;
                try {
                  await api.readyForApproval(activeRec.id).catch(() => {});
                  await api.approve(activeRec.id, shares);
                  await api.execute(activeRec.id);
                  toast(`Executed ${activeRec.direction} ${activeRec.symbol} — ${shares} shares`, "success");
                  await load();
                } catch (err) {
                  toast("Approve & execute failed: " + (err instanceof Error ? err.message : ""), "error");
                }
              }}
              onExecute={onExecute}
              onReject={onReject}
            />
            <GroupChat messages={sortedTimeline} onSend={onSend} activeSymbol={activeRec?.symbol} roleFilter={chatRoleFilter} onRoleFilterChange={setChatRoleFilter} />
          </div>
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
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <HelpPanel open={helpOpen} onClose={() => setHelpOpen(false)} />
      <MarketPulse open={pulseOpen} onClose={() => setPulseOpen(false)} />
      <ToastContainer />
    </main>
  );
}

function EmptyState({ onScan, scanning }: { onScan: () => void; scanning: boolean }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 24, padding: 48 }}>
      <div style={{ width: 64, height: 64, borderRadius: 16, background: "linear-gradient(135deg, var(--accent), #60a5fa)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
          <polyline points="16 7 22 7 22 13" />
        </svg>
      </div>
      <div style={{ fontSize: 20, fontWeight: 600 }}>Trading Desk AI</div>
      <div style={{ color: "var(--text-soft)", maxWidth: 480, textAlign: "center", lineHeight: 1.7 }}>
        Multi-role AI trading desk with Research, Quant Pricing, Risk, and Trader.
        Scan for earnings events to get started.
      </div>
      <button className="btn btn-accent" onClick={onScan} disabled={scanning}>
        {scanning ? "Scanning..." : "Scan Earnings"}
      </button>
    </div>
  );
}
