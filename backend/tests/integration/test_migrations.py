from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.core.config import settings


def test_migration_upgrade_downgrade(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'migration.db'}")
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    command.upgrade(config, "20260807_0005")
    engine = create_engine(settings.database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO projects "
                "(id,name,root_path,language,framework,scan_status,total_files,"
                "total_endpoints,created_at,updated_at) "
                "VALUES ('p','retained','/sample','python','fastapi','READY',1,0,"
                "CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO scan_tasks "
                "(id,project_id,revision_id,status,stage,progress,discovered_files,processed_files,"
                "skipped_files,failed_files,error_summary,created_at) "
                "VALUES ('s','p','r','SUCCEEDED','COMPLETED',100,1,1,0,0,'[]',CURRENT_TIMESTAMP)"
            )
        )
    engine.dispose()
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT status FROM scan_tasks WHERE id='s'")) == "SUCCEEDED"
        assert connection.scalar(text("SELECT updated_at FROM scan_tasks WHERE id='s'"))
        assert {"created_at", "updated_at"} <= {
            column["name"] for column in inspect(connection).get_columns("endpoint_nodes")
        }
    engine.dispose()
    command.downgrade(config, "20260807_0005")
    command.upgrade(config, "head")
