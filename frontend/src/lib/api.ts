import { EventItem, Position, Recommendation, RoleMessage, Summary, TraderAvatarStatus } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
  }
  return response.json();
}

export const api = {
  events: () => fetchJson<{ events: EventItem[] }>("/events"),
  scan: () => fetchJson<{ results: unknown[] }>("/scan", { method: "POST" }),
  randomEvent: () => fetchJson<{ event: EventItem; recommendation: Recommendation }>("/demo/random-event", { method: "POST" }),
  recs: () => fetchJson<{ recommendations: Recommendation[] }>("/recs"),
  rec: (id: string) =>
    fetchJson<{ recommendation: Recommendation; summary: Summary; timeline: RoleMessage[] }>(`/recs/${id}`),
  discuss: (id: string, message: string) =>
    fetchJson<RoleMessage>(`/recs/${id}/discuss`, { method: "POST", body: JSON.stringify({ message }) }),
  readyForApproval: (id: string) => fetchJson(`/recs/${id}/ready`, { method: "POST" }),
  approve: (id: string, shares?: number) => fetchJson(`/recs/${id}/approve`, { method: "POST", body: JSON.stringify({ shares }) }),
  execute: (id: string) => fetchJson(`/recs/${id}/execute`, { method: "POST" }),
  reject: (id: string, reason: string) =>
    fetchJson(`/recs/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  roleChat: (role: string, recommendationId: string, message: string) =>
    fetchJson<RoleMessage>(`/roles/${role}/chat`, {
      method: "POST",
      body: JSON.stringify({ recommendation_id: recommendationId, message }),
    }),
  traderAvatarStatus: (recommendationId?: string) =>
    fetchJson<TraderAvatarStatus>(`/trader/avatar/status${recommendationId ? `?recommendation_id=${encodeURIComponent(recommendationId)}` : ""}`),
  traderAvatarStart: (recommendationId: string) =>
    fetchJson<TraderAvatarStatus>("/trader/avatar/start", {
      method: "POST",
      body: JSON.stringify({ recommendation_id: recommendationId }),
    }),
  traderAvatarSpeak: (recommendationId: string, text: string, priority = "APPEND") =>
    fetchJson("/trader/avatar/speak", {
      method: "POST",
      body: JSON.stringify({ recommendation_id: recommendationId, text, priority }),
    }),
  traderAvatarStop: (recommendationId: string) =>
    fetchJson("/trader/avatar/stop", {
      method: "POST",
      body: JSON.stringify({ recommendation_id: recommendationId }),
    }),
  positions: () => fetchJson<{ positions: Position[] }>("/positions"),
  sellTrade: (tradeId: string, shares: number) =>
    fetchJson<{ trade: unknown; pnl: number; shares_sold: number }>(`/trades/${tradeId}/sell`, {
      method: "POST", body: JSON.stringify({ shares }),
    }),
  portfolio: () => fetchJson<Record<string, unknown>>("/portfolio"),
};

export const streamUrl = `${API_BASE.replace(/\/api$/, "")}/api/stream`;
