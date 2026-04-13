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

  // Refresh position prices every 60 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      api.positions(true).then((d) => setPositions(d.positions)).catch(console.error);
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
        toast(`Voice: switching to ${p.symbol}`, "info");
      } else if (action === "approve") {
        toast(`Voice: approved ${p.symbol}`, "success");
        void load();
      } else if (action === "reject") {
        toast(`Voice: rejected ${p.symbol}`, "info");
        void load();
      } else if (action === "execute") {
        if (p.recommendation_id) {
          api.execute(p.recommendation_id as string).then(() => { toast(`Voice: executed ${p.symbol}`, "success"); void load(); }).catch(console.error);
        }
      } else if (action === "sell") {
        if (p.trade_id) {
          const pos = positions.find((pp) => pp.id === p.trade_id);
          api.sellTrade(p.trade_id as string, pos?.shares ?? 0).then((r) => { toast(`Voice: sold ${p.symbol}, P&L $${r.pnl.toFixed(2)}`, r.pnl >= 0 ? "success" : "error"); void load(); }).catch(console.error);
        }
      } else if (action === "switch_tab") {
        toast(`Voice: ${p.tab} tab`, "info");
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
      }} mode={mode} onScan={scanning ? undefined : onScan} onSettings={() => setSettingsOpen(true)} onHelp={() => setHelpOpen(true)} />
      {!hasContent ? (
        <EmptyState onScan={onScan} scanning={scanning} />
      ) : (
        <div className="workstation-body">
          <div className="column">
            <InboxTabs
              events={events}
              recommendations={recommendations}
              activeSymbol={activeRec?.symbol}
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
            <GroupChat messages={sortedTimeline} onSend={onSend} activeSymbol={activeRec?.symbol} />
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
