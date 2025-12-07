# Echo Frontend (Vite + Preact)

## 使用方式
1. `cd frontend`
2. 安装依赖（需网络）：`npm install` 或 `pnpm install`。
3. 开发：`npm run dev`（默认 http://localhost:5173）。生产请走 Nginx+HTTPS，满足 iOS 开麦要求。

可选环境变量：
- `VITE_WS_BASE`：WS 基址，默认 `ws://localhost:8000`。如果后端不在同一端口，必须设置，比如 `VITE_WS_BASE=ws://127.0.0.1:8000`。

## 功能占位
- 基于 Preact 的骨架；按钮可连占位 WebSocket `/ws/lectures/demo`。
- 后续需在用户手势下调用 `getUserMedia` 采集 16kHz mono，分片推送 WSS。
- Markdown 预览、登录、导出等待接入后端 API。
