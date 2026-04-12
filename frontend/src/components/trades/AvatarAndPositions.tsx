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
  onAvatarStart: () => Promise<void>;
  onAvatarStop: () => Promise<void>;
};

export function AvatarAndPositions({ positions, activeSymbol, avatarStatus, recommendation, onSell, onAvatarStart, onAvatarStop }: Props) {
  const agora = useAgoraAvatar();
  const session = avatarStatus?.session;
  const isLive = agora.connected;

  async function handleStart() {
    await onAvatarStart();
  }

  async function handleJoinRTC() {
    if (!session) return;
    await agora.join({
      appId: session.appid,
      channel: session.channel,
      token: session.token,
      uid: session.uid,
      agentUid: session.agent_uid,
    });
  }

  async function handleStop() {
    await agora.leave();
    await onAvatarStop();
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Avatar */}
      <div className="panel">
        <div className="panel-header">
          <span>Trader Avatar</span>
          <span style={{ fontSize: 10, color: isLive ? "var(--accent)" : session ? "var(--warn)" : "var(--text-muted)" }}>
            {isLive ? (agora.agentAudioPlaying ? "Speaking" : "Live") : session ? "Agent Ready — Join RTC" : "Offline"}
          </span>
        </div>

        {/* Video area */}
        <div
          ref={agora.videoContainerRef}
          style={{
            background: "#060d18", minHeight: 220,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}
        >
          {!isLive && !session && (
            <div style={{ color: "var(--text-muted)", fontSize: 13, textAlign: "center", padding: 20 }}>
              Start a call to activate the trader avatar.
            </div>
          )}
          {session && !isLive && (
            <div style={{ color: "var(--warn)", fontSize: 13, textAlign: "center", padding: 20 }}>
              Agent started on <strong>{session.channel}</strong>. Click "Join Call" to connect audio/video.
            </div>
          )}
          {isLive && !agora.agentVideoTrack && (
            <div style={{ color: "var(--accent)", fontSize: 13, textAlign: "center", padding: 20 }}>
              Connected. Waiting for avatar video stream...
            </div>
          )}
        </div>

        {agora.error && (
          <div style={{ padding: "6px 16px", fontSize: 12, color: "var(--danger)", background: "rgba(255,122,122,0.08)" }}>
            {agora.error}
          </div>
        )}

        {/* Controls */}
        <div style={{ padding: "10px 16px", display: "flex", gap: 8, borderTop: "1px solid var(--line)" }}>
          {!session && (
            <button className="btn btn-accent" onClick={handleStart} disabled={!recommendation}>
              Start Call
            </button>
          )}
          {session && !isLive && (
            <button className="btn btn-accent" onClick={handleJoinRTC}>
              Join Call
            </button>
          )}
          {isLive && (
            <button className="btn btn-danger" onClick={handleStop}>
              End Call
            </button>
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
            <div style={{ padding: 20, color: "var(--text-muted)", fontSize: 13, textAlign: "center" }}>
              No open positions.
            </div>
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
        <button onClick={() => setShowSell(true)} style={{ marginTop: 6, fontSize: 11, color: "var(--sell)", background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}>
          Sell...
        </button>
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
