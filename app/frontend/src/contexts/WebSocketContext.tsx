/**
 * WebSocket Context for Real-time Data Streaming
 * 
 * Provides WebSocket connection management and data streaming
 * for all visualization components.
 */

'use client';

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

interface WebSocketContextValue {
  /** Whether WebSocket is connected */
  connected: boolean;
  /** Whether WebSocket is connecting */
  connecting: boolean;
  /** Last error, if any */
  error: Error | null;
  /** Subscribe to a data stream */
  subscribe: (channel: string, callback: (data: unknown) => void) => () => void;
  /** Send a message to the server */
  send: (channel: string, data: unknown) => void;
  /** Get current connection status */
  getStatus: () => 'connected' | 'connecting' | 'disconnected' | 'error';
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

interface WebSocketProviderProps {
  children: React.ReactNode;
  /** WebSocket server URL */
  url?: string;
  /** Auto-reconnect enabled */
  autoReconnect?: boolean;
  /** Reconnect delay in milliseconds */
  reconnectDelay?: number;
}

export function WebSocketProvider({
  children,
  url = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8100',
  autoReconnect = true,
  reconnectDelay = 3000,
}: WebSocketProviderProps) {
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const socketRef = useRef<Socket | null>(null);
  const subscribersRef = useRef<Map<string, Set<(data: unknown) => void>>>(new Map());
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (socketRef.current?.connected) {
      return;
    }

    setConnecting(true);
    setError(null);

    try {
      const socket = io(url, {
        transports: ['websocket'],
        reconnection: autoReconnect,
        reconnectionDelay: reconnectDelay,
        reconnectionAttempts: 10,
      });

      socket.on('connect', () => {
        console.log('[WebSocket] Connected');
        setConnected(true);
        setConnecting(false);
        setError(null);
      });

      socket.on('disconnect', (reason) => {
        console.log('[WebSocket] Disconnected:', reason);
        setConnected(false);
        setConnecting(false);

        if (autoReconnect && reason !== 'io client disconnect') {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        }
      });

      socket.on('connect_error', (err) => {
        console.error('[WebSocket] Connection error:', err);
        setError(err);
        setConnecting(false);
        setConnected(false);
      });

      // Handle incoming data for all subscribed channels
      socket.onAny((event, data) => {
        const callbacks = subscribersRef.current.get(event);
        if (callbacks) {
          callbacks.forEach((callback) => {
            try {
              callback(data);
            } catch (err) {
              console.error(`[WebSocket] Error in subscriber callback for ${event}:`, err);
            }
          });
        }
      });

      socketRef.current = socket;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create WebSocket connection');
      setError(error);
      setConnecting(false);
      setConnected(false);
    }
  }, [url, autoReconnect, reconnectDelay]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [connect]);

  const subscribe = useCallback((channel: string, callback: (data: unknown) => void) => {
    if (!subscribersRef.current.has(channel)) {
      subscribersRef.current.set(channel, new Set());
    }
    subscribersRef.current.get(channel)!.add(callback);

    // Emit subscribe event to server if connected
    if (socketRef.current?.connected) {
      socketRef.current.emit('subscribe', channel);
    }

    // Return unsubscribe function
    return () => {
      const callbacks = subscribersRef.current.get(channel);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          subscribersRef.current.delete(channel);
          // Emit unsubscribe event to server if connected
          if (socketRef.current?.connected) {
            socketRef.current.emit('unsubscribe', channel);
          }
        }
      }
    };
  }, []);

  const send = useCallback((channel: string, data: unknown) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(channel, data);
    } else {
      console.warn(`[WebSocket] Cannot send to ${channel}: not connected`);
    }
  }, []);

  const getStatus = useCallback((): 'connected' | 'connecting' | 'disconnected' | 'error' => {
    if (error) return 'error';
    if (connected) return 'connected';
    if (connecting) return 'connecting';
    return 'disconnected';
  }, [connected, connecting, error]);

  const value: WebSocketContextValue = {
    connected,
    connecting,
    error,
    subscribe,
    send,
    getStatus,
  };

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider');
  }
  return context;
}
