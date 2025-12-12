# Echo 开发进度

## 当前状态（2025-12-12）

### 已完成

#### M0后端基础设施（90%）

**数据层**：
- ✅ schema.sql：6张表（user/lecture/utterance/summary/export_job/audio_upload）
  - 软删除支持（lectures.deleted_at）
  - 唯一约束（summaries防重复is_latest、audio_uploads去重checksum）
  - 优化索引（utterances按source拉取增量、export_jobs按时间排序）
  - 预置管理员账号（admin/admin123）
- ✅ db.py：psycopg3异步连接池（2-10连接）
- ✅ cli.py：init-db命令初始化数据库

**认证与鉴权**：
- ✅ auth.py：登录/登出/verify_token
  - bcrypt密码验证
  - secrets.token_hex(32)生成256位随机Token
  - 时序攻击防护（假hash防用户名枚举）
- ✅ middleware.py：Bearer Token鉴权中间件
  - 精确路径匹配（避免前缀误放行）
  - 用户信息注入request.state

**讲座管理**：
- ✅ lectures.py：CRUD操作（create/get/list/end）
- ✅ 权限校验：仅创建者可访问/操作自己的讲座（防越权）
- ✅ API路由：
  - `POST /api/auth/login`（登录）
  - `POST /api/auth/logout`（登出）
  - `POST /api/lectures`（创建讲座）
  - `GET /api/lectures`（列表，分页）
  - `GET /api/lectures/{id}`（详情，含权限检查）
  - `POST /api/lectures/{id}/join`（加入，含权限检查）
  - `POST /api/lectures/{id}/end`（结束，含权限检查）

**WebSocket**：
- ✅ ws.py：房间管理（lecture_id→连接集合）+ 心跳机制
  - 握手鉴权（query参数传token）
  - 30s心跳ping/pong
  - 断线自动清理
- ✅ `/ws/lectures/{id}`端点（含鉴权、心跳、占位echo）

**任务队列**：
- ✅ tasks.py：进程内异步队列（asyncio.Queue + 2 workers）
  - submit_task提交异步任务
  - startup启动workers，shutdown停止workers

**文件存储**：
- ✅ storage.py：本地磁盘存储（exports/ uploads/）
  - 路径穿越防护（..和绝对路径检查+resolve验证）
  - 过期文件清理（7天）
  - save_file/get_file_path/delete_file/cleanup_expired_files

**已修复的安全问题**：
1. ✅ 路径穿越漏洞（storage.py双重校验）
2. ✅ 越权访问漏洞（讲座API权限检查）
3. ✅ summaries唯一约束缺失（部分索引WHERE is_latest = TRUE）
4. ✅ 时序攻击漏洞（auth.py假hash恒定时间）
5. ✅ 路径前缀误放行（middleware.py精确匹配）

**待修复的稳定性问题**（不影响基本功能）：
1. ⚠️ DB异常处理缺失（连接异常未捕获，可能污染连接池）
2. ⚠️ WS并发安全（房间set并发修改、广播无超时可能阻塞）
3. ⚠️ shutdown阻塞（队列join可能卡死）

#### M0前端（0%）
- ❌ 登录页面
- ❌ 路由守卫
- ❌ Token持久化

#### 其他
- ✅ 项目脚手架（前后端目录结构、构建配置）
- ✅ 文档（需求、开发文档、开发步骤、Status、features.json）
- ✅ .env.example环境变量模板

### 未完成

#### M1：实时英文字幕（0%）
- ❌ Whisper ASR集成
- ❌ seq生成与广播逻辑
- ❌ 异步落库utterance（含source='realtime'）
- ❌ 前端麦克风采集（16kHz mono PCM）
- ❌ 前端WSS推送音频帧
- ❌ 前端字幕显示（EN）

#### M2：中译与推送（0%）
- ❌ 百度翻译API集成
- ❌ 广播EN+ZH字幕
- ❌ 前端双列字幕显示

#### M3：总结与导出（0%）
- ❌ DeepSeek LLM集成（摘要/要点/QA/提纲）
- ❌ 导出文件生成（md/txt/Word/PDF）
- ❌ 前端总结展示页
- ❌ 前端Markdown预览与下载

#### M4：弱网补传与运维（0%）
- ❌ HTTP音频上传接口
- ❌ 后台重跑ASR+翻译（source='reprocess'）
- ❌ 监控指标（/api/admin/metrics）
- ❌ 错误码规范
- ❌ 部署脚本与文档

#### 部署与环境（0%）
- ❌ Postgres数据库初始化（本地/云）
- ❌ 环境变量配置（DATABASE_URL/API密钥）
- ❌ Nginx配置（静态托管+反代）
- ❌ HTTPS/WSS证书申请与配置
- ❌ Whisper模型下载与推理环境

## 下一步计划

### 立即修复（稳定性问题，预计0.5天）
1. DB异常处理：捕获psycopg异常，确保连接池不被污染
2. WS并发安全：使用asyncio.Lock保护房间修改，广播加超时
3. shutdown优化：先取消workers再join队列，避免卡死

### M0前端（预计1天）
1. 登录页面（用户名/密码表单）
2. Token持久化（localStorage）
3. 路由守卫（未登录拦截）
4. 讲座列表/详情页面（调用后端API）

### M1：实时英文字幕（预计3–4天）
1. Whisper本地推理集成（small/medium模型）
2. WS房间管理（lecture_id→连接集合）
3. seq单调递增生成
4. 前端麦克风采集（16kHz mono PCM，0.5–2s分片）
5. 前端WSS推送音频帧
6. 后端接收→ASR→广播EN字幕
7. 异步落库utterance
8. 前端字幕显示（先只显示EN）

### M2：中译与推送（预计1–2天）
1. 百度翻译API集成（批量/分段/重试）
2. 后端广播EN+ZH字幕
3. 前端双列显示英/中

### M3：总结与导出（预计3–5天）
1. `/api/lectures/{id}/end` 触发总结任务
2. DeepSeek LLM集成（摘要/要点/QA/提纲）
3. `/api/lectures/{id}/summaries` 查询接口
4. `/api/lectures/{id}/exports` 导出（md/txt/Word/PDF）
5. python-docx + Markdown→PDF渲染
6. 前端总结展示页
7. 前端Markdown预览与下载

### M4：弱网补传与运维（预计2–3天）
1. HTTP上传整段音频接口
2. 后台重跑ASR+翻译
3. 监控指标（/metrics）
4. 错误码规范与日志
5. 部署脚本与文档

## 关键风险

1. **Whisper推理性能**：16GB机器能否支持small模型实时推理（目标<1s）？需GPU优先。
2. **百度翻译API限流**：QPS限制，需重试与降级策略。
3. **iOS Safari麦克风权限**：必须HTTPS+用户手势，测试环境需自签证书。
4. **并发处理**：50–100讲座并发，需压测验证。
5. **证书申请流程**：手动申请可能延期，影响正式部署。
6. **任务队列依赖**：Whisper/DeepSeek/导出任务必须用后台队列，避免阻塞WS/HTTP。
7. **弱网重跑策略**：需`audio_upload`表和`utterance.source`字段区分实时/重跑，避免覆盖冲突。

## 总工期估算

MVP首版预计**10–16天**（按串行开发）。并行开发可缩短至**7–10天**。
