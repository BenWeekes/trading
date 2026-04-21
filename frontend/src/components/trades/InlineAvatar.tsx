"use client";

import { Recommendation, TraderAvatarStatus } from "@/lib/types";
import { useAgoraAvatar } from "@/hooks/useAgoraAvatar";
import { useState } from "react";

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
  const showControls = isLive && agora.hasVideo;

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
              <div style={{ fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8, color: "var(--accent)" }}>
                Trader Avatar
              </div>
              {starting ? "Connecting to voice session..." : "Ready to start voice session"}
            </div>
          )}
          {isLive && !agora.hasVideo && (
            <div style={{ color: "var(--accent)", fontSize: 12, textAlign: "center", padding: 16 }}>
              {agora.hasAudio ? "Audio connected. Waiting for avatar video..." : "Connecting avatar..."}
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
            {starting ? "Starting..." : "Start Call"}
          </button>
        ) : showControls ? (
          <>
            <button onClick={agora.toggleMute} title={agora.muted ? "Unmute" : "Mute"} style={{
              minWidth: 72, height: 32, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center",
              background: agora.muted ? "rgba(255,122,122,0.15)" : "var(--bg-panel-soft)",
              border: `1px solid ${agora.muted ? "rgba(255,122,122,0.4)" : "var(--line)"}`,
              color: agora.muted ? "var(--danger)" : "var(--text)", cursor: "pointer", fontSize: 11, fontWeight: 600, padding: "0 10px",
            }}>
              {agora.muted ? "Unmute" : "Mute"}
            </button>
            <button onClick={handleStop} style={{
              display: "flex", alignItems: "center", gap: 4, padding: "4px 10px", borderRadius: 6,
              background: "rgba(255,122,122,0.15)", border: "1px solid rgba(255,122,122,0.4)",
              color: "var(--danger)", fontSize: 11, fontWeight: 600, cursor: "pointer",
            }}>
              End Call
            </button>
          </>
        ) : (
          <div style={{ color: "var(--text-muted)", fontSize: 11 }}>Connecting...</div>
        )}
      </div>
    </div>
  );
}
