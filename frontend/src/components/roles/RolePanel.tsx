import { RoleMessage } from "@/lib/types";

type Props = {
  role: string;
  messages: RoleMessage[];
  onSend: (role: string, message: string) => void;
};

export function RolePanel({ role, messages, onSend }: Props) {
  return (
    <section
      style={{
        border: "1px solid var(--line)",
        borderRadius: 20,
        background: "var(--bg-panel)",
        padding: 16,
        display: "grid",
        gap: 12,
        minHeight: 180,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <strong style={{ fontSize: 18, textTransform: "capitalize" }}>{role.replace("_", " ")}</strong>
        <span style={{ color: "var(--text-soft)", fontSize: 12 }}>Own context</span>
      </div>
      <div style={{ display: "grid", gap: 10, maxHeight: 240, overflowY: "auto" }}>
        {messages.length === 0 ? (
          <div style={{ color: "var(--text-soft)", fontSize: 14 }}>No discussion yet.</div>
        ) : (
          messages.map((message) => (
            <div key={message.id} style={{ padding: 12, borderRadius: 14, background: "var(--bg-panel-soft)" }}>
              <div style={{ fontSize: 13, color: "var(--text-soft)", marginBottom: 6 }}>{message.sender}</div>
              <div style={{ marginBottom: 8 }}>{message.message_text}</div>
              {Object.keys(message.structured_payload ?? {}).length > 0 ? (
                <pre
                  style={{
                    margin: 0,
                    whiteSpace: "pre-wrap",
                    fontSize: 12,
                    color: "var(--text-soft)",
                  }}
                >
                  {JSON.stringify(message.structured_payload, null, 2)}
                </pre>
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
          onSend(role, value);
          form.reset();
        }}
        style={{ display: "flex", gap: 8 }}
      >
        <input
          name="message"
          placeholder={`Ask ${role.replace("_", " ")}...`}
          style={{
            flex: 1,
            borderRadius: 12,
            border: "1px solid var(--line)",
            background: "#0b1728",
            color: "var(--text)",
            padding: "10px 12px",
          }}
        />
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
      </form>
    </section>
  );
}
