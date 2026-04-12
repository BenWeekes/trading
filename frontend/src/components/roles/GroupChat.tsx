"use client";

import { useEffect, useRef } from "react";
import { RoleMessage } from "@/lib/types";

type Props = {
  messages: RoleMessage[];
  onSend: (message: string) => void;
  activeSymbol?: string | null;
};

const ROLE_ICONS: Record<string, string> = {
  research: "\u{1F4CA}",
  risk: "\u{1F6E1}",
  quant_pricing: "\u{1F4C8}",
  trader: "\u{1F4BC}",
};

const ROLE_LABELS: Record<string, string> = {
  research: "Research",
  risk: "Risk",
  quant_pricing: "Quant",
  trader: "Trader",
};

function senderLabel(sender: string, role: string): string {
  if (sender === "user") return "You";
  const roleKey = sender.replace("role:", "");
  return ROLE_LABELS[roleKey] ?? ROLE_LABELS[role] ?? role;
}

function senderIcon(sender: string, role: string): string {
  if (sender === "user") return "\u{1F464}";
  const roleKey = sender.replace("role:", "");
  return ROLE_ICONS[roleKey] ?? ROLE_ICONS[role] ?? "\u{1F916}";
}

function roleColorClass(sender: string, role: string): string {
  if (sender === "user") return "role-user";
  const roleKey = sender.replace("role:", "");
  return `role-${roleKey}` || `role-${role}`;
}

export function GroupChat({ messages, onSend, activeSymbol }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length]);

  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
      <div className="panel-header">
        <span>Desk Conversation {activeSymbol ? `\u2014 ${activeSymbol}` : ""}</span>
        <span style={{ fontSize: 10, color: "var(--text-muted)" }} title="Use @research, @risk, @quant_pricing, or @trader to direct a message. Plain messages go to the trader.">
          @mentions enabled
        </span>
      </div>

      {/* Messages */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: "8px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
        {messages.length === 0 ? (
          <div style={{ color: "var(--text-muted)", fontSize: 13, padding: 20, textAlign: "center" }}>
            {activeSymbol ? "No conversation yet. Ask the desk something." : "Select an event to start a conversation."}
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.sender === "user";
            const isQuery = msg.structured_payload?.type === "role_query";
            return (
              <div key={msg.id} style={{
                padding: "10px 12px",
                borderRadius: 12,
                background: isUser ? "rgba(113, 217, 182, 0.06)" : isQuery ? "rgba(96, 165, 250, 0.06)" : "var(--bg-panel-soft)",
                border: `1px solid ${isUser ? "rgba(113, 217, 182, 0.2)" : "var(--line)"}`,
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <span className={roleColorClass(msg.sender, msg.role)} style={{ fontSize: 12, fontWeight: 600 }}>
                    {senderIcon(msg.sender, msg.role)} {senderLabel(msg.sender, msg.role)}
                    {isQuery && <span style={{ color: "var(--text-muted)", fontWeight: 400 }}> asked {ROLE_LABELS[msg.role] ?? msg.role}</span>}
                  </span>
                  <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div style={{ fontSize: 13, whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{msg.message_text}</div>
                {msg.structured_payload && Object.keys(msg.structured_payload).length > 1 && (
                  <details style={{ marginTop: 6 }}>
                    <summary style={{ cursor: "pointer", color: "var(--text-muted)", fontSize: 11 }}>Structured output</summary>
                    <pre style={{ margin: "6px 0 0", whiteSpace: "pre-wrap", fontSize: 11, color: "var(--text-muted)", lineHeight: 1.5 }}>
                      {JSON.stringify(msg.structured_payload, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const fd = new FormData(e.currentTarget);
          const val = String(fd.get("message") ?? "").trim();
          if (!val) return;
          onSend(val);
          e.currentTarget.reset();
        }}
        style={{ padding: "8px 12px 12px", borderTop: "1px solid var(--line)", display: "flex", gap: 8 }}
      >
        <input
          name="message"
          placeholder={activeSymbol ? `Ask the desk about ${activeSymbol}...` : "Select an event first"}
          disabled={!activeSymbol}
          style={{
            flex: 1, padding: "10px 14px", borderRadius: 10,
            border: "1px solid var(--line)", background: "var(--bg)",
            color: "var(--text)", fontSize: 13,
          }}
        />
        <button type="submit" className="btn btn-accent" disabled={!activeSymbol}>Send</button>
      </form>
    </div>
  );
}
