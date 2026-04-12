"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { DeskInbox } from "@/components/layout/DeskInbox";
import { Header } from "@/components/layout/Header";
import { GroupChat } from "@/components/roles/GroupChat";
import { ActivePositionCard } from "@/components/trades/ActivePositionCard";
import { RecommendationCard } from "@/components/trades/RecommendationCard";
import { TraderAvatarPanel } from "@/components/trades/TraderAvatarPanel";
import { useSSE } from "@/hooks/useSSE";
import { api, streamUrl } from "@/lib/api";
import { EventItem, Position, Recommendation, RoleMessage, Summary, TraderAvatarStatus } from "@/lib/types";

export default function Page() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [activeRecommendation, setActiveRecommendation] = useState<Recommendation | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [timeline, setTimeline] = useState<RoleMessage[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [portfolioValue, setPortfolioValue] = useState<number | undefined>();
  const [mode, setMode] = useState<string>("paper");
  const [avatarStatus, setAvatarStatus] = useState<TraderAvatarStatus | null>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const initialRecSet = useRef(false);

  const load = useCallback(async () => {
    const [eventData, recData, positionData, portfolioData] = await Promise.all([
      api.events(), api.recs(), api.positions(), api.portfolio(),
    ]);
    setEvents(eventData.events);
    setRecommendations(recData.recommendations);
    setPositions(positionData.positions);
    setPortfolioValue(Number(portfolioData.portfolio_value ?? 0));
    setMode(String(portfolioData.status ?? "paper"));
    if (!initialRecSet.current && recData.recommendations.length > 0) {
      setActiveRecommendation(recData.recommendations[0]);
      initialRecSet.current = true;
    }
  }, []);

  useEffect(() => { load().catch(console.error); }, [load]);

  const activeRecId = activeRecommendation?.id;
  useEffect(() => {
    if (!activeRecId) return;
    api.rec(activeRecId).then((data) => {
      setActiveRecommendation(data.recommendation);
      setSummary(data.summary);
      setTimeline(data.timeline);
    }).catch(console.error);
    api.traderAvatarStatus(activeRecId).then(setAvatarStatus).catch(console.error);
  }, [activeRecId]);

  useSSE(streamUrl, useCallback((_type: string, payload: unknown) => {
    if (typeof payload === "object" && payload && "recommendation_id" in payload) {
      const p = payload as { recommendation_id?: string };
      if (p.recommendation_id && p.recommendation_id === activeRecId) {
        api.rec(p.recommendation_id).then((data) => {
          setActiveRecommendation(data.recommendation);
          setSummary(data.summary);
          setTimeline(data.timeline);
        }).catch(console.error);
      }
    }
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    refreshTimerRef.current = setTimeout(() => { void load(); }, 500);
  }, [activeRecId, load]));

  useEffect(() => () => { if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current); }, []);

  const sortedTimeline = useMemo(
    () => [...timeline].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()),
    [timeline]
  );

  const activePosition = useMemo(
    () => positions.find((p) => p.symbol === activeRecommendation?.symbol) ?? null,
    [positions, activeRecommendation?.symbol]
  );

  async function handleScan() { await api.scan(); await load(); }

  async function handleRandomEvent() {
    const result = await api.randomEvent();
    setActiveRecommendation(result.recommendation);
    initialRecSet.current = true;
    await load();
  }

  async function handleDeskSend(message: string) {
    if (!activeRecommendation) return;
    await api.discuss(activeRecommendation.id, message);
    const data = await api.rec(activeRecommendation.id);
    setActiveRecommendation(data.recommendation);
    setTimeline(data.timeline);
    setSummary(data.summary);
  }

  async function handleSell(symbol: string, shares: number) {
    // TODO: Wire to backend sell/close endpoint
    console.log(`Sell ${shares} shares of ${symbol}`);
    alert(`Sell ${shares} shares of ${symbol} — backend endpoint not yet implemented`);
  }

  const hasContent = events.length > 0 || recommendations.length > 0;

  return (
    <main className="workstation">
      <Header portfolioValue={portfolioValue} mode={mode} onScan={handleScan} onRandomEvent={handleRandomEvent} />

      {!hasContent ? (
        <EmptyState onScan={handleScan} onRandom={handleRandomEvent} />
      ) : (
        <div className="workstation-body">
          {/* Left: Desk Inbox */}
          <div className="column">
            <DeskInbox
              events={events}
              recommendations={recommendations}
              positions={positions}
              activeSymbol={activeRecommendation?.symbol}
              onSelectEvent={(ev) => {
                const rec = recommendations.find((r) => r.symbol === ev.symbol) ?? null;
                setActiveRecommendation(rec);
              }}
              onSelectRecommendation={setActiveRecommendation}
              onSelectPosition={(pos) => {
                const rec = recommendations.find((r) => r.symbol === pos.symbol) ?? null;
                if (rec) setActiveRecommendation(rec);
              }}
            />
          </div>

          {/* Center: Conversation */}
          <div className="column">
            <GroupChat messages={sortedTimeline} onSend={handleDeskSend} activeSymbol={activeRecommendation?.symbol} />
          </div>

          {/* Right: Trade Desk */}
          <div className="column">
            {/* Avatar at top when enabled */}
            {avatarStatus?.enabled && (
              <TraderAvatarPanel
                recommendation={activeRecommendation}
                avatarStatus={avatarStatus}
                timeline={sortedTimeline}
                onStart={async () => {
                  if (!activeRecommendation) return;
                  setAvatarStatus(await api.traderAvatarStart(activeRecommendation.id));
                }}
                onStop={async () => {
                  if (!activeRecommendation) return;
                  await api.traderAvatarStop(activeRecommendation.id);
                  setAvatarStatus(await api.traderAvatarStatus(activeRecommendation.id));
                }}
                onSpeak={async (text) => {
                  if (!activeRecommendation) return;
                  await api.traderAvatarSpeak(activeRecommendation.id, text);
                }}
              />
            )}

            {/* Combined Recommendation + Summary */}
            <RecommendationCard
              recommendation={activeRecommendation}
              summary={summary}
              onReady={async () => activeRecommendation && await api.readyForApproval(activeRecommendation.id).then(load)}
              onApprove={async (shares) => activeRecommendation && await api.approve(activeRecommendation.id, shares).then(load)}
              onExecute={async () => activeRecommendation && await api.execute(activeRecommendation.id).then(load)}
              onReject={async () => activeRecommendation && await api.reject(activeRecommendation.id, "User rejected").then(load)}
            />

            {/* Active Position with sell controls */}
            <ActivePositionCard position={activePosition} onSell={handleSell} />
          </div>
        </div>
      )}
    </main>
  );
}

function EmptyState({ onScan, onRandom }: { onScan: () => void; onRandom: () => void }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 24, padding: 48 }}>
      <div style={{
        width: 64, height: 64, borderRadius: 16,
        background: "linear-gradient(135deg, var(--accent), #60a5fa)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 28, fontWeight: 700, color: "#fff",
      }}>W</div>
      <div style={{ fontSize: 20, fontWeight: 600 }}>Weekes AATF Trading Workstation</div>
      <div style={{ color: "var(--text-soft)", maxWidth: 480, textAlign: "center", lineHeight: 1.7 }}>
        Multi-role AI trading desk with Research, Quant Pricing, Risk, and Trader.
        Each role analyses independently, then the Trader synthesises a recommendation for your approval.
      </div>
      <div style={{ display: "flex", gap: 12 }}>
        <button className="btn btn-accent" onClick={onScan}>Run Earnings Scan</button>
        <button className="btn btn-accent" onClick={onRandom}>Random Demo Event</button>
      </div>
    </div>
  );
}
