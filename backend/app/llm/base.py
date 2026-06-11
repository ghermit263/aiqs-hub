from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """所有模型供应商的统一接口：输入 prompt，输出文本。"""

    name: str = "base"

    def __init__(self, base_url: str = "", api_key: str = "", model: str = "", timeout: int = 180):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @abstractmethod
    def complete(self, system: str, user: str) -> tuple[str, dict]:
        """返回 (生成文本, usage信息dict{prompt_tokens, completion_tokens})"""
        ...
