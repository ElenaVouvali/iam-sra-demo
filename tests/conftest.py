"""Existing regressions use a declared synthetic detector double, not live Presidio.

Privacy screening is mandatory. Detector integration is tested separately when the
pinned packages/model are installed. These doubles prove flow, not NLP coverage.
"""
import re
import pytest
from iam_sra.privacy import Finding


class SyntheticDetector:
    def analyze(self, *, text, **kwargs):
        found = []
        patterns = {
            'EMAIL_ADDRESS': r'\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b',
            'PHONE_NUMBER': r'(?<!\w)(?:\+1[ -]?)?\(?202\)?[ -]?555[ -]?01\d{2}(?!\w)',
            'PERSON': r'\b(?:Alice Example|Morgan Testperson)\b',
            'CREDIT_CARD': r'\b4111[ -]?1111[ -]?1111[ -]?1111\b',
            'IBAN_CODE': r'\bGB82[ ]?WEST[ ]?1234[ ]?5698[ ]?7654[ ]?32\b',
        }
        for kind, pattern in patterns.items():
            found.extend(Finding(kind,m.start(),m.end()) for m in re.finditer(pattern,text))
        return found


@pytest.fixture(autouse=True)
def synthetic_privacy_detector(monkeypatch, request):
    if request.node.get_closest_marker('presidio_live'): return
    monkeypatch.setattr('iam_sra.privacy.detector', lambda:SyntheticDetector())
