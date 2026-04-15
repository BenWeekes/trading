"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type PulseStock = {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  direction: "up" | "down" | "same";
  category: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export function MarketPulse({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [stocks, setStocks] = useState<PulseStock[]>([]);
  const [count, setCount] = useState(0);
  const [callsPerMin, setCallsPerMin] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchPulse = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/market-pulse`);
      const d = await r.json();
      setStocks(d.stocks || []);
      setCount(d.count || 0);
      setCallsPerMin(d.calls_per_min || 0);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (!open) {
      if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
      return;
    }
    fetchPulse();
    intervalRef.current = setInterval(fetchPulse, 3000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [open, fetchPulse]);

  if (!open) return null;

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 1000,
      background: "rgba(0,0,0,0.8)", display: "flex", flexDirection: "column",
    }} onClick={onClose}>
      <div style={{
        flex: 1, margin: 20, background: "var(--bg-panel)", border: "1px solid var(--line)",
        borderRadius: 16, display: "flex", flexDirection: "column", overflow: "hidden",
      }} onClick={(e) => e.stopPropagation()}>

        {/* Header */}
        <div style={{
          padding: "12px 20px", borderBottom: "1px solid var(--line)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <strong style={{ fontSize: 16 }}>Market Pulse</strong>
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{count} stocks</span>
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{callsPerMin}/min API</span>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--buy)", animation: "pulse 2s infinite" }} />
          </div>
          <button className="btn" onClick={onClose}>Close</button>
        </div>

        {/* Stock Grid */}
        <div style={{
          flex: 1, overflowY: "auto", padding: 12,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
          gap: 6,
          alignContent: "start",
        }}>
          {stocks.map((s) => (
            <StockCell key={s.symbol} stock={s} />
          ))}
        </div>
      </div>
    </div>
  );
}

function StockCell({ stock }: { stock: PulseStock }) {
  const isUp = stock.change_pct > 0;
  const isDown = stock.change_pct < 0;
  const bgColor = stock.direction === "up" ? "rgba(110, 231, 183, 0.12)"
    : stock.direction === "down" ? "rgba(252, 165, 165, 0.12)"
    : "transparent";
  const borderColor = stock.direction === "up" ? "rgba(110, 231, 183, 0.3)"
    : stock.direction === "down" ? "rgba(252, 165, 165, 0.3)"
    : "var(--line)";
  const changeColor = isUp ? "var(--buy)" : isDown ? "var(--sell)" : "var(--text-muted)";

  return (
    <div style={{
      padding: "8px 10px", borderRadius: 8,
      border: `1px solid ${borderColor}`,
      background: bgColor,
      transition: "background 0.3s, border-color 0.3s",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <strong style={{ fontSize: 12 }}>{stock.symbol}</strong>
        <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
          {stock.category === "gainers" ? "▲" : stock.category === "losers" ? "▼" : "◆"}
        </span>
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, fontVariantNumeric: "tabular-nums", marginTop: 2 }}>
        ${stock.price.toFixed(2)}
      </div>
      <div style={{ fontSize: 11, fontWeight: 600, color: changeColor, fontVariantNumeric: "tabular-nums" }}>
        {isUp ? "+" : ""}{stock.change_pct.toFixed(2)}%
      </div>
      <div style={{ fontSize: 9, color: "var(--text-muted)", marginTop: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {stock.name}
      </div>
    </div>
  );
}
