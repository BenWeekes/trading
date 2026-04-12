"use client";

import { useEffect, useRef, useState } from "react";
import { RoleMessage } from "@/lib/types";

type Props = {
  messages: RoleMessage[];
  onSend: (message: string) => void;
  activeSymbol?: string | null;
};

const ROLES = [
  { key: "research", icon: "\u{1F4CA}", label: "Research", color: "#60a5fa" },
  { key: "risk", icon: "\u{1F6E1}", label: "Risk", color: "#f87171" },
  { key: "quant_pricing", icon: "\u{1F4C8}", label: "Quant", color: "#a78bfa" },
  { key: "trader", icon: "\u{1F4BC}", label: "Trader", color: "var(--accent)" },
];

const ROLE_MAP = Object.fromEntries(ROLES.map((r) => [r.key, r]));

function senderInfo(sender: string, role: string) {
  if (sender === "user") return { icon: "\u{1F464}", label: "You", color: "var(--text)" };
  const key = sender.replace("role:", "");
  return ROLE_MAP[key] ?? ROLE_MAP[role] ?? { icon: "\u{1F916}", label: role, color: "var(--text-soft)" };
}

export function GroupChat({ messages, onSend, activeSymbol }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [inputValue, setInputValue] = useState("");
  const [roleFilter, setRoleFilter] = useState<string | null>(null);
  const [showMentions, setShowMentions] = useState(false);
  const [mentionFilter, setMentionFilter] = useState("");
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages.length]);

  const filteredRoles = ROLES.filter((r) =>
    r.key.startsWith(mentionFilter) || r.label.toLowerCase().startsWith(mentionFilter)
  );

  function handleInputChange(value: string) {
    setInputValue(value);
    const atMatch = value.match(/@(\w*)$/);
    if (atMatch) {
      setShowMentions(true);
      setMentionFilter(atMatch[1].toLowerCase());
      setSelectedIdx(0);
    } else {
      setShowMentions(false);
    }
  }

  function insertMention(roleKey: string) {
    const before = inputValue.replace(/@\w*$/, "");
    setInputValue(`${before}@${roleKey} `);
    setShowMentions(false);
    inputRef.current?.focus();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (showMentions && filteredRoles.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIdx((i) => (i + 1) % filteredRoles.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIdx((i) => (i - 1 + filteredRoles.length) % filteredRoles.length);
      } else if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        insertMention(filteredRoles[selectedIdx].key);
      } else if (e.key === "Escape") {
        setShowMentions(false);
      }
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const val = inputValue.trim();
    if (!val || sending) return;
    setSending(true);
    setInputValue("");
    setShowMentions(false);
    try {
      await onSend(val);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
      <div className="panel-header" style={{ flexWrap: "wrap", gap: 6 }}>
        <span>Desk Chat {activeSymbol ? `\u2014 ${activeSymbol}` : ""}</span>
        <div style={{ display: "flex", gap: 4 }}>
          <FilterChip active={roleFilter === null} onClick={() => setRoleFilter(null)} color="var(--text-soft)">All</FilterChip>
          {ROLES.map((r) => (
            <FilterChip key={r.key} active={roleFilter === r.key} onClick={() => setRoleFilter(roleFilter === r.key ? null : r.key)} color={r.color}>
              {r.icon}
            </FilterChip>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: "8px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
        {messages.length === 0 ? (
          <div style={{ color: "var(--text-muted)", fontSize: 13, padding: 20, textAlign: "center" }}>
            {activeSymbol ? "Ask the desk something, or type @ to pick a role." : "Select an event to start."}
          </div>
        ) : (
          messages
          .filter((msg) => {
            if (!roleFilter) return true;
            const senderKey = msg.sender.replace("role:", "");
            return senderKey === roleFilter || msg.role === roleFilter || msg.sender === "user";
          })
          .map((msg) => {
            const info = senderInfo(msg.sender, msg.role);
            const isQuery = msg.structured_payload?.type === "role_query";
            return (
              <div key={msg.id} style={{
                padding: "8px 10px", borderRadius: 10,
                background: msg.sender === "user" ? "rgba(113, 217, 182, 0.06)" : isQuery ? "rgba(96, 165, 250, 0.06)" : "var(--bg-panel-soft)",
                border: `1px solid ${msg.sender === "user" ? "rgba(113, 217, 182, 0.15)" : "transparent"}`,
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 3 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: info.color }}>
                    {info.icon} {info.label}
                    {isQuery && <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>{" "}asked {ROLE_MAP[msg.role]?.label ?? msg.role}</span>}
                  </span>
                  <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{new Date(msg.timestamp).toLocaleTimeString()}</span>
                </div>
                <div style={{ fontSize: 13, whiteSpace: "pre-wrap", lineHeight: 1.55 }}>{msg.message_text}</div>
              </div>
            );
          })
        )}
        {sending && (
          <div style={{ padding: "8px 10px", borderRadius: 10, background: "var(--bg-panel-soft)", color: "var(--text-muted)", fontSize: 12 }}>
            Thinking...
          </div>
        )}
      </div>

      {/* Input with @ autocomplete + keyboard nav */}
      <div style={{ position: "relative", padding: "8px 12px 12px", borderTop: "1px solid var(--line)" }}>
        {showMentions && filteredRoles.length > 0 && (
          <div style={{
            position: "absolute", bottom: "100%", left: 12, right: 12,
            background: "var(--bg-panel)", border: "1px solid var(--line)",
            borderRadius: 10, padding: 4, boxShadow: "var(--shadow)",
          }}>
            {filteredRoles.map((r, i) => (
              <button
                key={r.key}
                onClick={() => insertMention(r.key)}
                style={{
                  display: "flex", alignItems: "center", gap: 8, width: "100%",
                  padding: "8px 10px", background: i === selectedIdx ? "var(--bg-panel-soft)" : "transparent",
                  border: "none", color: "var(--text)", cursor: "pointer", borderRadius: 6, fontSize: 13,
                }}
              >
                <span style={{ color: r.color }}>{r.icon}</span>
                <span style={{ fontWeight: 600 }}>@{r.key}</span>
                <span style={{ color: "var(--text-muted)" }}>{r.label}</span>
              </button>
            ))}
          </div>
        )}
        <form onSubmit={handleSubmit} style={{ display: "flex", gap: 8 }}>
          <input
            ref={inputRef}
            value={inputValue}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={activeSymbol ? `Message about ${activeSymbol}... (@ to mention)` : "Select an event first"}
            disabled={!activeSymbol || sending}
            style={{
              flex: 1, padding: "10px 14px", borderRadius: 10,
              border: "1px solid var(--line)", background: "var(--bg)",
              color: "var(--text)", fontSize: 13,
            }}
          />
          <button type="submit" className="btn btn-accent" disabled={!activeSymbol || sending || !inputValue.trim()}>
            {sending ? "..." : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}

function FilterChip({ active, onClick, color, children }: { active: boolean; onClick: () => void; color: string; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "2px 8px", borderRadius: 6, fontSize: 11, fontWeight: 600,
        border: `1px solid ${active ? color : "transparent"}`,
        background: active ? "rgba(255,255,255,0.06)" : "transparent",
        color: active ? color : "var(--text-muted)",
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}
