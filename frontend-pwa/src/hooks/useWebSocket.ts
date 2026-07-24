import { useEffect, useRef, useCallback, useState } from "react";

type WsEvent = {
  event_type: string;
  job_id: string;
  version: number;
  timestamp?: string;
  payload: Record<string, unknown>;
};

export default function useWebSocket(url: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<WsEvent | null>(null);
  const listenersRef = useRef<Map<string, Set<(e: WsEvent) => void>>>(new Map());

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log("[ws] Connected to Inti");
    };

    ws.onmessage = (msg) => {
      try {
        const event: WsEvent = JSON.parse(msg.data);
        setLastEvent(event);

        const handlers = listenersRef.current.get(event.event_type);
        if (handlers) {
          for (const fn of handlers) fn(event);
        }

        const allHandlers = listenersRef.current.get("*");
        if (allHandlers) {
          for (const fn of allHandlers) fn(event);
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      reconnectRef.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const subscribe = useCallback(
    (eventType: string, callback: (e: WsEvent) => void) => {
      const handlers = listenersRef.current.get(eventType) ?? new Set();
      handlers.add(callback);
      listenersRef.current.set(eventType, handlers);
      return () => {
        handlers.delete(callback);
        if (handlers.size === 0) listenersRef.current.delete(eventType);
      };
    },
    []
  );

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { connected, lastEvent, subscribe, send };
}
