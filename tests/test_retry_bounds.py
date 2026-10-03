from pydantic import ValidationError
from iam_sra.schemas import ScoreDecision
from iam_sra.llm_client import schema_error


def test_model_rule_error_includes_actionable_reason():
    from iam_sra.schemas import Concern
    from iam_sra.settings import CONCERNS
    facet=CONCERNS['noise']['facets'][0]
    try:
        Concern.model_validate(dict(concern_id='noise', status='assessed',
            position='opposed', score=3, facets=[facet,facet],
            excerpts=['private citizen text'], rationale='Explicit objection'))
    except ValidationError as exc:
        message=str(schema_error(exc))
        assert 'Duplicate facet' in message
        assert 'private citizen text' not in message
    else:
        raise AssertionError('Duplicate facets must still be rejected')


def test_excess_evidence_retry_names_limit_without_echoing_text():
    try:
        ScoreDecision.model_validate(dict(concern_id='noise', status='assessed',
            decision='retained', score=3, excerpts=['private text'] * 4))
    except ValidationError as exc:
        message = str(schema_error(exc))
        assert 'excerpts:too_long' in message
        assert 'at most 3 items' in message
        assert 'select the most relevant evidence IDs' in message
        assert 'private text' not in message
    else:
        raise AssertionError('Excess evidence must still be rejected')
