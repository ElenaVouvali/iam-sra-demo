from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from iam_sra.readiness_score import ReadinessScore, assign_score, current_score


def session():
    return SimpleNamespace(state='final', pending=None, final_readiness={'coverage': 'partial'},
        events=[{'id':'R1_1', 'active':True, 'context':'original', 'text':'Noise affects rest.', 'records':[]}])


class Client:
    def assign(self, payload):
        return ReadinessScore(crl=2, explanation='Recognises potential impacts.', evidence_ids=['R1_1'])


def test_score_invalidation_and_scope():
    s = session()
    assign_score(s, Client())
    assert current_score(s)['crl'] == 2
    assert current_score(s)['srl'] is None
    s.events[0]['text'] = 'Corrected answer.'
    assert current_score(s) is None


def test_unfinished_interview_cannot_be_scored():
    s = session(); s.state = 'review'
    with pytest.raises(ValueError): assign_score(s, Client())


def test_score_range():
    with pytest.raises(ValidationError):
        ReadinessScore(crl=10, explanation='Unsupported.', evidence_ids=['R1_1'])


def test_privacy_gate_before_scoring():
    s = session(); s.events[0]['text'] = 'My PIN is 1234'
    from iam_sra.privacy import PrivacyError
    with pytest.raises(PrivacyError): assign_score(s, Client())


@pytest.mark.parametrize('wire', [
    '{"crl":3,"explanation":"Understanding.","evidence_ids":["invented"]}',
    '{"crl":3,"explanation":"Understanding.","evidence_ids":[]}',
])
def test_live_response_requires_existing_support(monkeypatch, wire):
    from iam_sra.readiness_score import WorkbookScoreClient, score_input
    def request(self, http, stage, system, payload, schema, validator):
        return validator(wire)
    monkeypatch.setattr(WorkbookScoreClient, '_request', request)
    with pytest.raises(ValueError): WorkbookScoreClient().assign(score_input(session()))
