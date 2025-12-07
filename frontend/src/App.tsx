import { useEffect, useRef, useState } from 'preact/hooks';

type WsStatus = 'idle' | 'connecting' | 'open' | 'closed' | 'error';

export function App() {
  const [wsStatus, setWsStatus] = useState<WsStatus>('idle');
  const [log, setLog] = useState<string[]>([]);
  const socketRef = useRef<WebSocket | null>(null);

  const wsBase = (import.meta.env.VITE_WS_BASE as string | undefined)?.replace(/\/$/, '') || 'ws://localhost:8000';

  useEffect(() => {
    return () => {
      socketRef.current?.close();
    };
  }, []);

  const connect = () => {
    const url = `${wsBase}/ws/lectures/demo`;
    const ws = new WebSocket(url);
    socketRef.current = ws;
    setWsStatus('connecting');

    ws.onopen = () => setWsStatus('open');
    ws.onclose = () => setWsStatus('closed');
    ws.onerror = () => setWsStatus('error');
    ws.onmessage = (ev) => {
      setLog((prev) => [ev.data, ...prev].slice(0, 5));
    };
  };

  return (
    <div class="page">
      <header>
        <h1>Echo MVP</h1>
        <p>Preact + FastAPI skeleton。iOS 需 HTTPS 与用户手势开麦。</p>
      </header>

      <section class="card">
        <h2>WebSocket 连通性</h2>
        <p class="muted">当前状态：{wsStatus}（ws 基址：{wsBase}）</p>
        <div class="actions">
          <button onClick={connect} disabled={wsStatus === 'open' || wsStatus === 'connecting'}>
            连接占位 WS
          </button>
        </div>
        <ul class="log">
          {log.map((line, idx) => (
            <li key={idx}>{line}</li>
          ))}
        </ul>
      </section>

      <section class="card">
        <h2>麦克风权限提示</h2>
        <p class="muted">
          真实链路需在用户手势下调用 getUserMedia，采集 16kHz mono PCM，0.5–2s 分片后走 WSS。
        </p>
      </section>
    </div>
  );
}
