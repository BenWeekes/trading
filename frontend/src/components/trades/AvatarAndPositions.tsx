"use client";

import { useState } from "react";
import { Position, Recommendation, TraderAvatarStatus } from "@/lib/types";
import { useAgoraAvatar } from "@/hooks/useAgoraAvatar";

type Props = {
  positions: Position[];
  activeSymbol?: string | null;
  avatarStatus?: TraderAvatarStatus | null;
  recommendation?: Recommendation | null;
  onSell: (symbol: string, shares: number) => void;
  onAvatarStart: () => Promise<TraderAvatarStatus | null>;
  onAvatarStop: () => Promise<void>;
};

export function AvatarAndPositions({ positions, activeSymbol, avatarStatus, recommendation, onSell, onAvatarStart, onAvatarStop }: Props) {
  const agora = useAgoraAvatar();
  const [starting, setStarting] = useState(false);

  async function handleStartCall() {
    if (!recommendation || starting) return;
    setStarting(true);
    try {
      // Phase 1+2: Backend starts agent and returns tokens
      const status = await onAvatarStart();
      if (!status?.session) throw new Error("No session returned");

      // Phase 3: Frontend joins RTC channel for audio/video
      await agora.join({
        appId: status.session.appid,
        channel: status.session.channel,
        token: status.session.token,
        uid: status.session.uid,
      });
    } catch (err: any) {
      console.error("Start call failed:", err);
    } finally {
      setStarting(false);
    }
  }

  async function handleEndCall() {
    await agora.leave();
    await onAvatarStop();
  }

  const isLive = agora.connected;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Avatar Panel */}
      <div className="panel">
        <div className="panel-header">
          <span>Trader Avatar</span>
          <span style={{ fontSize: 10, color: isLive ? "var(--accent)" : "var(--text-muted)" }}>
            {isLive ? (agora.hasAudio ? "Live" : "Connected") : "Offline"}
          </span>
        </div>

        {/* Video container */}
        <div
          ref={agora.videoContainerRef}
          style={{
            background: "#060d18",
            minHeight: 240,
            display: isLive && agora.hasVideo ? "block" : "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            overflow: "hidden",
            borderRadius: "0",
          }}
        >
          {!isLive && (
            <div style={{ color: "var(--text-muted)", fontSize: 13, textAlign: "center", padding: 24 }}>
              {starting ? "Starting call..." : "Press Start Call to connect with the trader avatar."}
            </div>
          )}
          {isLive && !agora.hasVideo && (
            <div style={{ color: "var(--accent)", fontSize: 13, textAlign: "center", padding: 24 }}>
              {agora.hasAudio ? "Audio connected. Waiting for avatar video..." : "Connecting..."}
            </div>
          )}
        </div>

        {agora.error && (
          <div style={{ padding: "6px 16px", fontSize: 12, color: "var(--danger)", background: "rgba(255,122,122,0.06)" }}>
            {agora.error}
          </div>
        )}

        {/* Controls */}
        <div style={{ padding: "10px 16px", display: "flex", gap: 8, borderTop: "1px solid var(--line)", justifyContent: "center" }}>
          {!isLive ? (
            <button className="btn btn-accent" onClick={handleStartCall} disabled={!recommendation || starting}>
              {starting ? "Starting..." : "Start Call"}
            </button>
          ) : (
            <>
              <button
                className={`btn ${agora.muted ? "btn-danger" : ""}`}
                onClick={agora.toggleMute}
                title={agora.muted ? "Unmute microphone" : "Mute microphone"}
                style={{ minWidth: 44, textAlign: "center" }}
              >
                {agora.muted ? "\u{1F507}" : "\u{1F3A4}"}
              </button>
              <button className="btn btn-danger" onClick={handleEndCall}>
                End Call
              </button>
            </>
          )}
        </div>
      </div>

      {/* Portfolio */}
      <div className="panel">
        <div className="panel-header">
          <span>Portfolio</span>
          <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{positions.length} position{positions.length !== 1 ? "s" : ""}</span>
        </div>
        <div style={{ maxHeight: 400, overflowY: "auto" }}>
          {positions.length === 0 ? (
            <div style={{ padding: 20, color: "var(--text-muted)", fontSize: 13, textAlign: "center" }}>No open positions.</div>
          ) : (
            positions.map((pos) => (
              <PositionRow key={pos.id} position={pos} active={pos.symbol === activeSymbol} onSell={onSell} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function PositionRow({ position, active, onSell }: { position: Position; active: boolean; onSell: (s: string, n: number) => void }) {
  const [sellShares, setSellShares] = useState(position.shares ?? 0);
  const [showSell, setShowSell] = useState(false);
  const pnl = position.unrealized_pnl ?? 0;
  const total = position.shares ?? 0;

  return (
    <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--line)", background: active ? "var(--accent-glow)" : "transparent" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <strong style={{ fontSize: 14 }}>{position.symbol}</strong>
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 8 }}>{total} sh @ ${Number(position.entry_price ?? 0).toFixed(2)}</span>
        </div>
        <div style={{ fontSize: 14, fontWeight: 600, color: pnl >= 0 ? "var(--buy)" : "var(--sell)" }}>
          {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
        </div>
      </div>
      {!showSell ? (
        <button onClick={() => setShowSell(true)} style={{ marginTop: 6, fontSize: 11, color: "var(--sell)", background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}>Sell...</button>
      ) : (
        <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center" }}>
          <input type="number" value={sellShares} min={1} max={total} onChange={(e) => setSellShares(Math.min(Number(e.target.value), total))}
            style={{ width: 60, padding: "4px 8px", borderRadius: 6, border: "1px solid var(--line)", background: "var(--bg)", color: "var(--text)", fontSize: 12, textAlign: "center" }} />
          <button className="btn btn-danger" style={{ fontSize: 11, padding: "4px 10px" }} onClick={() => { onSell(position.symbol, sellShares); setShowSell(false); }}>Sell {sellShares}</button>
          {sellShares < total && <button className="btn" style={{ fontSize: 11, padding: "4px 10px" }} onClick={() => { onSell(position.symbol, total); setShowSell(false); }}>All</button>}
          <button style={{ fontSize: 11, color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer" }} onClick={() => setShowSell(false)}>Cancel</button>
        </div>
      )}
    </div>
  );
}
