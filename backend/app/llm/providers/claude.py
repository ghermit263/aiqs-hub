"""Anthropic Claude 原生接口。base_url 默认 https://api.anthropic.com"""
import httpx

from ..base import LLMProvider


class ClaudeProvider(LLMProvider):
    name = "claude"

    def complete(self, system: str, user: str) -> tuple[str, dict]:
        base = self.base_url or "https://api.anthropic.com"
        resp = httpx.post(
            f"{base}/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": self.model or "claude-sonnet-4-6",
                "max_tokens": 8192,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=self.timeout,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code} {resp.reason_phrase}：{resp.text[:500]}")
        data = resp.json()
        text = "".join(b.get("text", "") for b in data.get("content", []))
        usage = data.get("usage", {})
        return text, {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
        }
