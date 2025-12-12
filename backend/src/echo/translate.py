"""
百度翻译 API 集成

支持：
- 英译中（en → zh）
- 超时重试
- 错误处理
"""
from __future__ import annotations

import hashlib
import logging
import os
import random
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# 百度翻译配置
BAIDU_APPID = os.getenv("BAIDU_APPID", "")
BAIDU_SECRET = os.getenv("BAIDU_SECRET", "")
BAIDU_API_URL = "https://fanyi-api.baidu.com/api/trans/vip/translate"
TRANSLATE_TIMEOUT = float(os.getenv("TRANSLATE_TIMEOUT", "5.0"))
TRANSLATE_RETRIES = int(os.getenv("TRANSLATE_RETRIES", "2"))


def _generate_sign(query: str, salt: str) -> str:
    """
    生成百度翻译 API 签名

    签名算法：MD5(appid+q+salt+密钥)
    """
    sign_str = f"{BAIDU_APPID}{query}{salt}{BAIDU_SECRET}"
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest()


async def translate_text(text: str, from_lang: str = "en", to_lang: str = "zh") -> dict[str, Any]:
    """
    翻译文本（英译中）

    Args:
        text: 待翻译文本
        from_lang: 源语言（默认 en）
        to_lang: 目标语言（默认 zh）

    Returns:
        {
            "text": str,       # 翻译结果，空字符串表示失败
            "error": str|None, # 错误信息
            "code": int|None   # 错误码（3001=translate_failed）
        }
    """
    if not BAIDU_APPID or not BAIDU_SECRET:
        return {"text": "", "error": "translate_not_configured", "code": 3001}

    if not text.strip():
        return {"text": "", "error": None, "code": None}

    # 生成随机盐值
    salt = str(random.randint(32768, 65536))

    # 生成签名
    sign = _generate_sign(text, salt)

    # 构造请求参数
    params = {
        "q": text,
        "from": from_lang,
        "to": to_lang,
        "appid": BAIDU_APPID,
        "salt": salt,
        "sign": sign,
    }

    # 发起请求（带重试）
    for attempt in range(TRANSLATE_RETRIES + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(BAIDU_API_URL, params=params, timeout=TRANSLATE_TIMEOUT)
                response.raise_for_status()

                data = response.json()

                # 检查错误码
                if "error_code" in data:
                    error_code = data["error_code"]
                    error_msg = data.get("error_msg", "Unknown error")
                    logger.warning(f"Baidu translate error: {error_code} - {error_msg}")
                    return {"text": "", "error": f"baidu_error_{error_code}", "code": 3001}

                # 提取翻译结果
                trans_result = data.get("trans_result", [])
                if not trans_result:
                    return {"text": "", "error": "empty_result", "code": 3001}

                translated = trans_result[0].get("dst", "")
                return {"text": translated, "error": None, "code": None}

        except httpx.TimeoutException:
            if attempt < TRANSLATE_RETRIES:
                logger.warning(f"Translate timeout, retrying ({attempt + 1}/{TRANSLATE_RETRIES})...")
                continue
            logger.error("Translate timeout after retries")
            return {"text": "", "error": "translate_timeout", "code": 3001}

        except Exception as exc:
            logger.error(f"Translate failed: {exc}", exc_info=True)
            return {"text": "", "error": f"translate_failed: {exc}", "code": 3001}

    return {"text": "", "error": "translate_failed", "code": 3001}
