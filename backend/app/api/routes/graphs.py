from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.graph import (
    CombinedGraphRequest,
    GraphResponse,
    NodeDetailResponse,
    RelationDetailResponse,
    SourceResponse,
)
from app.services.graph_service import GraphService

router = APIRouter(prefix="/projects")


@router.get(
    "/{project_id}/endpoints/{endpoint_id}/graph",
    response_model=GraphResponse,
    summary="加载接口第一层拓扑",
)
def endpoint_graph(
    project_id: str,
    endpoint_id: str,
    session: Annotated[Session, Depends(get_db)],
    include_lower_confidence: Annotated[
        bool, Query(alias="includeLowerConfidence")
    ] = False,
    depth: Annotated[int, Query(ge=1, le=8)] = 1,
) -> GraphResponse:
    data = GraphService(session).endpoint_graph(
        project_id=project_id,
        endpoint_id=endpoint_id,
        include_lower_confidence=include_lower_confidence,
        depth=depth,
    )
    return GraphResponse(data=data)


@router.post(
    "/{project_id}/graph/combined",
    response_model=GraphResponse,
    summary="合并多个接口的第一层拓扑",
)
def combined_graph(
    project_id: str,
    payload: CombinedGraphRequest,
    session: Annotated[Session, Depends(get_db)],
) -> GraphResponse:
    data = GraphService(session).combined_graph(
        project_id=project_id,
        endpoint_ids=payload.endpoint_ids,
        include_lower_confidence=payload.include_lower_confidence,
        depth=payload.depth,
    )
    return GraphResponse(data=data)


@router.get(
    "/{project_id}/nodes/{node_id}/children",
    response_model=GraphResponse,
    summary="按需加载节点下一层",
)
def node_children(
    project_id: str,
    node_id: str,
    session: Annotated[Session, Depends(get_db)],
    include_lower_confidence: Annotated[
        bool, Query(alias="includeLowerConfidence")
    ] = False,
) -> GraphResponse:
    data = GraphService(session).neighbors(
        project_id=project_id,
        node_id=node_id,
        direction="downstream",
        include_lower_confidence=include_lower_confidence,
    )
    return GraphResponse(data=data)


@router.get(
    "/{project_id}/nodes/{node_id}/upstream",
    response_model=GraphResponse,
    summary="查询节点上游",
)
def node_upstream(
    project_id: str,
    node_id: str,
    session: Annotated[Session, Depends(get_db)],
    include_lower_confidence: Annotated[
        bool, Query(alias="includeLowerConfidence")
    ] = False,
) -> GraphResponse:
    data = GraphService(session).neighbors(
        project_id=project_id,
        node_id=node_id,
        direction="upstream",
        include_lower_confidence=include_lower_confidence,
    )
    return GraphResponse(data=data)


@router.get(
    "/{project_id}/nodes/{node_id}/downstream",
    response_model=GraphResponse,
    summary="查询节点下游",
)
def node_downstream(
    project_id: str,
    node_id: str,
    session: Annotated[Session, Depends(get_db)],
    include_lower_confidence: Annotated[
        bool, Query(alias="includeLowerConfidence")
    ] = False,
) -> GraphResponse:
    return node_children(
        project_id,
        node_id,
        session,
        include_lower_confidence,
    )


@router.get(
    "/{project_id}/nodes/{node_id}",
    response_model=NodeDetailResponse,
    summary="查询节点详情",
)
def node_detail(
    project_id: str,
    node_id: str,
    session: Annotated[Session, Depends(get_db)],
) -> NodeDetailResponse:
    return NodeDetailResponse(
        data=GraphService(session).node_detail(
            project_id=project_id,
            node_id=node_id,
        )
    )


@router.get(
    "/{project_id}/nodes/{node_id}/source",
    response_model=SourceResponse,
    summary="查询节点源码",
)
def node_source(
    project_id: str,
    node_id: str,
    session: Annotated[Session, Depends(get_db)],
) -> SourceResponse:
    return SourceResponse(
        data=GraphService(session).source(
            project_id=project_id,
            node_id=node_id,
        )
    )


@router.get(
    "/{project_id}/relations/{relation_id}",
    response_model=RelationDetailResponse,
    summary="查询关系及代码证据",
)
def relation_detail(
    project_id: str,
    relation_id: str,
    session: Annotated[Session, Depends(get_db)],
) -> RelationDetailResponse:
    return RelationDetailResponse(
        data=GraphService(session).relation_detail(
            project_id=project_id,
            relation_id=relation_id,
        )
    )
