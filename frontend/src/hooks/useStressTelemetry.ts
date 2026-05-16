import { useEffect, useRef } from 'react';
import { useStressStore } from '../store/stressStore';

export const useStressTelemetry = (scanId: number | string | undefined) => {
  const addTelemetryPoint = useStressStore((state) => state.addTelemetryPoint);
  const setScanning = useStressStore((state) => state.setScanning);
  const setWsStatus = useStressStore((state) => state.setWsStatus);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!scanId) return;

    let reconnectTimeout: ReturnType<typeof setTimeout>;
    let isMounted = true;
    let reconnectAttempts = 0;

    const connect = () => {
      if (!isMounted) return;
      
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const socketUrl = `${protocol}//${window.location.host}/ws/stress/${scanId}/`;

      console.log(`Connecting to telemetry WebSocket (Attempt ${reconnectAttempts + 1}): ${socketUrl}`);
      setWsStatus('connecting');
      
      const socket = new WebSocket(socketUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        if (!isMounted) return;
        console.log('Connected to Stress Telemetry');
        setWsStatus('connected');
        reconnectAttempts = 0;
      };

      socket.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'telemetry_update') {
            addTelemetryPoint(message.data);
          } else if (message.type === 'scan_status') {
            setScanning(message.status === 'running');
          }
        } catch (err) {
          console.error("Failed to parse WebSocket message", err);
        }
      };

      socket.onclose = (event) => {
        if (!isMounted) return;
        console.log(`Disconnected from Stress Telemetry: ${event.code}`);
        setWsStatus('disconnected');
        
        // Attempt reconnection if not closed cleanly
        if (event.code !== 1000 && event.code !== 1001) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
          reconnectAttempts++;
          reconnectTimeout = setTimeout(connect, delay);
        }
      };

      socket.onerror = (error) => {
        if (!isMounted) return;
        console.error('WebSocket Error:', error);
        setWsStatus('error');
      };
    };

    connect();

    return () => {
      isMounted = false;
      if (socketRef.current) {
        socketRef.current.close(1000);
      }
      clearTimeout(reconnectTimeout);
    };
  }, [scanId, addTelemetryPoint, setScanning, setWsStatus]);

  return socketRef.current;
};
