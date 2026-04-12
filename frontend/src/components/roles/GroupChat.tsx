import { RoleMessage } from "@/lib/types";

type Props = {
  messages: RoleMessage[];
  onSend: (message: string) => void;
};

const tooltip = "Use @research, @risk, @quant_pricing, or @trader to direct a message. Plain messages go to the trader.";

export function GroupChat({ messages, onSend }: Props) {
  return (
    <section
      style={{
        border: "1px solid var(--line)",
        borderRadius: 20,
        background: "var(--bg-panel)",
        padding: 16,
        display: "grid",
        gap: 12,
        minHeight: 520,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <strong style={{ fontSize: 18 }}>Desk Conversation</strong>
        <span style={{ color: "var(--text-soft)", fontSize: 12 }} title={tooltip}>
          @mentions enabled
        </span>
      </div>
      <div style={{ display: "grid", gap: 10, maxHeight: 520, overflowY: "auto", paddingRight: 4 }}>
        {messages.length === 0 ? (
          <div style={{ color: "var(--text-soft)", fontSize: 14 }}>No conversation yet.</div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              style={{
                padding: 12,
                borderRadius: 14,
                background: message.sender === "role:trader" ? "rgba(113, 217, 182, 0.08)" : "var(--bg-panel-soft)",
                border: "1px solid var(--line)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontSize: 13, color: "var(--text-soft)" }}>
                  {message.sender} {"->"} {message.role}
                </span>
                <span style={{ fontSize: 12, color: "var(--text-soft)" }}>
                  {new Date(message.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div style={{ whiteSpace: "pre-wrap", marginBottom: 6 }}>{message.message_text}</div>
              {Object.keys(message.structured_payload ?? {}).length > 0 ? (
                <details>
                  <summary style={{ cursor: "pointer", color: "var(--text-soft)", fontSize: 12 }}>Structured output</summary>
                  <pre style={{ margin: "8px 0 0", whiteSpace: "pre-wrap", fontSize: 12, color: "var(--text-soft)" }}>
                    {JSON.stringify(message.structured_payload, null, 2)}
                  </pre>
                </details>
              ) : null}
            </div>
          ))
        )}
      </div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          const form = event.currentTarget;
          const data = new FormData(form);
          const value = String(data.get("message") ?? "").trim();
          if (!value) return;
          onSend(value);
          form.reset();
        }}
        style={{ display: "grid", gap: 8 }}
      >
        <textarea
          name="message"
          rows={3}
          placeholder="Ask the desk something, or direct a role with @research / @risk / @quant_pricing / @trader"
          style={{
            width: "100%",
            borderRadius: 14,
            border: "1px solid var(--line)",
            background: "#0b1728",
            color: "var(--text)",
            padding: "12px 14px",
            resize: "vertical",
          }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: "var(--text-soft)", fontSize: 12 }}>{tooltip}</span>
          <button
            type="submit"
            style={{
              border: "1px solid rgba(113, 217, 182, 0.4)",
              background: "rgba(113, 217, 182, 0.12)",
              color: "var(--accent)",
              borderRadius: 12,
              padding: "10px 14px",
              cursor: "pointer",
            }}
          >
            Send
          </button>
        </div>
      </form>
    </section>
  );
}
