"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { DeskInbox } from "@/components/layout/DeskInbox";
import { Header } from "@/components/layout/Header";
import { GroupChat } from "@/components/roles/GroupChat";
import { SharedSummary } from "@/components/roles/SharedSummary";
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

  const load = useCallback(async () => {
    const [eventData, recData, positionData, portfolioData] = await Promise.all([
      api.events(),
      api.recs(),
      api.positions(),
      api.portfolio(),
    ]);
    setEvents(eventData.events);
    setRecommendations(recData.recommendations);
    setPositions(positionData.positions);
    setPortfolioValue(Number(portfolioData.portfolio_value ?? 0));
    setMode(String(portfolioData.status ?? "paper"));
    setActiveRecommendation((current) => current ?? recData.recommendations[0] ?? null);
  }, []);

  useEffect(() => {
    load().catch(console.error);
  }, [load]);

  useEffect(() => {
    if (!activeRecommendation) return;
    api.rec(activeRecommendation.id)
      .then((data) => {
        setActiveRecommendation(data.recommendation);
        setSummary(data.summary);
        setTimeline(data.timeline);
      })
      .catch(console.error);
    api.traderAvatarStatus(activeRecommendation.id).then(setAvatarStatus).catch(console.error);
  }, [activeRecommendation?.id]);

  useSSE(streamUrl, (_type, payload) => {
    if (typeof payload === "object" && payload && "recommendation_id" in payload && activeRecommendation) {
      const p = payload as { recommendation_id?: string };
      if (p.recommendation_id === activeRecommendation.id) {
        api.rec(activeRecommendation.id)
          .then((data) => {
            setActiveRecommendation(data.recommendation);
            setSummary(data.summary);
            setTimeline(data.timeline);
          })
          .catch(console.error);
      }
    }
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }
    refreshTimerRef.current = setTimeout(() => {
      void load();
    }, 500);
  });

  useEffect(() => {
    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, []);

  const sortedTimeline = useMemo(
    () => [...timeline].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()),
    [timeline]
  );
  const activePosition = useMemo(
    () => positions.find((position) => position.symbol === activeRecommendation?.symbol) ?? null,
    [positions, activeRecommendation?.symbol]
  );

  async function handleScan() {
    await api.scan();
    await load();
  }

  async function handleDeskSend(message: string) {
    if (!activeRecommendation) return;
    await api.discuss(activeRecommendation.id, message);
    const data = await api.rec(activeRecommendation.id);
    setTimeline(data.timeline);
    setSummary(data.summary);
  }

  return (
    <main style={{ minHeight: "100vh", height: "100vh", overflow: "hidden", display: "grid", gridTemplateRows: "auto 1fr" }}>
      <Header portfolioValue={portfolioValue} mode={mode} />
      <div style={{ padding: 24, minHeight: 0, display: "grid", gridTemplateRows: "auto 1fr", gap: 16, overflow: "hidden" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 0 }}>
          <div style={{ color: "var(--text-soft)" }}>Paper-first local workstation with role-led discussion.</div>
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={handleScan} style={topButtonStyle}>Run Scan</button>
            <button
              onClick={async () => {
                const result = await api.randomEvent();
                setActiveRecommendation(result.recommendation);
                await load();
              }}
              style={topButtonStyle}
            >
              Random Event
            </button>
          </div>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1.05fr 1.3fr 1fr",
            gap: 18,
            alignItems: "start",
            minHeight: 0,
            overflow: "hidden",
          }}
        >
          <div style={{ display: "grid", gap: 14, minHeight: 0, overflowY: "auto", paddingRight: 4 }}>
            <SectionLabel title="Desk Inbox" />
            <DeskInbox
              events={events}
              recommendations={recommendations}
              positions={positions}
              activeSymbol={activeRecommendation?.symbol}
              onSelectEvent={(event) => {
                const rec = recommendations.find((item) => item.symbol === event.symbol) ?? null;
                setActiveRecommendation(rec);
              }}
              onSelectRecommendation={(recommendation) => {
                setActiveRecommendation(recommendation);
              }}
              onSelectPosition={(position) => {
                const rec = recommendations.find((item) => item.symbol === position.symbol) ?? null;
                if (rec) {
                  setActiveRecommendation(rec);
                }
              }}
            />
          </div>
          <div style={{ display: "grid", gap: 14, minHeight: 0, overflowY: "auto", paddingRight: 4 }}>
            <SectionLabel title="Desk Chat" />
            <SharedSummary summary={summary} />
            <GroupChat messages={sortedTimeline} onSend={handleDeskSend} />
          </div>
          <div style={{ display: "grid", gap: 14, minHeight: 0, overflowY: "auto", paddingRight: 4, alignContent: "start" }}>
            <SectionLabel title="Trade Desk" />
            <TraderAvatarPanel
              recommendation={activeRecommendation}
              avatarStatus={avatarStatus}
              timeline={sortedTimeline}
              onStart={async () => {
                if (!activeRecommendation) return;
                const status = await api.traderAvatarStart(activeRecommendation.id);
                setAvatarStatus(status);
              }}
              onStop={async () => {
                if (!activeRecommendation) return;
                await api.traderAvatarStop(activeRecommendation.id);
                const status = await api.traderAvatarStatus(activeRecommendation.id);
                setAvatarStatus(status);
              }}
              onSpeak={async (text) => {
                if (!activeRecommendation) return;
                await api.traderAvatarSpeak(activeRecommendation.id, text);
              }}
            />
            <RecommendationCard
              recommendation={activeRecommendation}
              onReady={async () => activeRecommendation && await api.readyForApproval(activeRecommendation.id).then(load)}
              onApprove={async () => activeRecommendation && await api.approve(activeRecommendation.id).then(load)}
              onExecute={async () => activeRecommendation && await api.execute(activeRecommendation.id).then(load)}
              onReject={async () => activeRecommendation && await api.reject(activeRecommendation.id, "User rejected").then(load)}
            />
            <ActivePositionCard position={activePosition} />
          </div>
        </div>
      </div>
    </main>
  );
}

function SectionLabel({ title }: { title: string }) {
  return (
    <div style={{ fontSize: 12, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--text-soft)" }}>
      {title}
    </div>
  );
}

const topButtonStyle = {
  border: "1px solid rgba(113, 217, 182, 0.4)",
  background: "rgba(113, 217, 182, 0.12)",
  color: "var(--accent)",
  borderRadius: 12,
  padding: "10px 14px",
  cursor: "pointer",
} as const;
