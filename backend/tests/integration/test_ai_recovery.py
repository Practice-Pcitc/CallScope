from datetime import timedelta

from app.core.database import SessionLocal
from app.models.ai_analysis import AIAnalysis
from app.models.project import Project, utc_now
from app.services.ai_analysis_service import recover_ai_analyses


def test_restart_marks_pending_failed_and_expires_old_results():
    with SessionLocal() as session:
        project = Project(name="recovery", root_path="/synthetic")
        session.add(project)
        session.flush()
        records = []
        for key, created in (("pending", utc_now()), ("old", utc_now() - timedelta(days=40))):
            record = AIAnalysis(
                project_id=project.id,
                scan_revision_id="revision",
                scope_type="NODE_IMPACT",
                scope_key="node",
                provider="local",
                model="local",
                prompt_version="test",
                graph_version="test",
                depth=1,
                options={},
                context_hash=key,
                cache_key=key,
                status="ANALYZING",
                created_at=created,
            )
            session.add(record)
            records.append(record)
        session.commit()
        ids = [record.id for record in records]
    recover_ai_analyses()
    with SessionLocal() as session:
        assert session.get(AIAnalysis, ids[0]).status == "FAILED"
        assert session.get(AIAnalysis, ids[1]) is None
