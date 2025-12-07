# Echo Backend (FastAPI + uv)

## 运行方式（uv）
1. 安装 uv（已装可跳过）：`brew install uv`。
2. 创建虚拟环境并同步依赖（需要 Python 3.11+ 可用）：
   - `cd backend`
   - `uv venv -p 3.11`  # 如本机无 3.11，请先装或改为可用版本
   - `source .venv/bin/activate`
   - `uv sync`  # 读取 pyproject，安装依赖
3. 开发启动（热重载）：
   - `uv run uvicorn echo.main:app --reload --host 0.0.0.0 --port 8000`

## 目录结构
- `pyproject.toml`：uv 管理的依赖声明。
- `src/echo/main.py`：FastAPI 入口，含健康检查与示例 WebSocket。

## 环境变量（占位）
- `DATABASE_URL`：Postgres 连接串。
- `BAIDU_APP_ID` / `BAIDU_APP_KEY`：翻译 API。
- `DEEPSEEK_API_KEY`：LLM。
- `WHISPER_MODEL_PATH`：本地模型路径（可选）。

## 待办
- 接入真实鉴权、Postgres 连接池、Whisper/翻译/LLM 调用与队列。
