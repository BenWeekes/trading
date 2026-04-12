import { Summary } from "@/lib/types";

export function SharedSummary({ summary }: { summary?: Summary | null }) {
  return (
    <section
      style={{
        border: "1px solid var(--line)",
        borderRadius: 20,
        background: "linear-gradient(180deg, rgba(18, 37, 61, 0.92), rgba(13, 28, 48, 0.92))",
        padding: 16,
        boxShadow: "var(--shadow)",
      }}
    >
      <div style={{ fontSize: 12, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--text-soft)", marginBottom: 10 }}>
        Shared Summary
      </div>
      <div style={{ display: "grid", gap: 10 }}>
        <div><strong>Bull:</strong> {summary?.bull_case ?? "Waiting for role analysis."}</div>
        <div><strong>Bear:</strong> {summary?.bear_case ?? "Waiting for role analysis."}</div>
        <div><strong>Disagreement:</strong> {summary?.key_disagreement ?? "No material disagreement yet."}</div>
      </div>
    </section>
  );
}
