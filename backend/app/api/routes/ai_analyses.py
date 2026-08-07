from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.ai_service import AIAnalysisService
from app.ai.schemas import (
    AIAnalysisRequest,
    AIAnalysisResponse,
    AICombinedAnalysisRequest,
)
from app.core.database import get_db

router = APIRouter()


@router.post(
    "/projects/{project_id}/endpoints/{endpoint_id}/ai-analysis",
    response_model=AIAnalysisResponse,
    summary="生成单接口 AI 链路分析",
)
def analyze_endpoint(
    project_id: str,
    endpoint_id: str,
    payload: AIAnalysisRequest,
    session: Annotated[Session, Depends(get_db)],
) -> AIAnalysisResponse:
    service = AIAnalysisService(session)
    analysis, cached = service.analyze_endpoints(
        project_id=project_id,
        endpoint_ids=[endpoint_id],
        request=payload,
    )
    return AIAnalysisResponse(data=service.serialize(analysis, cached=cached))


@router.post(
    "/projects/{project_id}/endpoints/ai-combined-analysis",
    response_model=AIAnalysisResponse,
    summary="生成多接口联合 AI 链路分析",
)
def analyze_combined_endpoints(
    project_id: str,
    payload: AICombinedAnalysisRequest,
    session: Annotated[Session, Depends(get_db)],
) -> AIAnalysisResponse:
    service = AIAnalysisService(session)
    analysis, cached = service.analyze_endpoints(
        project_id=project_id,
        endpoint_ids=payload.endpoint_ids,
        request=payload,
    )
    return AIAnalysisResponse(data=service.serialize(analysis, cached=cached))


@router.post(
    "/projects/{project_id}/nodes/{node_id}/ai-impact-analysis",
    response_model=AIAnalysisResponse,
    summary="生成节点 AI 影响分析",
)
def analyze_node_impact(
    project_id: str,
    node_id: str,
    payload: AIAnalysisRequest,
    session: Annotated[Session, Depends(get_db)],
) -> AIAnalysisResponse:
    service = AIAnalysisService(session)
    analysis, cached = service.analyze_node(
        project_id=project_id,
        node_id=node_id,
        request=payload,
    )
    return AIAnalysisResponse(data=service.serialize(analysis, cached=cached))


@router.get(
    "/ai-analyses/{analysis_id}",
    response_model=AIAnalysisResponse,
    summary="查询 AI 分析结果",
)
def get_ai_analysis(
    analysis_id: str,
    session: Annotated[Session, Depends(get_db)],
) -> AIAnalysisResponse:
    service = AIAnalysisService(session)
    analysis = service.get(analysis_id)
    return AIAnalysisResponse(data=service.serialize(analysis, cached=True))


@router.post(
    "/ai-analyses/{analysis_id}/regenerate",
    response_model=AIAnalysisResponse,
    summary="重新生成 AI 分析",
)
def regenerate_ai_analysis(
    analysis_id: str,
    session: Annotated[Session, Depends(get_db)],
) -> AIAnalysisResponse:
    service = AIAnalysisService(session)
    analysis, cached = service.regenerate(analysis_id)
    return AIAnalysisResponse(data=service.serialize(analysis, cached=cached))
