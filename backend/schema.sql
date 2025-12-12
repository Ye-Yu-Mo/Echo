-- Echo schema v1
-- 实时讲座字幕系统数据库表结构

-- 用户表（管理员预置，无公开注册）
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(128) NOT NULL,  -- bcrypt hash
    role VARCHAR(16) NOT NULL DEFAULT 'user',  -- user|admin
    token VARCHAR(128) UNIQUE,  -- Bearer token，可选JWT或随机串，唯一约束防授权混淆
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    disabled_at TIMESTAMPTZ  -- 软删除标记
);

CREATE INDEX idx_users_username ON users(username);

-- 讲座会话表
CREATE TABLE IF NOT EXISTS lectures (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    creator_id INT NOT NULL REFERENCES users(id),
    status VARCHAR(16) NOT NULL DEFAULT 'init',  -- init|recording|summarizing|done
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ  -- 软删除标记，避免CASCADE误删所有关联数据
);

CREATE INDEX idx_lectures_status ON lectures(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_lectures_creator ON lectures(creator_id, created_at DESC) WHERE deleted_at IS NULL;

-- 字幕片段表（utterance = 一条字幕）
CREATE TABLE IF NOT EXISTS utterances (
    id SERIAL PRIMARY KEY,
    lecture_id INT NOT NULL REFERENCES lectures(id),  -- 移除CASCADE，避免误删
    seq INT NOT NULL,  -- 单调递增序号，保证顺序
    start_ms BIGINT NOT NULL,  -- 开始时间戳（毫秒）
    end_ms BIGINT NOT NULL,    -- 结束时间戳（毫秒）
    text_en TEXT NOT NULL,
    text_zh TEXT,  -- 可选中译
    source VARCHAR(16) NOT NULL DEFAULT 'realtime',  -- realtime|reprocess，区分实时/重跑
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(lecture_id, seq, source)  -- 同一讲座+seq+source唯一，允许重跑覆盖
);

CREATE INDEX idx_utterances_lecture_seq ON utterances(lecture_id, seq);
CREATE INDEX idx_utterances_lecture_source_seq ON utterances(lecture_id, source, seq);  -- 按source拉取增量字幕

-- 总结表（DeepSeek生成多种类型总结）
CREATE TABLE IF NOT EXISTS summaries (
    id SERIAL PRIMARY KEY,
    lecture_id INT NOT NULL REFERENCES lectures(id),  -- 移除CASCADE
    type VARCHAR(32) NOT NULL,  -- general_summary|outline|qa|key_concepts|key_examples
    content TEXT NOT NULL,  -- JSON或Markdown格式
    model_version VARCHAR(64),  -- 记录模型版本，便于追溯
    is_latest BOOLEAN NOT NULL DEFAULT TRUE,  -- 重跑时旧记录置为false，新记录为true
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_summaries_lecture ON summaries(lecture_id, type, is_latest);
CREATE INDEX idx_summaries_latest ON summaries(lecture_id) WHERE is_latest = TRUE;
-- 唯一约束：同一讲座+类型只能有一条is_latest=true记录
CREATE UNIQUE INDEX idx_summaries_unique_latest ON summaries(lecture_id, type) WHERE is_latest = TRUE;

-- 导出任务表（异步生成md/txt/Word/PDF）
CREATE TABLE IF NOT EXISTS export_jobs (
    id SERIAL PRIMARY KEY,
    lecture_id INT NOT NULL REFERENCES lectures(id),  -- 移除CASCADE
    kind VARCHAR(32) NOT NULL,  -- en|en_zh|summary_md|summary_pdf|en_docx|en_zh_docx|summary_docx
    status VARCHAR(16) NOT NULL DEFAULT 'pending',  -- pending|processing|done|failed
    file_uri TEXT,  -- 生成后文件路径或URL
    error_msg TEXT,  -- 失败原因
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_export_jobs_lecture ON export_jobs(lecture_id, created_at DESC);  -- 查最新导出
CREATE INDEX idx_export_jobs_status ON export_jobs(status, created_at);

-- 音频上传表（弱网补传重跑）
CREATE TABLE IF NOT EXISTS audio_uploads (
    id SERIAL PRIMARY KEY,
    lecture_id INT NOT NULL REFERENCES lectures(id),  -- 移除CASCADE
    file_uri TEXT NOT NULL,  -- 上传后音频文件路径
    checksum VARCHAR(64) NOT NULL,  -- SHA256校验和，去重用
    status VARCHAR(16) NOT NULL DEFAULT 'pending',  -- pending|processing|done|failed
    duration_ms BIGINT,  -- 音频时长（毫秒）
    error_msg TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(lecture_id, checksum)  -- 同一讲座+checksum唯一，避免重复处理
);

CREATE INDEX idx_audio_uploads_lecture ON audio_uploads(lecture_id, status);
CREATE INDEX idx_audio_uploads_status ON audio_uploads(status, created_at);

-- 预置管理员账号（密码: admin123，bcrypt hash）
-- bcrypt hash for 'admin123': $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5sDovXxP0CuKa
INSERT INTO users (username, password_hash, role)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5sDovXxP0CuKa', 'admin')
ON CONFLICT (username) DO NOTHING;
