import { useEffect, useRef } from 'react';
import { useStressStore } from '../store/stressStore';

export const useStressTelemetry = (scanId: number | string | undefined) => {
  const addTelemetryPoint = useStressStore((state) => state.addTelemetryPoint);
  const setScanning = useStressStore((state) => state.setScanning);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!scanId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // In reNgine, the port might be 8000 or handled by proxy. 
    // Usually, ws is on the same port as the app.
    const socketUrl = `${protocol}//${window.location.host}/ws/stress/${scanId}/`;

    console.log(`Connecting to telemetry WebSocket: ${socketUrl}`);
    const socket = new WebSocket(socketUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log('Connected to Stress Telemetry');
    };

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'telemetry_update') {
        addTelemetryPoint(message.data);
      } else if (message.type === 'scan_status') {
        setScanning(message.status === 'running');
      }
    };

    socket.onclose = () => {
      console.log('Disconnected from Stress Telemetry');
    };

    socket.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };

    return () => {
      socket.close();
    };
  }, [scanId, addTelemetryPoint, setScanning]);

  return socketRef.current;
};
