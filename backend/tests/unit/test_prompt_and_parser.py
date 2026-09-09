import pytest

from app.llm.exceptions import AIAnalysisError
from app.llm.response_parser import ResponseParser
from app.prompts.analysis import SYSTEM_PROMPT
from app.schemas.ai_analysis import AIAnalysisContext


def test_prompt_keeps_evidence_and_schema_constraints():
    assert "CONTEXT_JSON" in SYSTEM_PROMPT
    assert "OUTPUT_SCHEMA" in SYSTEM_PROMPT
    assert "allowed_references" in SYSTEM_PROMPT


def test_malformed_json_has_safe_error():
    with pytest.raises(AIAnalysisError):
        ResponseParser._json_payload("not json")


def test_untrusted_reference_shapes_are_rejected():
    # Only the reference validator needs this context field.
    from app.schemas.ai_analysis import AllowedReferences

    context = AIAnalysisContext.model_construct(
        allowed_references=AllowedReferences(
            node_ids=["allowed"], edge_ids=[], endpoint_ids=[], evidence_ids=[]
        )
    )
    payload = {
        "business_flow": [{"node_ids": ["allowed", {}, ["nested"], "invented"]}],
        "related_endpoints": [{"endpoint_id": {}}],
    }
    count = ResponseParser()._clean_references(payload, context)
    assert count == 4
    assert payload["business_flow"][0]["node_ids"] == ["allowed"]
