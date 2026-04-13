"use client";

import { useCallback, useEffect, useState } from "react";

type ToastType = "success" | "error" | "info";

type ToastItem = {
  id: number;
  message: string;
  type: ToastType;
};

let _nextId = 0;
let _addToast: ((message: string, type: ToastType) => void) | null = null;

/** Call from anywhere to show a toast. */
export function toast(message: string, type: ToastType = "info") {
  _addToast?.(message, type);
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const add = useCallback((message: string, type: ToastType) => {
    const id = ++_nextId;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  useEffect(() => {
    _addToast = add;
    return () => { _addToast = null; };
  }, [add]);

  if (toasts.length === 0) return null;

  return (
    <div style={{ position: "fixed", bottom: 20, right: 20, zIndex: 9999, display: "flex", flexDirection: "column", gap: 8 }}>
      {toasts.map((t) => (
        <div
          key={t.id}
          style={{
            padding: "10px 16px",
            borderRadius: 10,
            fontSize: 13,
            fontWeight: 500,
            maxWidth: 380,
            boxShadow: "0 8px 30px rgba(0,0,0,0.4)",
            border: `1px solid ${COLOR[t.type].border}`,
            background: COLOR[t.type].bg,
            color: COLOR[t.type].text,
            animation: "fadeIn 0.2s ease",
          }}
          onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}

const COLOR = {
  success: { bg: "rgba(16, 185, 129, 0.15)", border: "rgba(16, 185, 129, 0.4)", text: "#6ee7b7" },
  error: { bg: "rgba(255, 122, 122, 0.15)", border: "rgba(255, 122, 122, 0.4)", text: "#fca5a5" },
  info: { bg: "rgba(96, 165, 250, 0.15)", border: "rgba(96, 165, 250, 0.4)", text: "#93c5fd" },
};
