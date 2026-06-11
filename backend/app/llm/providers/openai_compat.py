"""OpenAI 兼容接口：覆盖 OpenAI / DeepSeek / 通义千问 / 豆包 / vLLM、Ollama 等内网模型。

只需配置 base_url + api_key + model：
  OpenAI:   https://api.openai.com/v1
  DeepSeek: https://api.deepseek.com/v1
  通义:     https://dashscope.aliyuncs.com/compatible-mode/v1
  豆包:     https://ark.cn-beijing.volces.com/api/v3
  内网vLLM: http://<内网IP>:8000/v1
"""
import httpx

from ..base import LLMProvider


class OpenAICompatProvider(LLMProvider):
    name = "openai_compat"

    def complete(self, system: str, user: str) -> tuple[str, dict]:
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.7,
            },
            timeout=self.timeout,
        )
        if resp.status_code >= 400:
            # 带上响应正文，否则只有状态码无法定位问题（如 Model Not Exist / 余额不足）
            raise RuntimeError(f"HTTP {resp.status_code} {resp.reason_phrase}：{resp.text[:500]}")
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return text, {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        }
