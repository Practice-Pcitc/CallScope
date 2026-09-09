from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.llm.token_budget import TokenBudget
from app.models.api_endpoint import ApiEndpoint
from app.repositories.endpoint_repository import EndpointRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.ai_analysis import (
    AIAnalysisContext,
    AllowedReferences,
    ContextMeta,
    EdgeContext,
    EndpointContext,
    NodeContext,
    SourceSnippet,
    StaticCondition,
    StaticDataOperation,
    StaticExternalCall,
)
from app.services.graph_service import GraphService

CONDITION_PATTERN = re.compile(
    r"^\s*(if\b.+|elif\b.+|raise\b.+|throw\s+.+|except\b.*|catch\s*\(.+)",
    re.IGNORECASE,
)


class AIContextBuilder:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.endpoints = EndpointRepository(session)
        self.graphs = GraphService(session)
        self.budget = TokenBudget(
            max_context_chars=settings.ai_max_context_chars,
            max_source_chars=settings.ai_max_source_chars,
            max_source_per_node=settings.ai_max_source_per_node,
            max_nodes=settings.ai_max_nodes,
            max_edges=settings.ai_max_edges,
        )

    def build_for_endpoints(
        self,
        *,
        project_id: str,
        endpoint_ids: list[str],
        depth: int,
        include_source: bool,
        include_medium_confidence: bool,
        scope_type: str | None = None,
    ) -> AIAnalysisContext:
        project = self.projects.get(project_id)
        if not project or not project.active_revision_id:
            raise AppException(
                code="PROJECT_NOT_READY",
                message="项目尚未完成静态扫描",
                status_code=409,
            )
        clean_ids = list(dict.fromkeys(endpoint_ids))
        endpoint_entities = [
            self._active_endpoint(project_id, project.active_revision_id, endpoint_id)
            for endpoint_id in clean_ids
        ]
        graph = (
            self.graphs.endpoint_graph(
                project_id=project_id,
                endpoint_id=clean_ids[0],
                include_lower_confidence=include_medium_confidence,
                depth=depth,
            )
            if len(clean_ids) == 1
            else self.graphs.combined_graph(
                project_id=project_id,
                endpoint_ids=clean_ids,
                include_lower_confidence=include_medium_confidence,
                depth=depth,
            )
        )

        original_node_count = len(graph.nodes)
        original_edge_count = len(graph.edges)
        graph_nodes = graph.nodes[: self.budget.max_nodes]
        allowed_node_ids = {node.id for node in graph_nodes}
        graph_edges = [
            edge
            for edge in graph.edges
            if edge.source in allowed_node_ids and edge.target in allowed_node_ids
        ][: self.budget.max_edges]
        truncated = (
            graph.meta.truncated
            or original_node_count > len(graph_nodes)
            or original_edge_count > len(graph_edges)
        )

        endpoint_contexts = [self._endpoint_context(item) for item in endpoint_entities]
        nodes = [
            NodeContext(
                id=node.id,
                node_type=node.type,
                name=node.name,
                qualified_name=node.qualified_name,
                module_name=node.module_name,
                file_path=node.file_path,
                start_line=node.start_line,
                end_line=node.end_line,
                signature=node.signature,
                metadata=node.metadata,
            )
            for node in graph_nodes
        ]
        edges = [
            EdgeContext(
                id=edge.id,
                source=edge.source,
                target=edge.target,
                relation_type=edge.relation_type,
                confidence=edge.confidence,
                file_path=edge.file_path,
                line_number=edge.line_number,
                evidence=edge.evidence,
                metadata=edge.metadata,
            )
            for edge in graph_edges
        ]
        snippets = self._source_snippets(project.root_path, graph_nodes) if include_source else []
        conditions = self._conditions(snippets)
        data_operations = self._data_operations(nodes)
        external_calls = self._external_calls(nodes)
        related = self._related_candidates(
            project_id=project_id,
            revision_id=project.active_revision_id,
            selected=endpoint_entities,
        )

        evidence_ids = [snippet.evidence_id for snippet in snippets]
        context = AIAnalysisContext(
            context_meta=ContextMeta(
                project_id=project_id,
                scan_revision_id=project.active_revision_id,
                scope_type=scope_type
                or ("SINGLE_ENDPOINT" if len(clean_ids) == 1 else "COMBINED_ENDPOINTS"),
                depth=depth,
                graph_version=settings.ai_graph_version,
                truncated=truncated,
                omitted_nodes=max(original_node_count - len(nodes), 0),
                omitted_edges=max(original_edge_count - len(edges), 0),
            ),
            endpoints=endpoint_contexts,
            nodes=nodes,
            edges=edges,
            source_snippets=snippets,
            conditions=conditions,
            data_operations=data_operations,
            external_calls=external_calls,
            related_endpoint_candidates=related,
            allowed_references=AllowedReferences(
                endpoint_ids=[
                    *[item.id for item in endpoint_contexts],
                    *[item.id for item in related],
                ],
                node_ids=[item.id for item in nodes],
                edge_ids=[item.id for item in edges],
                evidence_ids=evidence_ids,
            ),
        )
        return self._fit_context_budget(context)

    def build_for_node(
        self,
        *,
        project_id: str,
        node_id: str,
        depth: int,
        include_source: bool,
        include_medium_confidence: bool,
    ) -> AIAnalysisContext:
        project = self.projects.get(project_id)
        if not project or not project.active_revision_id:
            raise AppException(
                code="PROJECT_NOT_READY",
                message="项目尚未完成静态扫描",
                status_code=409,
            )
        detail = self.graphs.node_detail(project_id=project_id, node_id=node_id)
        endpoint_ids = list(
            dict.fromkeys(
                [
                    *detail.entry_endpoint_ids,
                    *[
                        endpoint_id
                        for edge in [*detail.upstream, *detail.downstream]
                        for endpoint_id in edge.entry_endpoint_ids
                    ],
                ]
            )
        )
        if not endpoint_ids:
            visited = {node_id}
            frontier = {node_id}
            confidences = (
                {"CONFIRMED", "HIGH", "MEDIUM", "LOW"}
                if include_medium_confidence
                else {"CONFIRMED", "HIGH"}
            )
            for _level in range(max(depth * 3, 12)):
                incoming = self.graphs.graphs.incoming(
                    project_id=project_id,
                    revision_id=project.active_revision_id,
                    node_ids=frontier,
                    confidences=confidences,
                )
                next_frontier = {
                    edge.source_node_id for edge in incoming if edge.source_node_id not in visited
                }
                visited.update(next_frontier)
                if not next_frontier or len(visited) >= 2000:
                    break
                frontier = next_frontier
            endpoint_ids = list(dict.fromkeys(self.graphs.graphs.endpoint_ids_for_nodes(visited)))
        if endpoint_ids:
            return self.build_for_endpoints(
                project_id=project_id,
                endpoint_ids=endpoint_ids[:10],
                depth=depth,
                include_source=include_source,
                include_medium_confidence=include_medium_confidence,
                scope_type="NODE_IMPACT",
            )
        raise AppException(
            code="NODE_HAS_NO_ENDPOINT",
            message="当前节点没有可追溯的接口入口",
            status_code=409,
        )

    def _active_endpoint(
        self,
        project_id: str,
        revision_id: str,
        endpoint_id: str,
    ) -> ApiEndpoint:
        endpoint = self.endpoints.get(endpoint_id)
        if (
            not endpoint
            or endpoint.project_id != project_id
            or endpoint.scan_revision_id != revision_id
        ):
            raise AppException(
                code="ENDPOINT_NOT_FOUND",
                message="接口不存在或不属于当前扫描版本",
                status_code=404,
            )
        return endpoint

    @staticmethod
    def _endpoint_context(endpoint: ApiEndpoint) -> EndpointContext:
        return EndpointContext(
            id=endpoint.id,
            http_method=endpoint.http_method,
            path=endpoint.path,
            function_name=endpoint.function_name,
            qualified_name=endpoint.qualified_name,
            module_name=endpoint.module_name,
            file_path=endpoint.file_path,
            start_line=endpoint.start_line,
            end_line=endpoint.end_line,
            summary=endpoint.summary,
            parameters=endpoint.parameters,
            response_type=endpoint.response_type,
            dependencies=endpoint.dependencies,
            tags=endpoint.tags,
            metadata=endpoint.extra_metadata,
        )

    def _source_snippets(self, root_path: str, nodes) -> list[SourceSnippet]:
        root = Path(root_path).resolve()
        snippets: list[SourceSnippet] = []
        total_chars = 0
        seen_locations: set[tuple[str | None, int | None, int | None]] = set()
        for node in nodes:
            location = (node.file_path, node.start_line, node.end_line)
            if location in seen_locations:
                continue
            seen_locations.add(location)
            content = self._read_node_source(root, node)
            if not content:
                continue
            content, trimmed = self.budget.trim_source(content)
            remaining = self.budget.max_source_chars - total_chars
            if remaining <= 0:
                break
            if len(content) > remaining:
                content = content[:remaining]
                trimmed = True
            evidence_id = f"source:{node.id}"
            snippets.append(
                SourceSnippet(
                    evidence_id=evidence_id,
                    node_id=node.id,
                    file_path=node.file_path,
                    start_line=node.start_line,
                    end_line=node.end_line,
                    content=content,
                    truncated=trimmed,
                )
            )
            total_chars += len(content)
        return snippets

    @staticmethod
    def _read_node_source(root: Path, node) -> str:
        if node.file_path:
            target = (root / node.file_path).resolve()
            try:
                target.relative_to(root)
            except ValueError:
                return ""
            if target.is_file():
                try:
                    lines = target.read_text(encoding="utf-8").splitlines()
                    start = max((node.start_line or 1) - 1, 0)
                    end = min(node.end_line or start + 80, len(lines))
                    return "\n".join(lines[start:end])
                except (OSError, UnicodeError):
                    return ""
        return ""

    @staticmethod
    def _conditions(snippets: list[SourceSnippet]) -> list[StaticCondition]:
        conditions: list[StaticCondition] = []
        for snippet in snippets:
            for offset, line in enumerate(snippet.content.splitlines()):
                match = CONDITION_PATTERN.match(line)
                if not match:
                    continue
                expression = match.group(1).strip()
                lowered = expression.lower()
                kind = (
                    "ERROR_HANDLING"
                    if lowered.startswith(("raise", "throw", "except", "catch"))
                    else "BUSINESS_RULE"
                )
                conditions.append(
                    StaticCondition(
                        node_id=snippet.node_id,
                        evidence_id=snippet.evidence_id,
                        expression=expression[:500],
                        line_number=(snippet.start_line or 1) + offset,
                        kind=kind,
                    )
                )
                if len(conditions) >= 80:
                    return conditions
        return conditions

    @staticmethod
    def _data_operations(nodes: list[NodeContext]) -> list[StaticDataOperation]:
        results: list[StaticDataOperation] = []
        for node in nodes:
            name = node.name
            lowered = name.lower()
            if node.node_type not in {
                "REPOSITORY",
                "DATABASE_OPERATION",
                "DATABASE_TABLE",
            } and not any(
                token in lowered
                for token in (
                    "save",
                    "insert",
                    "select",
                    "find",
                    "get",
                    "update",
                    "delete",
                    "remove",
                )
            ):
                continue
            operation = "UNKNOWN"
            if any(token in lowered for token in ("save", "insert", "create", "add")):
                operation = "WRITE"
            elif any(token in lowered for token in ("update", "edit", "modify")):
                operation = "UPDATE"
            elif any(token in lowered for token in ("delete", "remove")):
                operation = "DELETE"
            elif any(token in lowered for token in ("select", "find", "get", "query", "list")):
                operation = "READ"
            resource = str(node.metadata.get("tableName") or "UNKNOWN_TABLE")
            results.append(
                StaticDataOperation(
                    node_id=node.id,
                    resource=resource,
                    operation=operation,
                    method_name=node.qualified_name,
                )
            )
        return results[:80]

    @staticmethod
    def _external_calls(nodes: list[NodeContext]) -> list[StaticExternalCall]:
        type_map = {
            "REDIS": "REDIS",
            "EXTERNAL_HTTP": "EXTERNAL_API",
            "DATABASE_TABLE": "DATABASE",
            "DATABASE_OPERATION": "DATABASE",
        }
        results = []
        for node in nodes:
            dependency_type = type_map.get(node.node_type)
            if not dependency_type:
                lowered = f"{node.name} {node.qualified_name}".lower()
                if any(token in lowered for token in ("http", "client", "feign")):
                    dependency_type = "EXTERNAL_API"
                elif "redis" in lowered:
                    dependency_type = "REDIS"
                elif any(token in lowered for token in ("oss", "s3", "storage")):
                    dependency_type = "OBJECT_STORAGE"
            if dependency_type:
                results.append(
                    StaticExternalCall(
                        node_id=node.id,
                        dependency_type=dependency_type,
                        name=node.qualified_name,
                    )
                )
        return results[:50]

    def _related_candidates(
        self,
        *,
        project_id: str,
        revision_id: str,
        selected: list[ApiEndpoint],
    ) -> list[EndpointContext]:
        selected_ids = {item.id for item in selected}
        candidates: dict[str, ApiEndpoint] = {}
        for module_name in {item.module_name for item in selected}:
            items, _ = self.endpoints.list(
                project_id=project_id,
                revision_id=revision_id,
                search=None,
                http_method=None,
                module=module_name,
                tag=None,
                offset=0,
                limit=20,
            )
            for item in items:
                if item.id not in selected_ids:
                    candidates[item.id] = item
        return [self._endpoint_context(item) for item in list(candidates.values())[:20]]

    def _fit_context_budget(self, context: AIAnalysisContext) -> AIAnalysisContext:
        payload = context.model_dump_json()
        if len(payload) <= self.budget.max_context_chars:
            return context
        context.context_meta.truncated = True
        while (
            len(context.model_dump_json()) > self.budget.max_context_chars
            and context.source_snippets
        ):
            context.source_snippets.pop()
        allowed_evidence = {item.evidence_id for item in context.source_snippets}
        context.conditions = [
            item for item in context.conditions if item.evidence_id in allowed_evidence
        ]
        context.allowed_references.evidence_ids = sorted(allowed_evidence)
        return context
