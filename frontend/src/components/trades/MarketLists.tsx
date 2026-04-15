"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Position } from "@/lib/types";

type PulseStock = {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  direction: "up" | "down" | "same";
};

type Tab = "open" | "all" | "gainers" | "losers" | "active";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

type Props = {
  positions: Position[];
  activeSymbol?: string | null;
  onSell: (tradeId: string, symbol: string, shares: number) => void;
  onSelectSymbol?: (symbol: string) => void;
};

export function MarketLists({ positions, activeSymbol, onSell, onSelectSymbol }: Props) {
  const [tab, setTab] = useState<Tab>("open");
  const [pulseStocks, setPulseStocks] = useState<PulseStock[]>([]);
  const [tickerPrices, setTickerPrices] = useState<Record<string, PulseStock>>({});
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchPulse = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/market-pulse`);
      const d = await r.json();
      setPulseStocks(d.stocks || []);
    } catch { /* ignore */ }
    try {
      const r = await fetch(`${API_BASE}/ticker`);
      const d = await r.json();
      setTickerPrices(d.prices || {});
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    fetchPulse();
    intervalRef.current = setInterval(fetchPulse, 3000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchPulse]);

  const gainers = pulseStocks.filter((s) => s.change_pct > 0).sort((a, b) => b.change_pct - a.change_pct);
  const losers = pulseStocks.filter((s) => s.change_pct < 0).sort((a, b) => a.change_pct - b.change_pct);
  const active = [...pulseStocks].sort((a, b) => Math.abs(b.change_pct) - Math.abs(a.change_pct));
  // "All" combines everything: pulse stocks + ticker prices, deduped, sorted A-Z
  const allMap = new Map<string, PulseStock>();
  for (const s of pulseStocks) allMap.set(s.symbol, s);
  for (const [sym, data] of Object.entries(tickerPrices)) {
    if (!allMap.has(sym)) allMap.set(sym, { symbol: sym, name: "", price: 0, change: 0, change_pct: 0, direction: "same", ...(data as object) } as PulseStock);
  }
  // Also include position symbols
  for (const pos of positions) {
    if (pos.symbol && !allMap.has(pos.symbol)) {
      allMap.set(pos.symbol, { symbol: pos.symbol, name: "", price: Number(pos.current_price ?? 0), change: 0, change_pct: 0, direction: "same" });
    }
  }
  const allSymbols = [...allMap.values()].sort((a, b) => a.symbol.localeCompare(b.symbol));

  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--line)" }}>
        {([["open", `Open (${positions.length})`], ["all", `All (${allSymbols.length})`], ["gainers", "▲"], ["losers", "▼"], ["active", "◆"]] as [Tab, string][]).map(([t, label]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              flex: 1, padding: "8px 4px", background: "transparent", border: "none",
              borderBottom: tab === t ? "2px solid var(--accent)" : "2px solid transparent",
              color: tab === t ? "var(--text)" : "var(--text-muted)",
              fontSize: 11, fontWeight: 600, cursor: "pointer",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* List */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {tab === "open" && (
          positions.length === 0 ? (
            <div style={{ padding: 20, color: "var(--text-muted)", fontSize: 13, textAlign: "center" }}>No open positions.</div>
          ) : (
            positions.map((pos) => (
              <PositionRow key={pos.id} position={pos} active={pos.symbol === activeSymbol} onSell={onSell} onSelect={onSelectSymbol} />
            ))
          )
        )}
        {tab === "all" && (
          allSymbols.length === 0 ? (
            <div style={{ padding: 20, color: "var(--text-muted)", fontSize: 13, textAlign: "center" }}>Prices loading...</div>
          ) : (
            allSymbols.map((s) => <StockRow key={s.symbol} stock={s} active={s.symbol === activeSymbol} onSelect={onSelectSymbol} />)
          )
        )}
        {tab === "gainers" && gainers.map((s) => <StockRow key={s.symbol} stock={s} active={s.symbol === activeSymbol} onSelect={onSelectSymbol} />)}
        {tab === "losers" && losers.map((s) => <StockRow key={s.symbol} stock={s} active={s.symbol === activeSymbol} onSelect={onSelectSymbol} />)}
        {tab === "active" && active.map((s) => <StockRow key={s.symbol} stock={s} active={s.symbol === activeSymbol} onSelect={onSelectSymbol} />)}
      </div>
    </div>
  );
}

function StockRow({ stock, active, onSelect }: { stock: PulseStock & { symbol: string }; active: boolean; onSelect?: (s: string) => void }) {
  const isUp = stock.change_pct > 0;
  const isDown = stock.change_pct < 0;
  const color = isUp ? "var(--buy)" : isDown ? "var(--sell)" : "var(--text-muted)";
  const bg = stock.direction === "up" ? "rgba(110,231,183,0.06)" : stock.direction === "down" ? "rgba(252,165,165,0.06)" : "transparent";

  return (
    <button
      onClick={() => onSelect?.(stock.symbol)}
      style={{
        display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%",
        padding: "6px 12px", background: active ? "var(--accent-glow)" : bg,
        border: "none", borderBottom: "1px solid var(--line)", color: "inherit", cursor: "pointer",
        transition: "background 0.2s",
      }}
    >
      <div style={{ textAlign: "left" }}>
        <strong style={{ fontSize: 12 }}>{stock.symbol}</strong>
        <div style={{ fontSize: 9, color: "var(--text-muted)" }}>{stock.name}</div>
      </div>
      <div style={{ textAlign: "right" }}>
        <div style={{ fontSize: 12, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>${stock.price.toFixed(2)}</div>
        <div style={{ fontSize: 10, fontWeight: 600, color, fontVariantNumeric: "tabular-nums" }}>
          {isUp ? "+" : ""}{stock.change_pct.toFixed(2)}%
        </div>
      </div>
    </button>
  );
}

function PositionRow({ position, active, onSell, onSelect }: {
  position: Position; active: boolean;
  onSell: (id: string, s: string, n: number) => void;
  onSelect?: (s: string) => void;
}) {
  const [showSell, setShowSell] = useState(false);
  const [sellShares, setSellShares] = useState(position.shares ?? 0);
  const pnl = position.unrealized_pnl ?? 0;
  const total = position.shares ?? 0;
  const dir = (position.direction ?? "BUY").toUpperCase();
  const isShort = dir === "SHORT";
  const exitLabel = isShort ? "Cover" : "Sell";

  return (
    <div style={{
      padding: "8px 12px", borderBottom: "1px solid var(--line)",
      background: active ? "var(--accent-glow)" : "transparent", cursor: "pointer",
    }} onClick={() => onSelect?.(position.symbol)}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <span style={{ fontSize: 10, fontWeight: 600, color: isShort ? "var(--warn)" : "var(--buy)", marginRight: 4 }}>{dir}</span>
          <strong style={{ fontSize: 12 }}>{position.symbol}</strong>
          <span style={{ fontSize: 10, color: "var(--text-muted)", marginLeft: 6 }}>{total} sh</span>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 12, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>${Number(position.current_price ?? 0).toFixed(2)}</div>
          <div style={{ fontSize: 10, fontWeight: 600, color: pnl >= 0 ? "var(--buy)" : "var(--sell)", fontVariantNumeric: "tabular-nums" }}>
            {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
          </div>
        </div>
      </div>
      {!showSell ? (
        <button onClick={(e) => { e.stopPropagation(); setShowSell(true); }} style={{ marginTop: 4, fontSize: 10, color: "var(--sell)", background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}>{exitLabel}...</button>
      ) : (
        <div onClick={(e) => e.stopPropagation()} style={{ marginTop: 6, display: "flex", gap: 6, alignItems: "center" }}>
          <input type="number" value={sellShares} min={1} max={total} onChange={(e) => setSellShares(Math.min(Number(e.target.value), total))}
            style={{ width: 50, padding: "3px 6px", borderRadius: 6, border: "1px solid var(--line)", background: "var(--bg)", color: "var(--text)", fontSize: 11, textAlign: "center" }} />
          <button className="btn btn-danger" style={{ fontSize: 10, padding: "3px 8px" }} onClick={() => { onSell(position.id, position.symbol, sellShares); setShowSell(false); }}>{exitLabel}</button>
          <button style={{ fontSize: 10, color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer" }} onClick={() => setShowSell(false)}>x</button>
        </div>
      )}
    </div>
  );
}
