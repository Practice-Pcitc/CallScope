from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from app.ai.exceptions import AIAnalysisError
from app.ai.schemas import AIAnalysisContext, AIChainAnalysis


class ResponseParser:
    def parse(
        self,
        content: str,
        context: AIAnalysisContext,
    ) -> tuple[AIChainAnalysis, int]:
        payload = self._json_payload(content)
        invalid_count = self._clean_references(payload, context)
        try:
            return AIChainAnalysis.model_validate(payload), invalid_count
        except ValidationError as exc:
            raise AIAnalysisError(f"AI 返回结果不符合 Schema：{exc}") from exc

    @staticmethod
    def _json_payload(content: str) -> dict[str, Any]:
        cleaned = content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start < 0 or end <= start:
                raise AIAnalysisError("AI 未返回有效 JSON") from None
            try:
                payload = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError as exc:
                raise AIAnalysisError(f"AI JSON 解析失败：{exc}") from exc
        if not isinstance(payload, dict):
            raise AIAnalysisError("AI 返回值必须是 JSON 对象")
        return payload

    def _clean_references(
        self,
        payload: dict[str, Any],
        context: AIAnalysisContext,
    ) -> int:
        allowed = context.allowed_references
        allowed_sets = {
            "node_ids": set(allowed.node_ids),
        }
        invalid_count = 0
        analysis_arrays = [
            "business_flow",
            "business_rules",
            "state_changes",
            "failure_flows",
            "key_business_nodes",
            "business_risks",
        ]
        for array_name in analysis_arrays:
            items = payload.get(array_name, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                for field, allowed_values in allowed_sets.items():
                    values = item.get(field, [])
                    if not isinstance(values, list):
                        item[field] = []
                        invalid_count += 1
                        continue
                    clean = [value for value in values if value in allowed_values]
                    invalid_count += len(values) - len(clean)
                    item[field] = clean
        related_items = payload.get("related_endpoints", [])
        if isinstance(related_items, list):
            clean_related = []
            for item in related_items:
                if (
                    not isinstance(item, dict)
                    or item.get("endpoint_id") not in set(allowed.endpoint_ids)
                ):
                    invalid_count += 1
                    continue
                clean_related.append(item)
            payload["related_endpoints"] = clean_related
        return invalid_count
