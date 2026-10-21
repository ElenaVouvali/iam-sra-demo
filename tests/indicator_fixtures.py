"""Small authored synthetic definitions and responses; never partner source text."""
from copy import deepcopy
from iam_sra.indicator_assessment import IndicatorAssessment
from iam_sra.indicator_client import POLICY


def bank():
    profiles = {'technical': 'TRL', 'organisational': 'ORL', 'citizen': 'CRL'}
    statements, rows, indicators = [], [], []
    citizen = ['A test citizen recognises the IAM issue.', 'A test citizen identifies potential effects of IAM.',
               'A test citizen explains the issue with reasons.', 'A test citizen expresses reasoned views in a discussion.',
               'A test citizen proposes justified safeguards.', 'A test citizen evaluates trade-offs through demonstrations.',
               'A test citizen contribution demonstrably changes a decision.', 'A test citizen uses established accountability channels.',
               'A test citizen sustains participation in governance.']
    for n in range(1, 16):
        key = f'indicator-{n:02d}'
        indicators.append({'id': key, 'number': n, 'name': f'Synthetic indicator {n}', 'definition': f'Synthetic issue {n}.',
                           'assessment_criteria': {p: {'text': f'Test criterion {n} for {p}',
                                                      'source': {'sheet': 'Synthetic criteria', 'cell': f'F{n+1}'}} for p in profiles}})
        for level in range(1, 10):
            row_id = f'{key}-level-{level}'
            rows.append({'id': row_id, 'indicator_id': key, 'level': level, 'status': 'To review', 'comment': '',
                         'source': {'sheet': 'Synthetic scales', 'row': n * 9 + level, 'status_cell': f'H{level}', 'comment_cell': f'I{level}'}})
            for profile, scale in profiles.items():
                statements.append({'id': f'{key}-{scale.lower()}-{level}', 'indicator_id': key, 'profile': profile,
                                   'scale': scale, 'level': level, 'statement': citizen[level-1] if profile == 'citizen' else f'Synthetic {scale} {level}',
                                   'source': {'sheet': 'Synthetic scales', 'cell': ('G' if profile == 'citizen' else 'E') + str(n*9+level)}, 'review_row_id': row_id})
    return {'schema_version': 'readiness-scale-bank-1.0.0', 'bank_version': 'fn-v4-1.0.0', 'status': 'draft_test_fixture',
            'source': {'document': 'synthetic-readiness.xlsx', 'sha256': 'a' * 64}, 'profiles': profiles, 'indicators': indicators,
            'statements': statements, 'review_rows': rows,
            'generic_scales': {scale: [{'level': n, 'description': f'Fixture label {n}. Synthetic generic description.'} for n in range(1, 10)] for scale in (*profiles.values(), 'SRL')}}


def reading(answer, kind='reasoning', actuality='unspecified', actor='self', domain='IAM'):
    return {'meaning': 'You describe your position and reasoning.', 'observations': [{'quote': answer, 'kind': kind,
            'actor': actor, 'actuality': actuality, 'domain': domain}]}


def matching(statements, evidence, level=5, abstain=False):
    selected = next(s for s in statements if s['level'] == level)
    return {'assessments': [{'statement_id': s['id'], 'status': 'supported' if s == selected and not abstain else 'insufficient',
                            'evidence': [{'evidence_id': evidence[0]['evidence_id'], 'quote': evidence[0]['observations'][0]['quote']}] if s == selected and not abstain else []} for s in statements],
            'selected_statement_id': None if abstain else selected['id'], 'explanation': 'Synthetic fixture judgment; not live model inference.',
            'material_conflict': False, 'selection_unclear': abstain, 'gap': ''}


class Client:
    def __init__(self, kind='condition', level=5, abstain=False):
        self.kind, self.level, self.abstain = kind, level, abstain
        self.calls = 0

    def interpret(self, indicator, scope, question, answer, feedback=''):
        self.calls += 1
        return reading(answer, self.kind)

    def match(self, indicator, scope, statements, evidence):
        self.calls += 1
        return matching(statements, evidence, self.level, self.abstain)


def engine():
    from iam_sra.conversation_session import ConversationSession
    from iam_sra.synthetic_runner import synthetic_collection
    session = ConversationSession(synthetic_collection())
    session.set_context('personal', 'citizen', 'madrid')
    session.finish(); session.confirm_general(); session.decline_scenario(); session.confirm_final()
    session.indicators = IndicatorAssessment(bank())
    return session
