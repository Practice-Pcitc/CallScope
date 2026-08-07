from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from uuid import uuid4

from app.ai.exceptions import AIAnalysisError
from app.ai.providers.base import ProviderResult


class OpenAICompatibleProvider:
    provider_name = "openai-compatible"

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str,
        timeout_seconds: int,
    ) -> None:
        self.model_name = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate(self, system_prompt: str, user_prompt: str) -> ProviderResult:
        request_id = str(uuid4())
        body = json.dumps(
            {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Request-ID": request_id,
            },
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AIAnalysisError(f"AI Provider 调用失败：{exc}") from exc
        try:
            choice = payload["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIAnalysisError("AI Provider 返回格式不完整") from exc
        usage = payload.get("usage") or {}
        return ProviderResult(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            latency_ms=int((time.perf_counter() - started) * 1000),
            finish_reason=choice.get("finish_reason"),
            request_id=payload.get("id") or request_id,
        )
