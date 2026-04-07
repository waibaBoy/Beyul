"use client";

import { useEffect, useRef, useState } from "react";
import type { MarketLiveConnectionState, MarketLiveEvent } from "@/lib/api/types";
import { publicEnv } from "@/lib/env";

type UseMarketLiveEventsOptions = {
  marketId: string | null;
  enabled?: boolean;
  onEvent: (event: MarketLiveEvent) => void;
};

export const useMarketLiveEvents = ({ marketId, enabled = true, onEvent }: UseMarketLiveEventsOptions) => {
  const [connectionState, setConnectionState] = useState<MarketLiveConnectionState>("idle");
  const onEventRef = useRef(onEvent);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (!enabled || !marketId) {
      setConnectionState("idle");
      return;
    }

    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let attempt = 0;
    let disposed = false;

    const connect = () => {
      if (disposed) {
        return;
      }

      setConnectionState(attempt === 0 ? "connecting" : "reconnecting");
      socket = new WebSocket(`${publicEnv.wsBaseUrl}/ws/markets/${marketId}`);

      socket.onopen = () => {
        attempt = 0;
        setConnectionState("connected");
      };

      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data) as MarketLiveEvent;
          onEventRef.current(event);
        } catch {
          // Ignore malformed frames so one bad payload does not kill the live session.
        }
      };

      socket.onerror = () => {
        socket?.close();
      };

      socket.onclose = () => {
        if (disposed) {
          return;
        }
        setConnectionState("reconnecting");
        const backoffMs = Math.min(1000 * 2 ** attempt, 5000);
        attempt += 1;
        reconnectTimer = window.setTimeout(connect, backoffMs);
      };
    };

    connect();

    return () => {
      disposed = true;
      setConnectionState("disconnected");
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      socket?.close();
    };
  }, [enabled, marketId]);

  return { connectionState };
};
