"use client";

export function HelpPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 1000,
      background: "rgba(0,0,0,0.6)", display: "flex", justifyContent: "center", alignItems: "flex-start",
      paddingTop: 60, overflowY: "auto",
    }} onClick={onClose}>
      <div style={{
        background: "var(--bg-panel)", border: "1px solid var(--line)", borderRadius: 16,
        width: 600, maxHeight: "80vh", overflowY: "auto", boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
      }} onClick={(e) => e.stopPropagation()}>

        <div style={{
          padding: "16px 20px", borderBottom: "1px solid var(--line)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          position: "sticky", top: 0, background: "var(--bg-panel)", zIndex: 1,
        }}>
          <strong style={{ fontSize: 16 }}>How to Use Trading Desk AI</strong>
          <button className="btn" onClick={onClose}>Close</button>
        </div>

        <div style={{ padding: "16px 20px", display: "grid", gap: 20 }}>

          <Section title="Getting Started">
            <p>Click <b>Scan Earnings</b> to find stocks with recent earnings surprises. The AI roles analyse each stock in the background and results stream in as they complete.</p>
          </Section>

          <Section title="The Three Columns">
            <Row label="Left — Inbox" text="Events tab shows earnings events with PASS/BUY/SHORT status. Recommendations tab shows actionable trades." />
            <Row label="Centre — Analysis" text="Trade panel shows the recommendation with bull/bear summary, price levels, and approve/reject controls. Desk chat below lets you talk to the AI roles." />
            <Row label="Right — Execute" text="Trader avatar for voice interaction. Portfolio shows open positions with sell/cover controls." />
          </Section>

          <Section title="Desk Chat">
            <Row label="@research" text="Ask the Research analyst about fundamentals, earnings quality, catalysts" />
            <Row label="@risk" text="Ask the Risk manager about position sizing, portfolio overlap, what could go wrong" />
            <Row label="@quant_pricing" text="Ask the Quant about price levels, entry/stop/target zones, volatility" />
            <Row label="@trader" text="Ask the Trader for the final recommendation (or just type without @)" />
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>Type @ to see a role picker with keyboard navigation. Use the filter buttons in the chat header to view one role at a time.</p>
          </Section>

          <Section title="Trade Actions">
            <Row label="BUY" text="Open or add to a long position" />
            <Row label="SELL" text="Reduce or close a long position" />
            <Row label="SHORT" text="Open a short position" />
            <Row label="COVER" text="Close a short position" />
            <Row label="PASS" text="No trade — the best action is to wait" />
          </Section>

          <Section title="Approval Flow">
            <Step n={1} text="Scan finds stocks → AI roles analyse → Trader recommends" />
            <Step n={2} text="Review the recommendation and chat with roles" />
            <Step n={3} text="Click Ready for Approval when satisfied" />
            <Step n={4} text="Click Approve (edit share count first if needed)" />
            <Step n={5} text="Click Execute to place the paper order" />
          </Section>

          <Section title="Conviction & Sizing">
            <Row label="10/10" text="125% of standard position (max confidence bonus)" />
            <Row label="8-9/10" text="100% — full standard size" />
            <Row label="7/10" text="75% — decent but not strong" />
            <Row label="Below 7" text="No trade — conviction too low" />
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>Edit the share count before approving to override. Configure thresholds in Settings.</p>
          </Section>

          <Section title="Voice Commands (Avatar)">
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>Start a call with the trader avatar, then speak these commands:</p>
            <Row label="Show me NVDA" text="Switch to a specific stock's recommendation" />
            <Row label="Show events / recommendations" text="Switch inbox tab" />
            <Row label="Approve / Approve NVDA" text="Approve the current or named recommendation" />
            <Row label="Reject / Reject this" text="Reject the current recommendation" />
            <Row label="Execute" text="Execute an approved recommendation" />
            <Row label="Sell NVDA / Close NVDA" text="Sell an open position" />
            <Row label="Status" text="Hear portfolio summary" />
            <Row label="Help" text="List available voice commands" />
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>Any other speech is treated as a question for the Trader role.</p>
          </Section>

          <Section title="Settings">
            <p>Click <b>Settings</b> in the header to configure strategy parameters: universe filters, entry conditions, risk limits, conviction thresholds, hold periods, execution rules, and PEAD scoring weights.</p>
          </Section>

        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--accent)", marginBottom: 8, paddingBottom: 4, borderBottom: "1px solid var(--line)" }}>
        {title}
      </div>
      <div style={{ display: "grid", gap: 6, fontSize: 13, color: "var(--text-soft)" }}>
        {children}
      </div>
    </div>
  );
}

function Row({ label, text }: { label: string; text: string }) {
  return (
    <div style={{ display: "flex", gap: 10 }}>
      <span style={{ color: "var(--text)", fontWeight: 600, minWidth: 120, flexShrink: 0 }}>{label}</span>
      <span>{text}</span>
    </div>
  );
}

function Step({ n, text }: { n: number; text: string }) {
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
      <span style={{ width: 22, height: 22, borderRadius: "50%", background: "var(--accent-glow)", border: "1px solid var(--accent-border)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: "var(--accent)", flexShrink: 0 }}>{n}</span>
      <span>{text}</span>
    </div>
  );
}
