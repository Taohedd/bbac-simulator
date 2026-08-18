import { useEffect, useRef, useState } from 'react';
import { useStore } from '../store/useStore';
import { RiskEvent } from '../types';

// Built from window.location so this works through the Vite dev server proxy
// configured in vite.config.ts ('/ws' -> ws://localhost:8000, ws: true),
// instead of hardcoding the backend host/port. Matches the relative-path
// approach used in api/client.ts.
const getWebSocketUrl = (): string => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/stream`;
};

const RECONNECT_DELAY_MS = 3000;

// Minimal runtime check — confirms the parsed message actually has the
// shape of a RiskEvent before it's cast and pushed into the store, so a
// malformed backend payload fails loudly here instead of silently
// corrupting state somewhere downstream.
function isRiskEvent(data: unknown): data is RiskEvent {
  if (typeof data !== 'object' || data === null) return false;
  const d = data as Record<string, unknown>;
  return (
    d.type === 'risk_event' &&
    typeof d.log_id === 'string' &&
    typeof d.user_id === 'string' &&
    typeof d.risk_score === 'number' &&
    typeof d.decision === 'string'
  );
}

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  const addLiveEvent = useStore((state) => state.addLiveEvent);

  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket(getWebSocketUrl());
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          console.log('WebSocket connected to BBAC stream');
        };

        ws.onmessage = (event: MessageEvent) => {
          try {
            const data: unknown = JSON.parse(event.data);
            if (isRiskEvent(data)) {
              addLiveEvent(data);
            } else {
              console.warn('Received malformed WebSocket message — ignoring:', data);
            }
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          console.log(`WebSocket disconnected. Reconnecting in ${RECONNECT_DELAY_MS}ms...`);
          reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
        };

        ws.onerror = (error: Event) => {
          console.error('WebSocket encountered an error:', error);
          ws.close(); // Force close to trigger onclose and reconnect logic
        };
      } catch (error) {
        console.error('Failed to establish WebSocket connection:', error);
        reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        // Remove onclose listener to prevent reconnect loop on intentional unmount
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [addLiveEvent]);

  return { isConnected };
};