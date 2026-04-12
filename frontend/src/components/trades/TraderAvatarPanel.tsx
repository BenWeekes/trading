import { Recommendation, RoleMessage, TraderAvatarStatus } from "@/lib/types";

type Props = {
  recommendation?: Recommendation | null;
  avatarStatus?: TraderAvatarStatus | null;
  timeline: RoleMessage[];
  onStart: () => void;
  onStop: () => void;
  onSpeak: (text: string) => void;
};

export function TraderAvatarPanel({ recommendation, avatarStatus, timeline, onStart, onStop, onSpeak }: Props) {
  const latestTraderMessage = [...timeline].reverse().find((message) => message.role === "trader" && message.sender === "role:trader");
  const enabled = avatarStatus?.enabled;
  const session = avatarStatus?.session;

  return (
    <section style={{ border: "1px solid var(--line)", borderRadius: 20, background: "var(--bg-panel)", padding: 18, display: "grid", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <strong style={{ fontSize: 18 }}>Trader Avatar</strong>
        <span style={{ color: "var(--text-soft)", fontSize: 12 }}>
          {session ? `Live on ${session.channel}` : enabled ? "Ready" : "Disabled"}
        </span>
      </div>
      <div style={{ color: "var(--text-soft)", fontSize: 14 }}>
        The trader is the only voice/avatar role. Supporting roles stay text-first in the shared desk chat.
      </div>
      <div style={{ border: "1px solid var(--line)", borderRadius: 16, overflow: "hidden", background: "#08111d", minHeight: 180 }}>
        {enabled && avatarStatus?.client_url ? (
          <iframe
            src={avatarStatus.client_url}
            title="Trader Avatar"
            style={{ width: "100%", height: 220, border: 0, display: "block" }}
          />
        ) : (
            <div style={{ minHeight: 180, display: "grid", placeItems: "center", color: "var(--text-soft)", padding: 24 }}>
            Configure Agora to enable the trader avatar.
          </div>
        )}
      </div>
      <div style={{ display: "grid", gap: 6, fontSize: 13, color: "var(--text-soft)" }}>
        <div>Active symbol: {recommendation?.symbol ?? "-"}</div>
        <div>Profile: {avatarStatus?.profile ?? "-"}</div>
        <div>Agent: {session?.agent_id ?? "No active session"}</div>
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button onClick={onStart} disabled={!recommendation || !enabled} style={buttonStyle("var(--accent)")}>
          Start Voice Session
        </button>
        <button onClick={onStop} disabled={!session} style={buttonStyle("var(--warn)")}>
          Stop Session
        </button>
        <button
          onClick={() => latestTraderMessage && onSpeak(latestTraderMessage.message_text)}
          disabled={!session || !latestTraderMessage}
          style={buttonStyle("var(--text)")}
          title={latestTraderMessage?.message_text}
        >
          Speak Latest Trader View
        </button>
      </div>
    </section>
  );
}

function buttonStyle(color: string) {
  return {
    border: `1px solid ${color}`,
    background: "transparent",
    color,
    borderRadius: 12,
    padding: "10px 14px",
    cursor: "pointer",
  } as const;
}
