import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize(
    "values",
    [
        {"ai_provider": "unknown"},
        {"ai_base_url": "http://localhost.evil.test/v1"},
        {"ai_base_url": "https://name:password@example.com/v1"},
        {"ai_provider": "openai-compatible", "ai_api_key": ""},
        {"max_scan_files": 0},
        {"ai_max_retries": -1},
        {"cors_origins": ["*"]},
        {"ai_timeout_seconds": 0},
    ],
)
def test_invalid_settings_fail_fast(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_settings_repr_hides_credentials():
    assert "secret-marker" not in repr(Settings(_env_file=None, ai_api_key="secret-marker"))
