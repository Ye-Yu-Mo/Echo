"""
文件存储管理

提供：
- 本地磁盘存储（exports/ uploads/）
- 文件保存/读取/URI生成
- 过期文件清理（7天）

后续可扩展为对象存储（S3/OSS）
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path


# 存储根目录（从环境变量读取）
STORAGE_ROOT = Path(os.environ.get("STORAGE_PATH", "./storage"))
EXPORTS_DIR = STORAGE_ROOT / "exports"
UPLOADS_DIR = STORAGE_ROOT / "uploads"

# 过期天数
EXPIRE_DAYS = int(os.environ.get("STORAGE_EXPIRE_DAYS", "7"))


def init_storage() -> None:
    """初始化存储目录"""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def save_file(file_type: str, filename: str, content: bytes) -> str:
    """
    保存文件到本地存储

    file_type: 'export' 或 'upload'
    filename: 文件名（建议带时间戳或UUID避免冲突）
    content: 文件内容

    返回：文件URI（相对路径，如 exports/xxx.md）
    """
    # 安全检查：禁止路径穿越
    if ".." in filename or filename.startswith("/"):
        raise ValueError(f"Invalid filename: {filename}")

    base_dir = EXPORTS_DIR if file_type == "export" else UPLOADS_DIR
    file_path = base_dir / filename

    # 再次检查resolve后的路径仍在base_dir内
    resolved_path = file_path.resolve()
    if not str(resolved_path).startswith(str(base_dir.resolve())):
        raise ValueError(f"Path traversal attempt detected: {filename}")

    file_path.write_bytes(content)

    # 返回相对URI
    return f"{file_type}s/{filename}"


def get_file_path(file_uri: str) -> Path:
    """
    从URI获取文件绝对路径

    file_uri: 如 exports/xxx.md 或 uploads/yyy.wav
    """
    # 安全检查：禁止路径穿越
    if ".." in file_uri or file_uri.startswith("/"):
        raise ValueError(f"Invalid file_uri: {file_uri}")

    file_path = STORAGE_ROOT / file_uri

    # 再次检查resolve后的路径仍在STORAGE_ROOT内
    resolved_path = file_path.resolve()
    if not str(resolved_path).startswith(str(STORAGE_ROOT.resolve())):
        raise ValueError(f"Path traversal attempt detected: {file_uri}")

    return file_path


def delete_file(file_uri: str) -> bool:
    """
    删除文件

    返回True（成功）或False（文件不存在）
    """
    file_path = get_file_path(file_uri)
    if not file_path.exists():
        return False

    file_path.unlink()
    return True


async def cleanup_expired_files() -> tuple[int, int]:
    """
    清理过期文件（超过EXPIRE_DAYS天的文件）

    返回：(导出文件删除数, 上传文件删除数)
    """
    cutoff_time = datetime.now() - timedelta(days=EXPIRE_DAYS)
    cutoff_timestamp = cutoff_time.timestamp()

    exports_deleted = 0
    uploads_deleted = 0

    # 清理导出文件
    for file_path in EXPORTS_DIR.iterdir():
        if file_path.is_file() and file_path.stat().st_mtime < cutoff_timestamp:
            file_path.unlink()
            exports_deleted += 1

    # 清理上传文件
    for file_path in UPLOADS_DIR.iterdir():
        if file_path.is_file() and file_path.stat().st_mtime < cutoff_timestamp:
            file_path.unlink()
            uploads_deleted += 1

    return exports_deleted, uploads_deleted
