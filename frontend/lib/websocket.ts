// WebSocket hooks for the agent stream and the sovereignty network monitor.

import { useCallback, useEffect, useRef, useState } from "react";
import { WS_URL } from "@/lib/config";
import { isTerminal, type AgentEvent, type TraceEvent } from "@/lib/events";

export type { AgentEvent, TraceEvent } from "@/lib/events";

const RECONNECT_MS = 3000;

/**
 * Opens `url`, reconnecting on close until the owning component unmounts.
 * Handlers are read through a ref so callers can pass inline functions.
 */
function useReconnectingSocket(
  url: string,
  handlers: {
    onOpen?: () => void;
    onClose?: () => void;
    onMessage: (data: unknown) => void;
  },
) {
  const socketRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef(handlers);

  useEffect(() => {
    handlersRef.current = handlers;
  });

  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      const ws = new WebSocket(url);
      socketRef.current = ws;
      ws.onopen = () => handlersRef.current.onOpen?.();
      ws.onmessage = (msg: MessageEvent) => {
        try {
          handlersRef.current.onMessage(JSON.parse(msg.data));
        } catch {
          console.error("Unparseable socket message", msg.data);
        }
      };
      ws.onclose = () => {
        if (disposed) return;
        handlersRef.current.onClose?.();
        timer = setTimeout(connect, RECONNECT_MS);
      };
    };

    connect();
    return () => {
      disposed = true;
      clearTimeout(timer);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [url]);

  return socketRef;
}

export function useAgentWebSocket(baseUrl = WS_URL) {
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [startedAt, setStartedAt] = useState<number | null>(null);

  const nextId = useRef(0);
  const started = useRef(false);
  const tokenBuffer = useRef<{ text: string; iteration: unknown } | null>(null);
  const frame = useRef<number | null>(null);

  // Tokens arrive far faster than the screen refreshes; fold them in once per frame.
  const flushTokens = useCallback(() => {
    frame.current = null;
    const buffered = tokenBuffer.current;
    tokenBuffer.current = null;
    if (!buffered) return;
    setEvents((prev) => {
      const last = prev[prev.length - 1];
      if (last?.type === "streaming_thought") {
        const text = String(last.data.text ?? "") + buffered.text;
        return [...prev.slice(0, -1), { ...last, data: { ...last.data, text } }];
      }
      return [
        ...prev,
        {
          id: nextId.current++,
          at: Date.now(),
          type: "streaming_thought",
          data: { text: buffered.text, iteration: buffered.iteration },
        },
      ];
    });
  }, []);

  const handleMessage = (raw: unknown) => {
    const event = raw as AgentEvent;

    if (event.type === "token_chunk") {
      const token = String(event.data.token ?? "");
      tokenBuffer.current = {
        text: (tokenBuffer.current?.text ?? "") + token,
        iteration: event.data.iteration,
      };
      frame.current ??= requestAnimationFrame(flushTokens);
      return;
    }

    // Keep ordering: any buffered tokens belong before this event.
    if (frame.current !== null) {
      cancelAnimationFrame(frame.current);
      flushTokens();
    }

    if (event.type === "agent_start") started.current = true;
    const stamped: TraceEvent = { ...event, id: nextId.current++, at: Date.now() };
    setEvents((prev) => [...prev, stamped]);
    if (isTerminal(event, started.current)) setIsRunning(false);
  };

  const socket = useReconnectingSocket(`${baseUrl}/ws/agent`, {
    onOpen: () => setConnected(true),
    onClose: () => {
      setConnected(false);
      setIsRunning(false);
    },
    onMessage: handleMessage,
  });

  useEffect(
    () => () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current);
    },
    [],
  );

  const sendTask = useCallback(
    (userInput: string, filePath?: string) => {
      const ws = socket.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return false;
      started.current = false;
      tokenBuffer.current = null;
      setEvents([]);
      setIsRunning(true);
      setStartedAt(Date.now());
      ws.send(JSON.stringify({ user_input: userInput, file_path: filePath ?? null }));
      return true;
    },
    [socket],
  );

  const reset = useCallback(() => {
    if (isRunning) return;
    setEvents([]);
    setStartedAt(null);
  }, [isRunning]);

  return { events, connected, isRunning, startedAt, sendTask, reset };
}

// ── Network monitor ─────────────────────────────────────────────────────────

export interface NetworkEntry {
  timestamp: string;
  method: string;
  host: string;
  port: number;
  url: string;
  is_local: boolean;
  blocked: boolean;
}

export interface NetworkStatus {
  entries: NetworkEntry[];
  total: number;
  external_blocked: number;
  sovereign: boolean;
  connected: boolean;
}

export function useNetworkMonitor(baseUrl = WS_URL) {
  const [status, setStatus] = useState<NetworkStatus>({
    entries: [],
    total: 0,
    external_blocked: 0,
    sovereign: true,
    connected: false,
  });

  useReconnectingSocket(`${baseUrl}/ws/network`, {
    onOpen: () => setStatus((s) => ({ ...s, connected: true })),
    onClose: () => setStatus((s) => ({ ...s, connected: false })),
    onMessage: (data) =>
      setStatus({ ...(data as Omit<NetworkStatus, "connected">), connected: true }),
  });

  return status;
}
