from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import ConfigDict, Field

from app.schemas.common import ApiModel


class StrictAIModel(ApiModel):
    model_config = ConfigDict(
        alias_generator=lambda value: "".join(
            word.capitalize() if index else word
            for index, word in enumerate(value.split("_"))
        ),
        populate_by_name=True,
        extra="forbid",
    )


class BusinessFlowStep(StrictAIModel):
    step: int
    title: str
    description: str
    business_meaning: str
    node_ids: list[str] = Field(default_factory=list)


class BusinessRule(StrictAIModel):
    rule: str
    reason: str
    failure_result: str
    node_ids: list[str] = Field(default_factory=list)


class StateChange(StrictAIModel):
    business_object: str
    before: str
    after: str
    node_ids: list[str] = Field(default_factory=list)


class BusinessDataFlow(StrictAIModel):
    inputs: list[str] = Field(default_factory=list)
    reads: list[str] = Field(default_factory=list)
    changes: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)


class FailureFlow(StrictAIModel):
    scenario: str
    reason: str
    business_impact: str
    node_ids: list[str] = Field(default_factory=list)


class CoreBusinessObject(StrictAIModel):
    name: str
    role: str


class KeyBusinessNode(StrictAIModel):
    name: str
    business_importance: str
    reason: str
    node_ids: list[str] = Field(default_factory=list)


class ProcessPosition(StrictAIModel):
    position: Literal["START", "MIDDLE", "END", "INDEPENDENT", "UNKNOWN"]
    description: str


class BusinessRelatedEndpoint(StrictAIModel):
    endpoint_id: str
    relationship: str
    business_reason: str


class BusinessRisk(StrictAIModel):
    title: str
    description: str
    level: Literal["HIGH", "MEDIUM", "LOW"]
    node_ids: list[str] = Field(default_factory=list)


class TechnicalReference(StrictAIModel):
    entry: str
    core_methods: list[str] = Field(default_factory=list)
    data_access: list[str] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)


class AIChainAnalysis(StrictAIModel):
    business_summary: str
    business_scenario: str
    business_flow: list[BusinessFlowStep] = Field(default_factory=list)
    business_rules: list[BusinessRule] = Field(default_factory=list)
    state_changes: list[StateChange] = Field(default_factory=list)
    business_data_flow: BusinessDataFlow
    normal_flow: list[str] = Field(default_factory=list)
    failure_flows: list[FailureFlow] = Field(default_factory=list)
    core_business_objects: list[CoreBusinessObject] = Field(default_factory=list)
    key_business_nodes: list[KeyBusinessNode] = Field(default_factory=list)
    process_position: ProcessPosition
    related_endpoints: list[BusinessRelatedEndpoint] = Field(default_factory=list)
    business_risks: list[BusinessRisk] = Field(default_factory=list)
    technical_reference: TechnicalReference


class EndpointContext(StrictAIModel):
    id: str
    http_method: str
    path: str
    function_name: str
    qualified_name: str
    module_name: str
    file_path: str
    start_line: int
    end_line: int
    summary: str | None = None
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    response_type: str | None = None
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodeContext(StrictAIModel):
    id: str
    node_type: str
    name: str
    qualified_name: str
    module_name: str | None = None
    file_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    signature: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EdgeContext(StrictAIModel):
    id: str
    source: str
    target: str
    relation_type: str
    confidence: str
    file_path: str | None = None
    line_number: int | None = None
    evidence: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceSnippet(StrictAIModel):
    evidence_id: str
    node_id: str
    file_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    content: str
    truncated: bool = False


class StaticCondition(StrictAIModel):
    node_id: str
    evidence_id: str
    expression: str
    line_number: int | None = None
    kind: str


class StaticDataOperation(StrictAIModel):
    node_id: str
    resource: str
    operation: str
    method_name: str


class StaticExternalCall(StrictAIModel):
    node_id: str
    dependency_type: str
    name: str


class ContextMeta(StrictAIModel):
    project_id: str
    scan_revision_id: str
    scope_type: str
    depth: int
    graph_version: str
    truncated: bool = False
    omitted_nodes: int = 0
    omitted_edges: int = 0


class AllowedReferences(StrictAIModel):
    endpoint_ids: list[str]
    node_ids: list[str]
    edge_ids: list[str]
    evidence_ids: list[str]


class AIAnalysisContext(StrictAIModel):
    context_meta: ContextMeta
    endpoints: list[EndpointContext]
    nodes: list[NodeContext]
    edges: list[EdgeContext]
    source_snippets: list[SourceSnippet]
    conditions: list[StaticCondition]
    data_operations: list[StaticDataOperation]
    external_calls: list[StaticExternalCall]
    related_endpoint_candidates: list[EndpointContext]
    allowed_references: AllowedReferences


class AIAnalysisRequest(StrictAIModel):
    depth: int = Field(default=5, ge=1, le=8)
    include_source: bool = True
    include_medium_confidence: bool = False
    force_regenerate: bool = False


class AICombinedAnalysisRequest(AIAnalysisRequest):
    endpoint_ids: list[str] = Field(min_length=2, max_length=10)


class AIAnalysisData(StrictAIModel):
    analysis_id: str
    project_id: str
    scan_revision_id: str
    scope_type: str
    status: str
    provider: str
    model: str
    cached: bool
    stale: bool
    result: AIChainAnalysis | None = None
    error_message: str | None = None
    token_usage: dict[str, Any] = Field(default_factory=dict)
    invalid_reference_count: int = 0
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class AIAnalysisResponse(StrictAIModel):
    data: AIAnalysisData
