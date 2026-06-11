"""model_gateway：统一模型调用入口。

- 配置优先级：数据库 app_settings 表 > .env / 环境变量默认值
- intranet_only 开关：开启后仅允许 mock 和 base_url 为内网地址的供应商
- 所有调用写 llm_call_logs
"""
import ipaddress
import json
import re
import time
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from ..config import settings
from ..logger import logger
from ..models import AppSetting, LlmCallLog
from .base import LLMProvider
from .providers.claude import ClaudeProvider
from .providers.mock import MockProvider
from .providers.openai_compat import OpenAICompatProvider

PROVIDERS: dict[str, type[LLMProvider]] = {
    "mock": MockProvider,
    "openai_compat": OpenAICompatProvider,
    "claude": ClaudeProvider,
}


def get_effective_config(db: Session) -> dict:
    cfg = {
        "llm_provider": settings.llm_provider,
        "llm_base_url": settings.llm_base_url,
        "llm_api_key": settings.llm_api_key,
        "llm_model": settings.llm_model,
        "intranet_only": settings.intranet_only,
    }
    for row in db.query(AppSetting).all():
        if row.key in cfg:
            if row.key == "intranet_only":
                cfg[row.key] = row.value.lower() in ("1", "true", "yes")
            else:
                cfg[row.key] = row.value
    return cfg


def _is_intranet(url: str) -> bool:
    host = urlparse(url).hostname or ""
    if host in ("localhost",):
        return True
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:
        return False


def build_provider(db: Session) -> LLMProvider:
    cfg = get_effective_config(db)
    name = cfg["llm_provider"]
    cls = PROVIDERS.get(name)
    if not cls:
        raise ValueError(f"未知的模型供应商: {name}，可选: {list(PROVIDERS)}")
    if cfg["intranet_only"] and name != "mock" and not _is_intranet(cfg["llm_base_url"]):
        raise ValueError("内网模式已开启：仅允许调用内网地址的模型服务（base_url 须为内网IP）")
    if name != "mock" and name == "openai_compat" and not cfg["llm_base_url"]:
        raise ValueError("openai_compat 供应商需要配置 base_url")
    return cls(
        base_url=cfg["llm_base_url"],
        api_key=cfg["llm_api_key"],
        model=cfg["llm_model"],
        timeout=settings.llm_timeout,
    )


def call_llm(db: Session, system: str, user: str, task_id: int | None = None,
             retries: int = 2) -> str:
    """带重试与调用日志的统一调用。"""
    provider = build_provider(db)
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        start = time.monotonic()
        log = LlmCallLog(task_id=task_id, provider=provider.name, model=provider.model)
        try:
            text, usage = provider.complete(system, user)
            log.prompt_tokens = usage.get("prompt_tokens", 0)
            log.completion_tokens = usage.get("completion_tokens", 0)
            log.latency_ms = int((time.monotonic() - start) * 1000)
            log.success = True
            db.add(log)
            db.commit()
            logger.info("LLM调用成功 task=%s provider=%s model=%s 耗时=%sms tokens=%s/%s",
                        task_id, provider.name, provider.model, log.latency_ms,
                        log.prompt_tokens, log.completion_tokens)
            return text
        except Exception as e:  # noqa: BLE001
            log.latency_ms = int((time.monotonic() - start) * 1000)
            log.success = False
            log.error_msg = str(e)[:2000]
            db.add(log)
            db.commit()
            logger.error("LLM调用失败 task=%s provider=%s model=%s 第%s次尝试: %s",
                         task_id, provider.name, provider.model, attempt + 1, str(e)[:500])
            last_err = e
    raise RuntimeError(f"模型调用失败（已重试{retries}次）: {last_err}")


def extract_json(text: str) -> dict:
    """从模型输出中尽力提取 JSON 对象（容忍 markdown 代码块等包裹）。"""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if m:
        text = m.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"模型输出中未找到 JSON: {text[:200]}")
    return json.loads(text[start : end + 1])
