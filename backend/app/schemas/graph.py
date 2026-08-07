from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.schemas.common import ApiModel

Confidence = Literal["CONFIRMED", "HIGH", "MEDIUM", "LOW"]


class GraphNodeData(ApiModel):
    id: str
    type: str
    name: str
    qualified_name: str
    module_name: str | None
    file_path: str | None
    start_line: int | None
    end_line: int | None
    signature: str | None
    loaded: bool = False
    expanded: bool = False
    has_children: bool = False
    child_count: int = 0
    depth: int = 0
    entry_endpoint_ids: list[str] = Field(default_factory=list)
    shared: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeData(ApiModel):
    id: str
    source: str
    target: str
    relation_type: str
    confidence: Confidence
    file_path: str | None
    line_number: int | None
    column_number: int | None
    evidence: str | None
    entry_endpoint_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphMeta(ApiModel):
    node_count: int
    edge_count: int
    truncated: bool = False


class GraphData(ApiModel):
    project_id: str
    scan_revision_id: str
    roots: list[str]
    nodes: list[GraphNodeData]
    edges: list[GraphEdgeData]
    meta: GraphMeta


class GraphResponse(ApiModel):
    data: GraphData


class CombinedGraphRequest(ApiModel):
    endpoint_ids: list[str] = Field(min_length=1, max_length=50)
    include_lower_confidence: bool = False
    depth: int = Field(default=1, ge=1, le=8)


class NodeDetailData(GraphNodeData):
    source_excerpt: str | None
    upstream: list[GraphEdgeData]
    downstream: list[GraphEdgeData]


class NodeDetailResponse(ApiModel):
    data: NodeDetailData


class SourceData(ApiModel):
    node_id: str
    file_path: str | None
    start_line: int | None
    end_line: int | None
    source: str | None


class SourceResponse(ApiModel):
    data: SourceData


class RelationDetailData(GraphEdgeData):
    source_node: GraphNodeData
    target_node: GraphNodeData


class RelationDetailResponse(ApiModel):
    data: RelationDetailData
