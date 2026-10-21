"""Versioned transport contracts; no controller objects cross this boundary."""
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, UUID4

API_VERSION = '1.1.0'


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Empty(Strict):
    pass


class Context(Strict):
    perspective: str = Field(max_length=60)
    role: str = Field(max_length=80)
    city: str = Field(max_length=60)
    place: str = Field(default='', max_length=80)
    function: str = Field(default='', max_length=240)


class Answer(Strict):
    text: str = Field(default='', max_length=6000)
    control: Literal['answer', 'skip', 'unsure', 'decline'] = 'answer'


class Correction(Strict):
    text: str = Field(min_length=1, max_length=1500)


class Information(Strict):
    question: str = Field(min_length=1, max_length=300)


class Scenario(Strict):
    scenario_id: str = Field(min_length=1, max_length=100)


class Exposure(Strict):
    exposure_id: str = Field(min_length=1, max_length=100)


class EditAnswer(Strict):
    stage: Literal['general', 'scenario']
    event_id: str = Field(min_length=1, max_length=100)


class Preview(Strict):
    preview_id: str = Field(min_length=32, max_length=64)


class IndicatorSelection(Strict):
    profile: Literal['citizen'] = 'citizen'
    indicator_ids: list[str] = Field(min_length=1, max_length=3)
    context: Literal['general_understanding', 'illustrative_proposal', 'actual_experience']
    use_case: str = Field(default='', max_length=240)
    reuse_answers: dict[str, list[str]] = Field(default_factory=dict)


class IndicatorAnswer(Strict):
    text: str = Field(default='', max_length=2000)
    control: Literal['answer', 'skip', 'unsure', 'decline'] = 'answer'


class IndicatorReview(Strict):
    choice: Literal['endorse', 'select', 'unsure', 'decline']
    revision: int = Field(ge=0)
    statement_id: str | None = Field(default=None, max_length=100)
    explanation: str = Field(default='', max_length=600)


class IndicatorNext(Strict):
    indicator_id: str = Field(max_length=100)


class IndicatorEdit(Strict):
    event_id: str = Field(max_length=100)
    mode: Literal['answer', 'interpretation'] = 'answer'


ACTION_DATA = {
    'select_indicators': IndicatorSelection, 'indicator_answer': IndicatorAnswer,
    'indicator_correct': Correction, 'indicator_review': IndicatorReview,
    'indicator_next': IndicatorNext, 'indicator_edit': IndicatorEdit,
    **{key: Empty for key in ('indicator_confirm', 'indicator_finish', 'indicator_suggest')},
    'set_context': Context, 'answer': Answer,
    'correct_interpretation': Correction, 'ask_information': Information,
    'select_scenario': Scenario, 'acknowledge': Exposure, 'edit_answer': EditAnswer,
    'confirm_cleaned': Preview,
    **{key: Empty for key in (
        'confirm_answer', 'finish', 'confirm_general', 'accept_scenario',
        'decline_scenario', 'start_reflection', 'confirm_final', 'back',
        'edit_context', 'provisional_estimate', 'reset', 'discard_preview',
    )},
}


class ActionRequest(Strict):
    action: str = Field(min_length=1, max_length=40)
    expected_version: int = Field(ge=0)
    # Parse JSON UUIDs explicitly; never accept arbitrary text as a retry key.
    request_id: UUID4
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def parse(cls, raw):
        import json
        value = cls.model_validate_json(json.dumps(raw))
        if value.action not in ACTION_DATA:
            raise ValueError('Unknown action')
        data = ACTION_DATA[value.action].model_validate(value.data).model_dump()
        return value, data


class SessionView(Strict):
    api_version: str = API_VERSION
    id: str
    version: int
    state: str
    stage: str
    allowed_actions: list[str]
    question: dict[str, Any] | None
    pending: dict[str, Any] | None
    respondent: dict[str, Any] | None
    scenario: dict[str, Any] | None
    scenarios: list[dict[str, Any]]
    information: list[dict[str, Any]]
    answers: list[dict[str, Any]]
    summary: dict[str, Any]
    evidence: list[dict[str, Any]]
    qualitative_assessment: dict[str, Any]
    results: dict[str, Any]
    privacy_notice: str
    indicator_assessment: dict[str, Any] = Field(default_factory=dict)
    busy_job: str | None = None
    preview: dict[str, Any] | None = None
    retry_draft: dict[str, Any] | None = None
    returned_text: str | None = None


class JobView(Strict):
    api_version: str = API_VERSION
    id: str
    session_id: str
    status: Literal['queued', 'running', 'completed', 'failed', 'cancelled']
    version: int
    error: dict[str, Any] | None = None
