from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.ai_analysis import AIAnalysis
from app.models.project import utc_now


class AIAnalysisRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, analysis: AIAnalysis) -> AIAnalysis:
        self.session.add(analysis)
        self.session.flush()
        return analysis

    def get(self, analysis_id: str) -> AIAnalysis | None:
        return self.session.get(AIAnalysis, analysis_id)

    def get_by_cache_key(self, cache_key: str) -> AIAnalysis | None:
        return self.session.scalar(
            select(AIAnalysis).where(AIAnalysis.cache_key == cache_key)
        )

    def mark_project_stale(
        self,
        *,
        project_id: str,
        active_revision_id: str,
    ) -> int:
        result = self.session.execute(
            update(AIAnalysis)
            .where(
                AIAnalysis.project_id == project_id,
                AIAnalysis.scan_revision_id != active_revision_id,
                AIAnalysis.status == "COMPLETED",
            )
            .values(status="STALE", stale_at=utc_now())
        )
        return int(result.rowcount or 0)
