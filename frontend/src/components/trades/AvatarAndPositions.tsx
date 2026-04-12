"use client";

import { useState } from "react";
// Inline SVG icons matching lucide-react style (avoid npm install issues)
function MicIcon({ size = 18, ...p }: { size?: number } & React.SVGProps<SVGSVGElement>) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>;
}
function MicOffIcon({ size = 18, ...p }: { size?: number } & React.SVGProps<SVGSVGElement>) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><line x1="2" x2="22" y1="2" y2="22"/><path d="M18.89 13.23A7.12 7.12 0 0 0 19 12v-2"/><path d="M5 10v2a7 7 0 0 0 12 .84"/><path d="M15 9.34V5a3 3 0 0 0-5.68-1.33"/><path d="M9 9v3a3 3 0 0 0 5.12 2.12"/><line x1="12" x2="12" y1="19" y2="22"/></svg>;
}
function PhoneIcon({ size = 16, ...p }: { size?: number } & React.SVGProps<SVGSVGElement>) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92Z"/></svg>;
}
function PhoneOffIcon({ size = 16, ...p }: { size?: number } & React.SVGProps<SVGSVGElement>) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.42 19.42 0 0 1-3.33-2.67"/><path d="M22 2 2 22"/><path d="M8.77 5.7A19.79 19.79 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91"/></svg>;
}
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
      const status = await onAvatarStart();
      if (!status?.session) throw new Error("No session returned");
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
      <div className="panel" style={{ overflow: "hidden" }}>
        <div className="panel-header">
          <span>Trader Avatar</span>
          <span style={{ fontSize: 10, color: isLive ? "var(--accent)" : "var(--text-muted)" }}>
            {isLive ? (agora.hasAudio ? "Live" : "Connected") : "Offline"}
          </span>
        </div>

        {/* Video container — explicit height so Agora's 100% child resolves correctly */}
        <div
          ref={agora.videoContainerRef}
          style={{
            background: "#060d18",
            height: 280,
            minHeight: 280,
            display: isLive && agora.hasVideo ? "block" : "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {!isLive && (
            <div style={{ color: "var(--text-muted)", fontSize: 13, textAlign: "center", padding: 24 }}>
              {starting ? "Starting call..." : "Press Start Call to connect."}
            </div>
          )}
          {isLive && !agora.hasVideo && (
            <div style={{ color: "var(--accent)", fontSize: 13, textAlign: "center", padding: 24 }}>
              {agora.hasAudio ? "Audio connected. Waiting for video..." : "Connecting..."}
            </div>
          )}
        </div>

        {agora.error && (
          <div style={{ padding: "6px 16px", fontSize: 12, color: "var(--danger)", background: "rgba(255,122,122,0.06)" }}>
            {agora.error}
          </div>
        )}

        {/* Control bar — matching agent-samples style */}
        <div style={{
          padding: "12px 16px",
          borderTop: "1px solid var(--line)",
          display: "flex",
          gap: 12,
          justifyContent: "center",
          alignItems: "center",
        }}>
          {!isLive ? (
            <button onClick={handleStartCall} disabled={!recommendation || starting} style={{
              display: "flex", alignItems: "center", gap: 8,
              padding: "10px 20px", borderRadius: 10,
              background: "var(--accent-glow)", border: "1px solid var(--accent-border)",
              color: "var(--accent)", fontSize: 13, fontWeight: 600, cursor: "pointer",
            }}>
              <PhoneIcon size={16} />
              {starting ? "Starting..." : "Start Call"}
            </button>
          ) : (
            <>
              {/* Mute button */}
              <button onClick={agora.toggleMute} title={agora.muted ? "Unmute" : "Mute"} style={{
                display: "flex", alignItems: "center", justifyContent: "center",
                width: 44, height: 44, borderRadius: 10,
                background: agora.muted ? "rgba(255,122,122,0.15)" : "var(--bg-panel-soft)",
                border: `1px solid ${agora.muted ? "rgba(255,122,122,0.4)" : "var(--line)"}`,
                color: agora.muted ? "var(--danger)" : "var(--text)",
                cursor: "pointer",
              }}>
                {agora.muted ? <MicOffIcon size={18} /> : <MicIcon size={18} />}
              </button>

              {/* End call button */}
              <button onClick={handleEndCall} style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "10px 20px", borderRadius: 10,
                background: "rgba(255,122,122,0.15)", border: "1px solid rgba(255,122,122,0.4)",
                color: "var(--danger)", fontSize: 13, fontWeight: 600, cursor: "pointer",
              }}>
                <PhoneOffIcon size={16} />
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
