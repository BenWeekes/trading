"use client";

import { Recommendation, TraderAvatarStatus } from "@/lib/types";
import { useAgoraAvatar } from "@/hooks/useAgoraAvatar";
import { useState } from "react";

// Inline SVG icons
function MicIcon({ size = 16 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>;
}
function MicOffIcon({ size = 16 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="2" x2="22" y1="2" y2="22"/><path d="M18.89 13.23A7.12 7.12 0 0 0 19 12v-2"/><path d="M5 10v2a7 7 0 0 0 12 .84"/><path d="M15 9.34V5a3 3 0 0 0-5.68-1.33"/><path d="M9 9v3a3 3 0 0 0 5.12 2.12"/><line x1="12" x2="12" y1="19" y2="22"/></svg>;
}
function PhoneIcon({ size = 14 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92Z"/></svg>;
}
function PhoneOffIcon({ size = 14 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.42 19.42 0 0 1-3.33-2.67"/><path d="M22 2 2 22"/><path d="M8.77 5.7A19.79 19.79 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91"/></svg>;
}

type Props = {
  recommendation?: Recommendation | null;
  avatarStatus?: TraderAvatarStatus | null;
  onStart: () => Promise<TraderAvatarStatus | null>;
  onStop: () => Promise<void>;
};

export function InlineAvatar({ recommendation, avatarStatus, onStart, onStop }: Props) {
  const agora = useAgoraAvatar();
  const [starting, setStarting] = useState(false);
  const isLive = agora.connected;

  async function handleStart() {
    if (!recommendation || starting) return;
    setStarting(true);
    try {
      const status = await onStart();
      if (status?.session) {
        await agora.join({ appId: status.session.appid, channel: status.session.channel, token: status.session.token, uid: status.session.uid });
      }
    } catch (e) { console.error(e); }
    finally { setStarting(false); }
  }

  async function handleStop() {
    await agora.leave();
    await onStop();
  }

  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", width: 420, flexShrink: 0, alignSelf: "stretch", overflow: "hidden" }}>
      {/* Video area — stretches to fill */}
      <div
        ref={agora.videoContainerRef}
        style={{
          background: "#060d18", flex: 1, minHeight: 140,
          display: isLive && agora.hasVideo ? "block" : "flex",
          alignItems: "center", justifyContent: "center", overflow: "hidden",
        }}
      >
        {!isLive && (
          <div style={{ color: "var(--text-muted)", fontSize: 12, textAlign: "center", padding: 16 }}>
            <div style={{ fontSize: 28, marginBottom: 8, opacity: 0.3 }}>💼</div>
            {starting ? "Connecting..." : "Trader"}
          </div>
        )}
        {isLive && !agora.hasVideo && (
          <div style={{ color: "var(--accent)", fontSize: 12, textAlign: "center", padding: 16 }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>🎤</div>
            {agora.hasAudio ? "Audio live" : "Connecting..."}
          </div>
        )}
      </div>

      {/* Controls */}
      <div style={{
        display: "flex", gap: 6, justifyContent: "center", padding: "8px 10px",
        borderTop: "1px solid var(--line)",
      }}>
        {!isLive ? (
          <button onClick={handleStart} disabled={!recommendation || starting} style={{
            display: "flex", alignItems: "center", gap: 4, padding: "4px 10px", borderRadius: 6,
            background: "var(--accent-glow)", border: "1px solid var(--accent-border)",
            color: "var(--accent)", fontSize: 11, fontWeight: 600, cursor: "pointer",
          }}>
            <PhoneIcon /> {starting ? "..." : "Call"}
          </button>
        ) : (
          <>
            <button onClick={agora.toggleMute} title={agora.muted ? "Unmute" : "Mute"} style={{
              width: 32, height: 32, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center",
              background: agora.muted ? "rgba(255,122,122,0.15)" : "var(--bg-panel-soft)",
              border: `1px solid ${agora.muted ? "rgba(255,122,122,0.4)" : "var(--line)"}`,
              color: agora.muted ? "var(--danger)" : "var(--text)", cursor: "pointer",
            }}>
              {agora.muted ? <MicOffIcon /> : <MicIcon />}
            </button>
            <button onClick={handleStop} style={{
              display: "flex", alignItems: "center", gap: 4, padding: "4px 10px", borderRadius: 6,
              background: "rgba(255,122,122,0.15)", border: "1px solid rgba(255,122,122,0.4)",
              color: "var(--danger)", fontSize: 11, fontWeight: 600, cursor: "pointer",
            }}>
              <PhoneOffIcon /> End
            </button>
          </>
        )}
      </div>
    </div>
  );
}
