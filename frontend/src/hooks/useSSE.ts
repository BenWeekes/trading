"use client";

import { useEffect } from "react";

export function useSSE(url: string, onMessage: (eventType: string, payload: unknown) => void) {
  useEffect(() => {
    const source = new EventSource(url);
    const handler = (event: MessageEvent, eventType: string) => {
      try {
        onMessage(eventType, JSON.parse(event.data));
      } catch {
        onMessage(eventType, event.data);
      }
    };

    const eventTypes = [
      "market_event",
      "role_message",
      "role_query",
      "summary_update",
      "recommendation_update",
      "position_update",
      "cost_alert",
      "system",
      "voice_command",
      "price_update",
    ];
    eventTypes.forEach((eventType) => {
      source.addEventListener(eventType, (event) => handler(event as MessageEvent, eventType));
    });
    return () => source.close();
  }, [url, onMessage]);
}
