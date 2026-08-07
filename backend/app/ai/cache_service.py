from __future__ import annotations

import hashlib
import json

from app.ai.schemas import AIAnalysisContext


def context_hash(context: AIAnalysisContext) -> str:
    canonical = context.model_dump_json(by_alias=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def cache_key(
    *,
    project_id: str,
    revision_id: str,
    scope_type: str,
    scope_key: str,
    provider: str,
    model: str,
    prompt_version: str,
    graph_version: str,
    depth: int,
    options: dict,
    context_digest: str,
) -> str:
    payload = {
        "project_id": project_id,
        "revision_id": revision_id,
        "scope_type": scope_type,
        "scope_key": scope_key,
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "graph_version": graph_version,
        "depth": depth,
        "options": options,
        "context_hash": context_digest,
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
