"""Explicit test-only WSGI fixture for browser verification; never used by start-api.sh.

PYTHONPATH=src:tests .venv-api/bin/python -m gunicorn --workers 1 --threads 8 \
  --bind 127.0.0.1:8001 'api_browser_fixture:create_fixture()'
"""
import time
from iam_sra import privacy
from conftest import SyntheticDetector
from iam_sra.api import create_app
from iam_sra.api.adapter import ControllerAdapter
from iam_sra.api.service import AssessmentService
from iam_sra.baseline_client import MockBaselineClient
from iam_sra.conversation_session import ConversationSession
from iam_sra.conversation_benchmark import FixtureClient, FixtureComposer, load_cases
from iam_sra.synthetic_runner import synthetic_collection
from iam_sra.settings import ROOT
from iam_sra.assessment import AssessmentError
from iam_sra.citizen_score import empty_assessment
from iam_sra.indicator_assessment import IndicatorAssessment
from indicator_fixtures import bank, Client as IndicatorFixtureClient


class FixtureScore:
    def assign(self, payload):
        return empty_assessment('Synthetic fixture abstains; no live model judgement.')


class SlowFixture(FixtureClient):
    def extract_baseline(self, evidence, **kwargs):
        time.sleep(2 if any('simulate slow model' in value.lower() for value in evidence.values()) else .25)
        if any('simulate model failure' in value.lower() for value in evidence.values()):
            raise AssessmentError('Synthetic test failure.', code='transport')
        # A standalone privacy-preview journey uses empty authored claims, while
        # the complete authored meeting journey uses the exact fixture claims.
        try:
            return super().extract_baseline(evidence, **kwargs)
        except ValueError:
            return MockBaselineClient().extract_baseline(evidence, **kwargs)


def create_fixture():
    privacy.detector = lambda: SyntheticDetector()
    case = load_cases(ROOT / 'eval/conversation_meeting_cases_v2.json')['cases'][0]
    def make_engine():
        value = ConversationSession(synthetic_collection())
        value.indicators = IndicatorAssessment(bank())
        return value
    adapter = ControllerAdapter(
        engine_factory=make_engine,
        clients_factory=lambda engine: {'baseline': SlowFixture(case), 'planner': None,
                                        'information': FixtureComposer(), 'score': FixtureScore(),
                                        'indicator': IndicatorFixtureClient()},
        readiness=lambda: {'privacy': 'synthetic-detector-fixture', 'corpus': 'synthetic-corpus-fixture'})
    return create_app({'TESTING': True, 'SECRET_KEY': 'browser-fixture-only-not-a-deployment-secret'},
                      service=AssessmentService(adapter))
