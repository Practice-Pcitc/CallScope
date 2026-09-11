from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import timedelta
from time import perf_counter

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.exceptions import AppException
from app.core.logging import logger
from app.llm import GroundedLocalProvider, OpenAICompatibleProvider
from app.llm.exceptions import AIAnalysisError
from app.llm.response_parser import ResponseParser
from app.models.ai_analysis import AIAnalysis
from app.models.project import utc_now
from app.prompts.analysis import PromptBuilder
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.ai_analysis import (
    AIAnalysisContext,
    AIAnalysisData,
    AIAnalysisRequest,
    AIChainAnalysis,
)
from app.services.ai_cache import cache_key, context_hash
from app.services.ai_context_service import AIContextBuilder


class AIAnalysisService:
    def __init__(
        self, session: Session, schedule: Callable[[str, AIAnalysisContext], None] | None = None
    ) -> None:
        self.schedule = schedule
        self.session = session
        self.contexts = AIContextBuilder(session)
        self.analyses = AIAnalysisRepository(session)
        self.projects = ProjectRepository(session)
        self.prompts = PromptBuilder()
        self.parser = ResponseParser()

    def analyze_endpoints(
        self,
        *,
        project_id: str,
        endpoint_ids: list[str],
        request: AIAnalysisRequest,
    ) -> tuple[AIAnalysis, bool]:
        clean_ids = sorted(set(endpoint_ids))
        scope_type = "SINGLE_ENDPOINT" if len(clean_ids) == 1 else "COMBINED_ENDPOINTS"
        context = self.contexts.build_for_endpoints(
            project_id=project_id,
            endpoint_ids=clean_ids,
            depth=request.depth,
            include_source=request.include_source,
            include_medium_confidence=request.include_medium_confidence,
            scope_type=scope_type,
        )
        return self._analyze_context(
            context=context,
            scope_type=scope_type,
            scope_key=json.dumps(clean_ids, separators=(",", ":")),
            request=request,
        )

    def analyze_node(
        self,
        *,
        project_id: str,
        node_id: str,
        request: AIAnalysisRequest,
    ) -> tuple[AIAnalysis, bool]:
        context = self.contexts.build_for_node(
            project_id=project_id,
            node_id=node_id,
            depth=request.depth,
            include_source=request.include_source,
            include_medium_confidence=request.include_medium_confidence,
        )
        return self._analyze_context(
            context=context,
            scope_type="NODE_IMPACT",
            scope_key=node_id,
            request=request,
        )

    def get(self, analysis_id: str) -> AIAnalysis:
        analysis = self.analyses.get(analysis_id)
        if not analysis:
            raise AppException(
                code="AI_ANALYSIS_NOT_FOUND",
                message="AI 分析结果不存在",
                status_code=404,
            )
        project = self.projects.get(analysis.project_id)
        if (
            project
            and project.active_revision_id
            and analysis.scan_revision_id != project.active_revision_id
            and analysis.status == "COMPLETED"
        ):
            analysis.status = "STALE"
            analysis.stale_at = utc_now()
            self.session.commit()
        return analysis

    def regenerate(self, analysis_id: str) -> tuple[AIAnalysis, bool]:
        existing = self.get(analysis_id)
        request = AIAnalysisRequest(
            depth=existing.depth,
            include_source=bool(existing.options.get("include_source", True)),
            include_medium_confidence=bool(
                existing.options.get("include_medium_confidence", False)
            ),
            force_regenerate=True,
        )
        if existing.scope_type == "NODE_IMPACT":
            return self.analyze_node(
                project_id=existing.project_id,
                node_id=existing.scope_key,
                request=request,
            )
        endpoint_ids = json.loads(existing.scope_key)
        return self.analyze_endpoints(
            project_id=existing.project_id,
            endpoint_ids=endpoint_ids,
            request=request,
        )

    def _analyze_context(
        self,
        *,
        context: AIAnalysisContext,
        scope_type: str,
        scope_key: str,
        request: AIAnalysisRequest,
    ) -> tuple[AIAnalysis, bool]:
        provider = self._provider()
        options = {
            "include_source": request.include_source,
            "include_medium_confidence": request.include_medium_confidence,
        }
        digest = context_hash(context)
        key = cache_key(
            project_id=context.context_meta.project_id,
            revision_id=context.context_meta.scan_revision_id,
            scope_type=scope_type,
            scope_key=scope_key,
            provider=provider.provider_name,
            model=provider.model_name,
            prompt_version=settings.ai_prompt_version,
            graph_version=settings.ai_graph_version,
            depth=request.depth,
            options=options,
            context_digest=digest,
        )
        cached = self.analyses.get_by_cache_key(key)
        if cached and cached.status == "COMPLETED" and not request.force_regenerate:
            return cached, True
        if cached and cached.status == "ANALYZING":
            return cached, True
        if cached:
            cached.cache_key = hashlib.sha256(
                f"{cached.cache_key}:superseded:{cached.id}".encode()
            ).hexdigest()
            cached.status = "STALE"
            cached.stale_at = utc_now()
            self.session.flush()

        analysis = AIAnalysis(
            project_id=context.context_meta.project_id,
            scan_revision_id=context.context_meta.scan_revision_id,
            scope_type=scope_type,
            scope_key=scope_key,
            status="ANALYZING",
            provider=provider.provider_name,
            model=provider.model_name,
            prompt_version=settings.ai_prompt_version,
            graph_version=settings.ai_graph_version,
            depth=request.depth,
            options=options,
            context_hash=digest,
            cache_key=key,
            result=None,
            token_usage={},
        )
        try:
            self.analyses.add(analysis)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = self.analyses.get_by_cache_key(key)
            if existing is not None:
                return existing, True
            raise
        if self.schedule and settings.ai_provider == "openai-compatible":
            self.schedule(analysis.id, context)
            return analysis, False
        self.execute(analysis, context)
        return analysis, False

    def execute(self, analysis: AIAnalysis, context: AIAnalysisContext) -> None:
        provider = self._provider()
        started = perf_counter()
        system_prompt, user_prompt = self.prompts.build(
            context=context,
            task_type=analysis.scope_type,
        )
        try:
            provider_result = None
            parsed = None
            invalid_count = 0
            last_error: Exception | None = None
            for _attempt in range(settings.ai_max_retries + 1):
                try:
                    provider_result = provider.generate(system_prompt, user_prompt)
                    parsed, invalid_count = self.parser.parse(
                        provider_result.content,
                        context,
                    )
                    break
                except AIAnalysisError as exc:
                    last_error = exc
                    logger.warning(
                        "ai_retry",
                        extra={
                            "run_id": analysis.id,
                            "attempt": _attempt + 1,
                            "error_type": type(exc).__name__,
                        },
                    )
                    user_prompt += "\n\n上一轮输出未通过校验。请严格按 OUTPUT_SCHEMA 返回 JSON。"
            if parsed is None or provider_result is None:
                raise last_error or AIAnalysisError("AI 分析失败")
            analysis.result = parsed.model_dump(by_alias=False)
            analysis.status = "COMPLETED"
            analysis.invalid_reference_count = invalid_count
            analysis.token_usage = {
                "input_tokens": provider_result.input_tokens,
                "output_tokens": provider_result.output_tokens,
                "latency_ms": provider_result.latency_ms,
                "request_id": provider_result.request_id,
                **provider_result.metadata,
            }
            analysis.completed_at = utc_now()
            analysis.error_message = None
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            failed = self.analyses.get(analysis.id)
            if failed:
                failed.status = "FAILED"
                failed.error_message = "AI 分析失败，请检查模型配置或重试"
                self.session.commit()
                analysis = failed
            logger.error(
                "ai_failed", extra={"run_id": analysis.id, "error_type": type(exc).__name__}
            )
        logger.info(
            "ai_completed",
            extra={
                "run_id": analysis.id,
                "provider": provider.provider_name,
                "model": provider.model_name,
                "status": analysis.status,
                "duration_ms": round((perf_counter() - started) * 1000),
                "input_tokens": analysis.token_usage.get("input_tokens", 0),
                "output_tokens": analysis.token_usage.get("output_tokens", 0),
            },
        )

    @staticmethod
    def _provider():
        configured = settings.ai_provider.strip().lower()
        if configured in {"local", "grounded-local", "evidence"}:
            return GroundedLocalProvider()
        if not settings.ai_api_key:
            raise AppException(
                code="AI_PROVIDER_NOT_CONFIGURED",
                message="尚未配置 AI Provider API Key",
                status_code=503,
            )
        return OpenAICompatibleProvider(
            model=settings.ai_model,
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
            timeout_seconds=settings.ai_timeout_seconds,
        )

    @staticmethod
    def serialize(analysis: AIAnalysis, *, cached: bool) -> AIAnalysisData:
        result = None if not analysis.result else AIChainAnalysis.model_validate(analysis.result)
        return AIAnalysisData(
            analysis_id=analysis.id,
            project_id=analysis.project_id,
            scan_revision_id=analysis.scan_revision_id,
            scope_type=analysis.scope_type,
            status=analysis.status,
            provider=analysis.provider,
            model=analysis.model,
            cached=cached,
            stale=analysis.status == "STALE",
            result=result,
            error_message=analysis.error_message,
            token_usage=analysis.token_usage,
            invalid_reference_count=analysis.invalid_reference_count,
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
            completed_at=analysis.completed_at,
        )


def execute_ai_analysis(analysis_id: str, context: AIAnalysisContext) -> None:
    """Background tasks own their database session."""
    with SessionLocal() as session:
        service = AIAnalysisService(session)
        analysis = service.analyses.get(analysis_id)
        if analysis is not None and analysis.status == "ANALYZING":
            service.execute(analysis, context)


def recover_ai_analyses() -> None:
    with SessionLocal() as session:
        repository = AIAnalysisRepository(session)
        repository.mark_interrupted_failed()
        repository.delete_expired(utc_now() - timedelta(days=settings.ai_retention_days))
        session.commit()
