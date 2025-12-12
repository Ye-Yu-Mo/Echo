"""
Whisper ASR 模块
- 单例加载 Whisper small 模型（GPU/FP16 优先，CPU 降级）
- 简单 VAD（能量阈值过滤静音）
- 推理超时与错误处理
"""
from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np

logger = logging.getLogger(__name__)

# 全局单例
_model = None
_backend = None
_executor = ThreadPoolExecutor(max_workers=1)

# 配置
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
ENERGY_THRESHOLD = float(os.getenv("WHISPER_ENERGY_THRESHOLD", "30.0"))
ASR_TIMEOUT = float(os.getenv("WHISPER_TIMEOUT", "8.0"))

try:
    from faster_whisper import WhisperModel
    _HAS_FASTER = True
except ImportError:
    _HAS_FASTER = False
    logger.warning("faster-whisper not available, fallback to openai-whisper")

try:
    import whisper as openai_whisper
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

try:
    import torch
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False


def _detect_device() -> tuple[str, str]:
    """检测可用设备和计算类型"""
    if not _HAS_TORCH:
        return "cpu", "int8"

    import torch
    if torch.cuda.is_available():
        return "cuda", "float16"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps", "float16"
    return "cpu", "int8"


def _load_model() -> None:
    """加载 Whisper 模型（启动时调用）"""
    global _model, _backend

    device, compute_type = _detect_device()
    logger.info(f"Loading Whisper {WHISPER_MODEL} on {device} with {compute_type}")

    if _HAS_FASTER:
        _model = WhisperModel(WHISPER_MODEL, device=device, compute_type=compute_type)
        _backend = "faster"
        logger.info("Using faster-whisper backend")
    elif _HAS_OPENAI:
        _model = openai_whisper.load_model(WHISPER_MODEL, device=device)
        _backend = "openai"
        logger.info("Using openai-whisper backend")
    else:
        logger.error("No Whisper backend available")


def _compute_energy(wave: np.ndarray) -> float:
    """计算音频帧的能量（RMS）"""
    if wave.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(wave.astype(np.float32)))))


def _do_transcribe_sync(audio: np.ndarray) -> str:
    """同步推理（在线程池中执行）"""
    if _backend == "faster":
        segments, _ = _model.transcribe(audio, language="en", beam_size=5)
        return " ".join(seg.text.strip() for seg in segments).strip()
    elif _backend == "openai":
        result = _model.transcribe(audio, language="en")
        return str(result.get("text", "")).strip()
    return ""


async def transcribe(pcm_bytes: bytes) -> dict[str, any]:
    """
    转录音频帧

    Args:
        pcm_bytes: 16kHz mono PCM int16 二进制数据

    Returns:
        {
            "text": str,       # 转录文本，空字符串表示静音/无内容
            "error": str|None, # 错误信息
            "code": int|None   # 错误码（2001=asr_failed）
        }
    """
    if _model is None:
        return {"text": "", "error": "asr_unavailable", "code": 2001}

    if not pcm_bytes:
        return {"text": "", "error": None, "code": None}

    # 转换为 numpy array
    wave = np.frombuffer(pcm_bytes, dtype=np.int16)

    # VAD: 能量过滤
    if _compute_energy(wave) < ENERGY_THRESHOLD:
        return {"text": "", "error": None, "code": None}

    # 归一化到 [-1, 1]
    audio = wave.astype(np.float32) / 32768.0

    # 异步推理（在线程池中执行，避免阻塞事件循环）
    try:
        text = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(_executor, _do_transcribe_sync, audio),
            timeout=ASR_TIMEOUT
        )
        return {"text": text, "error": None, "code": None}
    except asyncio.TimeoutError:
        logger.warning("ASR timeout")
        return {"text": "", "error": "asr_timeout", "code": 2001}
    except Exception as exc:
        logger.error(f"ASR failed: {exc}", exc_info=True)
        return {"text": "", "error": f"asr_failed: {exc}", "code": 2001}


def init_asr() -> None:
    """初始化 ASR 模块（应用启动时调用）"""
    _load_model()
