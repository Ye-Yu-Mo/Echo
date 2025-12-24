/**
 * WebSocket 客户端
 * - 自动重连（指数退避）
 * - 心跳响应
 * - 字幕消息处理（英文+中文补丁）
 */

export interface SubtitleMessage {
  type: 'subtitle';
  lecture_id: number;
  seq: number;
  start_ms: number;
  end_ms: number;
  text_en: string;
}

export interface SubtitleZhMessage {
  type: 'subtitle_zh';
  lecture_id: number;
  seq: number;
  text_zh: string;
}

export interface ErrorMessage {
  type: 'error';
  code: number;
  message: string;
}

export interface InfoMessage {
  type: 'info';
  message: string;
}

export type WSMessage = SubtitleMessage | SubtitleZhMessage | ErrorMessage | InfoMessage | { type: 'ping' };

export type OnSubtitleCallback = (subtitle: SubtitleMessage) => void;
export type OnSubtitleZhCallback = (patch: SubtitleZhMessage) => void;
export type OnErrorCallback = (error: string) => void;
export type OnInfoCallback = (info: string) => void;

export class LectureWebSocket {
  private ws: WebSocket | null = null;
  private reconnectTimeout: number | null = null;
  private reconnectDelay = 1000; // 初始重连延迟
  private maxReconnectDelay = 30000; // 最大重连延迟
  private isManualClose = false;

  constructor(
    private lectureId: number,
    private token: string,
    private onSubtitle: OnSubtitleCallback,
    private onSubtitleZh: OnSubtitleZhCallback,
    private onError: OnErrorCallback,
    private onInfo?: OnInfoCallback
  ) {}

  connect(): void {
    this.isManualClose = false;

    // 获取 WebSocket URL（开发环境用 ws://，生产环境用 wss://）
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_HOST || 'localhost:8000';
    const url = `${protocol}//${host}/ws/lectures/${this.lectureId}?token=${this.token}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectDelay = 1000; // 重置重连延迟
    };

    this.ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);

        if (msg.type === 'subtitle') {
          this.onSubtitle(msg);
        } else if (msg.type === 'subtitle_zh') {
          this.onSubtitleZh(msg);
        } else if (msg.type === 'error') {
          this.onError(`${msg.message} (code: ${msg.code})`);
        } else if (msg.type === 'info' && this.onInfo) {
          this.onInfo(msg.message);
        } else if (msg.type === 'ping') {
          // 响应心跳
          this.ws?.send('pong');
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.onError('WebSocket connection error');
    };

    this.ws.onclose = () => {
      console.log('WebSocket closed');

      // 自动重连（除非手动关闭）
      if (!this.isManualClose) {
        this.scheduleReconnect();
      }
    };
  }

  sendAudioFrame(pcm: ArrayBuffer): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(pcm);
    }
  }

  close(): void {
    this.isManualClose = true;

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    this.reconnectTimeout = window.setTimeout(() => {
      console.log(`Reconnecting in ${this.reconnectDelay}ms...`);
      this.connect();
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
    }, this.reconnectDelay);
  }
}
