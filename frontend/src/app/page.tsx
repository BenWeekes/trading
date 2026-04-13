"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Header } from "@/components/layout/Header";
import { InboxTabs } from "@/components/layout/InboxTabs";
import { TradePanel } from "@/components/trades/TradePanel";
import { GroupChat } from "@/components/roles/GroupChat";
import { AvatarAndPositions } from "@/components/trades/AvatarAndPositions";
import { ToastContainer, toast } from "@/components/shared/Toast";
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
  const [scanning, setScanning] = useState(false);
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
    if (type === "recommendation_update" || type === "role_message" || type === "role_query" || type === "summary_update") {
      if (p.recommendation_id === activeRecId && activeRecId) {
        api.rec(activeRecId).then((d) => { setActiveRec(d.recommendation); setSummary(d.summary); setTimeline(d.timeline); }).catch(console.error);
      }
      api.recs().then((d) => setRecommendations(d.recommendations)).catch(console.error);
    } else if (type === "position_update") {
      api.positions().then((d) => setPositions(d.positions)).catch(console.error);
    } else if (type === "market_event") {
      api.events().then((d) => setEvents(d.events)).catch(console.error);
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
      <Header portfolioValue={portfolioValue} mode={mode} onScan={scanning ? undefined : onScan} />
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
      <ToastContainer />
    </main>
  );
}

function EmptyState({ onScan, scanning }: { onScan: () => void; scanning: boolean }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 24, padding: 48 }}>
      <div style={{ width: 64, height: 64, borderRadius: 16, background: "linear-gradient(135deg, var(--accent), #60a5fa)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28, fontWeight: 700, color: "#fff" }}>W</div>
      <div style={{ fontSize: 20, fontWeight: 600 }}>AI Trading Platform</div>
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
