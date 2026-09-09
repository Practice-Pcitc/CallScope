from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True)
class ProviderResult:
    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    finish_reason: str | None = None
    request_id: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class LLMProvider(Protocol):
    provider_name: str
    model_name: str

    def generate(self, system_prompt: str, user_prompt: str) -> ProviderResult: ...
