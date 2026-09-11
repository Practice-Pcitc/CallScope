from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TokenBudget:
    max_context_chars: int
    max_source_chars: int
    max_source_per_node: int
    max_nodes: int
    max_edges: int

    def trim_source(self, source: str) -> tuple[str, bool]:
        if len(source) <= self.max_source_per_node:
            return source, False
        head_size = int(self.max_source_per_node * 0.65)
        tail_size = self.max_source_per_node - head_size
        return (
            f"{source[:head_size]}\n\n/* ... 中间源码已按 Token 预算裁剪 ... */\n\n"
            f"{source[-tail_size:]}",
            True,
        )

    @staticmethod
    def estimate_tokens(text: str) -> int:
        # 中英文混合源码的保守估算；Provider 返回的真实 usage 会覆盖该估值。
        return max(1, (len(text) + 2) // 3)
