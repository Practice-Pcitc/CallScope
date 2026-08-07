from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import networkx as nx
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.api_endpoint import ApiEndpoint
from app.models.code_node import CodeNode
from app.models.code_relation import CodeRelation
from app.repositories.endpoint_repository import EndpointRepository
from app.repositories.graph_repository import GraphRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.graph import (
    GraphData,
    GraphEdgeData,
    GraphMeta,
    GraphNodeData,
    NodeDetailData,
    RelationDetailData,
    SourceData,
)

DEFAULT_CONFIDENCES = {"CONFIRMED", "HIGH"}
ALL_CONFIDENCES = {"CONFIRMED", "HIGH", "MEDIUM", "LOW"}


class GraphService:
    """向前端提供按需展开的轻量图查询。"""

    def __init__(self, session: Session) -> None:
        self.projects = ProjectRepository(session)
        self.endpoints = EndpointRepository(session)
        self.graphs = GraphRepository(session)

    def endpoint_graph(
        self,
        *,
        project_id: str,
        endpoint_id: str,
        include_lower_confidence: bool,
        depth: int = 1,
    ) -> GraphData:
        project, revision_id = self._active_project(project_id)
        self._endpoint(project_id, revision_id, endpoint_id)
        root = self.graphs.endpoint_root(
            project_id=project_id,
            revision_id=revision_id,
            endpoint_id=endpoint_id,
        )
        if not root:
            raise AppException(
                code="GRAPH_NOT_FOUND",
                message="该接口尚未生成拓扑图",
                status_code=404,
            )
        return self._entry_graph(
            project_id=project.id,
            revision_id=revision_id,
            roots=[root],
            endpoint_ids=[endpoint_id],
            include_lower_confidence=include_lower_confidence,
            depth=depth,
        )

    def combined_graph(
        self,
        *,
        project_id: str,
        endpoint_ids: list[str],
        include_lower_confidence: bool,
        depth: int = 1,
    ) -> GraphData:
        project, revision_id = self._active_project(project_id)
        roots: list[CodeNode] = []
        seen: set[str] = set()
        clean_endpoint_ids: list[str] = []
        for endpoint_id in endpoint_ids:
            if endpoint_id in seen:
                continue
            seen.add(endpoint_id)
            self._endpoint(project_id, revision_id, endpoint_id)
            root = self.graphs.endpoint_root(
                project_id=project_id,
                revision_id=revision_id,
                endpoint_id=endpoint_id,
            )
            if root:
                roots.append(root)
                clean_endpoint_ids.append(endpoint_id)
        if not roots:
            raise AppException(
                code="GRAPH_NOT_FOUND",
                message="所选接口尚未生成拓扑图",
                status_code=404,
            )
        return self._entry_graph(
            project_id=project.id,
            revision_id=revision_id,
            roots=roots,
            endpoint_ids=clean_endpoint_ids,
            include_lower_confidence=include_lower_confidence,
            depth=depth,
        )

    def _entry_graph(
        self,
        *,
        project_id: str,
        revision_id: str,
        roots: list[CodeNode],
        endpoint_ids: list[str],
        include_lower_confidence: bool,
        depth: int,
    ) -> GraphData:
        if depth <= 1:
            return self._one_hop_graph(
                project_id=project_id,
                revision_id=revision_id,
                roots=roots,
                endpoint_ids=endpoint_ids,
                include_lower_confidence=include_lower_confidence,
            )
        return self._multi_hop_graph(
            project_id=project_id,
            revision_id=revision_id,
            roots=roots,
            endpoint_ids=endpoint_ids,
            include_lower_confidence=include_lower_confidence,
            depth=depth,
        )

    def neighbors(
        self,
        *,
        project_id: str,
        node_id: str,
        direction: str,
        include_lower_confidence: bool,
    ) -> GraphData:
        project, revision_id = self._active_project(project_id)
        node = self._node(project_id, revision_id, node_id)
        confidences = self._confidences(include_lower_confidence)
        if direction == "upstream":
            edges = self.graphs.incoming(
                project_id=project_id,
                revision_id=revision_id,
                node_ids={node.id},
                confidences=confidences,
            )
            neighbor_ids = {edge.source_node_id for edge in edges}
        else:
            edges = self.graphs.outgoing(
                project_id=project_id,
                revision_id=revision_id,
                node_ids={node.id},
                confidences=confidences,
            )
            neighbor_ids = {edge.target_node_id for edge in edges}
        neighbors = self.graphs.nodes_by_ids(
            project_id=project_id,
            revision_id=revision_id,
            node_ids=neighbor_ids,
        )
        nodes = [node, *neighbors]
        return self._serialize_graph(
            project_id=project.id,
            revision_id=revision_id,
            roots=[node.id],
            nodes=nodes,
            edges=edges,
            entry_ids_by_node={item.id: set() for item in nodes},
            entry_ids_by_edge={item.id: set() for item in edges},
            depth_by_node={node.id: 0, **{item.id: 1 for item in neighbors}},
            confidences=confidences,
        )

    def node_detail(self, *, project_id: str, node_id: str) -> NodeDetailData:
        _, revision_id = self._active_project(project_id)
        node = self._node(project_id, revision_id, node_id)
        related = self.graphs.related(
            project_id=project_id,
            revision_id=revision_id,
            node_id=node.id,
            confidences=ALL_CONFIDENCES,
        )
        child_count = len(
            self.graphs.outgoing(
                project_id=project_id,
                revision_id=revision_id,
                node_ids={node.id},
                confidences=DEFAULT_CONFIDENCES,
            )
        )
        base = self._node_data(node, child_count=child_count)
        return NodeDetailData(
            **base.model_dump(),
            source_excerpt=node.source_excerpt,
            upstream=[
                self._edge_data(edge)
                for edge in related
                if edge.target_node_id == node.id
            ],
            downstream=[
                self._edge_data(edge)
                for edge in related
                if edge.source_node_id == node.id
            ],
        )

    def source(self, *, project_id: str, node_id: str) -> SourceData:
        project, revision_id = self._active_project(project_id)
        node = self._node(project_id, revision_id, node_id)
        source = node.source_excerpt
        if node.file_path:
            root = Path(project.root_path).resolve()
            target = (root / node.file_path).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise AppException(
                    code="SOURCE_PATH_INVALID",
                    message="源码路径超出项目目录",
                    status_code=400,
                ) from exc
            if target.is_file():
                try:
                    lines = target.read_text(encoding="utf-8").splitlines()
                    start = max((node.start_line or 1) - 1, 0)
                    end = min(node.end_line or start + 1, len(lines))
                    source = "\n".join(lines[start:end])
                except (OSError, UnicodeError):
                    pass
        return SourceData(
            node_id=node.id,
            file_path=node.file_path,
            start_line=node.start_line,
            end_line=node.end_line,
            source=source,
        )

    def relation_detail(
        self,
        *,
        project_id: str,
        relation_id: str,
    ) -> RelationDetailData:
        _, revision_id = self._active_project(project_id)
        relation = self.graphs.get_relation(
            project_id=project_id,
            revision_id=revision_id,
            relation_id=relation_id,
        )
        if not relation:
            raise AppException(
                code="RELATION_NOT_FOUND",
                message="关系不存在",
                status_code=404,
            )
        nodes = self.graphs.nodes_by_ids(
            project_id=project_id,
            revision_id=revision_id,
            node_ids={relation.source_node_id, relation.target_node_id},
        )
        by_id = {node.id: node for node in nodes}
        return RelationDetailData(
            **self._edge_data(relation).model_dump(),
            source_node=self._node_data(by_id[relation.source_node_id]),
            target_node=self._node_data(by_id[relation.target_node_id]),
        )

    def _one_hop_graph(
        self,
        *,
        project_id: str,
        revision_id: str,
        roots: list[CodeNode],
        endpoint_ids: list[str],
        include_lower_confidence: bool,
    ) -> GraphData:
        confidences = self._confidences(include_lower_confidence)
        root_ids = {root.id for root in roots}
        edges = self.graphs.outgoing(
            project_id=project_id,
            revision_id=revision_id,
            node_ids=root_ids,
            confidences=confidences,
        )
        target_ids = {edge.target_node_id for edge in edges}
        targets = self.graphs.nodes_by_ids(
            project_id=project_id,
            revision_id=revision_id,
            node_ids=target_ids,
        )
        entry_ids_by_node: dict[str, set[str]] = defaultdict(set)
        entry_ids_by_edge: dict[str, set[str]] = defaultdict(set)
        root_to_endpoint = {
            root.id: endpoint_id
            for root, endpoint_id in zip(roots, endpoint_ids, strict=True)
        }
        for root in roots:
            entry_ids_by_node[root.id].add(root_to_endpoint[root.id])
        for edge in edges:
            endpoint_id = root_to_endpoint.get(edge.source_node_id)
            if endpoint_id:
                entry_ids_by_edge[edge.id].add(endpoint_id)
                entry_ids_by_node[edge.target_node_id].add(endpoint_id)
        return self._serialize_graph(
            project_id=project_id,
            revision_id=revision_id,
            roots=[root.id for root in roots],
            nodes=[*roots, *targets],
            edges=edges,
            entry_ids_by_node=entry_ids_by_node,
            entry_ids_by_edge=entry_ids_by_edge,
            depth_by_node={
                **{root.id: 0 for root in roots},
                **{target.id: 1 for target in targets},
            },
            confidences=confidences,
        )

    def _multi_hop_graph(
        self,
        *,
        project_id: str,
        revision_id: str,
        roots: list[CodeNode],
        endpoint_ids: list[str],
        include_lower_confidence: bool,
        depth: int,
        max_nodes: int = 600,
    ) -> GraphData:
        confidences = self._confidences(include_lower_confidence)
        node_ids = {root.id for root in roots}
        edges_by_id: dict[str, CodeRelation] = {}
        entry_ids_by_node: dict[str, set[str]] = defaultdict(set)
        entry_ids_by_edge: dict[str, set[str]] = defaultdict(set)
        depth_by_node = {root.id: 0 for root in roots}
        truncated = False

        for root, endpoint_id in zip(roots, endpoint_ids, strict=True):
            entry_ids_by_node[root.id].add(endpoint_id)
            seen_for_entry = {root.id}
            frontier = {root.id}
            for current_depth in range(depth):
                if not frontier:
                    break
                outgoing = self.graphs.outgoing(
                    project_id=project_id,
                    revision_id=revision_id,
                    node_ids=frontier,
                    confidences=confidences,
                )
                next_frontier: set[str] = set()
                for edge in outgoing:
                    target_id = edge.target_node_id
                    if target_id not in node_ids and len(node_ids) >= max_nodes:
                        truncated = True
                        continue
                    node_ids.add(target_id)
                    edges_by_id[edge.id] = edge
                    entry_ids_by_edge[edge.id].add(endpoint_id)
                    entry_ids_by_node[target_id].add(endpoint_id)
                    depth_by_node[target_id] = min(
                        depth_by_node.get(target_id, current_depth + 1),
                        current_depth + 1,
                    )
                    if target_id not in seen_for_entry:
                        seen_for_entry.add(target_id)
                        next_frontier.add(target_id)
                frontier = next_frontier

        nodes = self.graphs.nodes_by_ids(
            project_id=project_id,
            revision_id=revision_id,
            node_ids=node_ids,
        )
        return self._serialize_graph(
            project_id=project_id,
            revision_id=revision_id,
            roots=[root.id for root in roots],
            nodes=nodes,
            edges=list(edges_by_id.values()),
            entry_ids_by_node=entry_ids_by_node,
            entry_ids_by_edge=entry_ids_by_edge,
            depth_by_node=depth_by_node,
            confidences=confidences,
            truncated=truncated,
        )

    def _serialize_graph(
        self,
        *,
        project_id: str,
        revision_id: str,
        roots: list[str],
        nodes: list[CodeNode],
        edges: list[CodeRelation],
        entry_ids_by_node: dict[str, set[str]],
        entry_ids_by_edge: dict[str, set[str]],
        depth_by_node: dict[str, int],
        confidences: set[str],
        truncated: bool = False,
    ) -> GraphData:
        unique_nodes = {node.id: node for node in nodes}
        graph = nx.DiGraph()
        graph.add_nodes_from(unique_nodes)
        graph.add_edges_from(
            (edge.source_node_id, edge.target_node_id)
            for edge in edges
            if edge.source_node_id in unique_nodes
            and edge.target_node_id in unique_nodes
        )
        computed_depths = dict(depth_by_node)
        for root in roots:
            if root not in graph:
                continue
            for node_id, distance in nx.single_source_shortest_path_length(
                graph,
                root,
            ).items():
                computed_depths[node_id] = min(
                    computed_depths.get(node_id, distance),
                    distance,
                )
        child_edges = self.graphs.outgoing(
            project_id=project_id,
            revision_id=revision_id,
            node_ids=set(unique_nodes),
            confidences=confidences,
        )
        counts: dict[str, int] = defaultdict(int)
        for edge in child_edges:
            counts[edge.source_node_id] += 1
        node_data: list[GraphNodeData] = []
        for node in unique_nodes.values():
            entries = sorted(entry_ids_by_node.get(node.id, set()))
            node_data.append(
                self._node_data(
                    node,
                    child_count=counts[node.id],
                    depth=computed_depths.get(node.id, 0),
                    entry_endpoint_ids=entries,
                    shared=len(entries) > 1,
                )
            )
        edge_data = [
            self._edge_data(
                edge,
                entry_endpoint_ids=sorted(entry_ids_by_edge.get(edge.id, set())),
            )
            for edge in {edge.id: edge for edge in edges}.values()
        ]
        return GraphData(
            project_id=project_id,
            scan_revision_id=revision_id,
            roots=roots,
            nodes=node_data,
            edges=edge_data,
            meta=GraphMeta(
                node_count=len(node_data),
                edge_count=len(edge_data),
                truncated=truncated,
            ),
        )

    @staticmethod
    def _node_data(
        node: CodeNode,
        *,
        child_count: int = 0,
        depth: int = 0,
        entry_endpoint_ids: list[str] | None = None,
        shared: bool = False,
    ) -> GraphNodeData:
        return GraphNodeData(
            id=node.id,
            type=node.node_type,
            name=node.name,
            qualified_name=node.qualified_name,
            module_name=node.module_name,
            file_path=node.file_path,
            start_line=node.start_line,
            end_line=node.end_line,
            signature=node.signature,
            has_children=child_count > 0,
            child_count=child_count,
            depth=depth,
            entry_endpoint_ids=entry_endpoint_ids or [],
            shared=shared,
            metadata=node.extra_metadata,
        )

    @staticmethod
    def _edge_data(
        edge: CodeRelation,
        *,
        entry_endpoint_ids: list[str] | None = None,
    ) -> GraphEdgeData:
        return GraphEdgeData(
            id=edge.id,
            source=edge.source_node_id,
            target=edge.target_node_id,
            relation_type=edge.relation_type,
            confidence=edge.confidence,
            file_path=edge.file_path,
            line_number=edge.line_number,
            column_number=edge.column_number,
            evidence=edge.evidence,
            entry_endpoint_ids=entry_endpoint_ids or [],
            metadata=edge.extra_metadata,
        )

    def _active_project(self, project_id: str):
        project = self.projects.get(project_id)
        if not project:
            raise AppException(
                code="PROJECT_NOT_FOUND",
                message="项目不存在",
                status_code=404,
            )
        if not project.active_revision_id:
            raise AppException(
                code="PROJECT_NOT_SCANNED",
                message="项目尚未完成扫描",
                status_code=409,
            )
        return project, project.active_revision_id

    def _endpoint(
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
                message="接口不存在",
                status_code=404,
            )
        return endpoint

    def _node(self, project_id: str, revision_id: str, node_id: str) -> CodeNode:
        node = self.graphs.get_node(
            project_id=project_id,
            revision_id=revision_id,
            node_id=node_id,
        )
        if not node:
            raise AppException(
                code="NODE_NOT_FOUND",
                message="节点不存在",
                status_code=404,
            )
        return node

    @staticmethod
    def _confidences(include_lower_confidence: bool) -> set[str]:
        return ALL_CONFIDENCES if include_lower_confidence else DEFAULT_CONFIDENCES
