"""
异步任务队列（进程内实现）

支持：
- ASR/翻译/落库任务（M1/M2）
- DeepSeek总结任务（M3）
- 导出任务（M3）
- 弱网重跑任务（M4）

后续可替换为Celery/RQ
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


# 全局任务队列
_queue: asyncio.Queue[tuple[Callable[..., Awaitable[Any]], tuple[Any, ...], dict[str, Any]]] | None = None

# worker任务列表
_workers: list[asyncio.Task] | None = None


async def _worker(worker_id: int) -> None:
    """
    Worker任务：循环处理队列

    从队列中取出任务并执行
    """
    global _queue
    if _queue is None:
        return

    logger.info(f"Worker {worker_id} started")

    while True:
        try:
            # 从队列取任务（阻塞等待）
            func, args, kwargs = await _queue.get()

            # 执行任务
            try:
                await func(*args, **kwargs)
            except Exception as exc:
                logger.error(f"Task failed in worker {worker_id}: {exc}", exc_info=True)
            finally:
                _queue.task_done()

        except asyncio.CancelledError:
            logger.info(f"Worker {worker_id} cancelled")
            break
        except Exception as exc:
            logger.error(f"Worker {worker_id} error: {exc}", exc_info=True)


def start_workers(num_workers: int = 2) -> None:
    """启动worker任务"""
    global _queue, _workers

    if _queue is not None:
        return  # 已启动

    _queue = asyncio.Queue()
    _workers = []

    for i in range(num_workers):
        task = asyncio.create_task(_worker(i))
        _workers.append(task)

    logger.info(f"Started {num_workers} workers")


async def stop_workers() -> None:
    """停止worker任务"""
    global _queue, _workers

    if _workers is None:
        return

    # 等待队列中的任务完成
    if _queue is not None:
        await _queue.join()

    # 取消所有worker
    for task in _workers:
        task.cancel()

    # 等待worker退出
    await asyncio.gather(*_workers, return_exceptions=True)

    _queue = None
    _workers = None

    logger.info("Workers stopped")


def submit_task(func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> None:
    """
    提交异步任务到队列

    示例：
        submit_task(process_audio, lecture_id=1, audio_bytes=b"...")
    """
    global _queue

    if _queue is None:
        raise RuntimeError("Workers not started. Call start_workers() first.")

    _queue.put_nowait((func, args, kwargs))
