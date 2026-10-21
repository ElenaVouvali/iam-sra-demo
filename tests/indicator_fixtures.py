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


def questionnaire(source=None):
    """Complete authored synthetic matrix; no partner questionnaire wording."""
    from iam_sra.questionnaire import VERSION, SCHEMA
    source = source or bank()
    profiles={'citizen':('CRL',17),'organisational':('ORL',12),'technical':('TRL',13)}
    probes=[{'id':f'{profile}-probe-{n}', 'profile':profile, 'text':'What remains unclear about {topic}?',
             'purpose':'clarification', 'ask_when':'Only when a relevant issue remains unresolved.',
             'origin':'newly_drafted','source_refs':[{'source_id':'v4','locator':'Synthetic source'}]}
            for profile,(_,count) in profiles.items() for n in range(count)]
    modules=[]
    for item in source['indicators']:
        for profile,(scale,_) in profiles.items():
            key=item['id']+'-'+scale.lower()
            questions=[{'id':key+f'-q{n:02d}','profile':profile,'indicator_id':item['id'],
                'text':f'Synthetic {profile} question {n} about issue {item["number"]}?',
                'purpose':'understanding' if n==1 else 'clarification','role':'opening' if n==1 else 'conditional_follow_up',
                'ask_when':'Relevant equivalent evidence is missing.' if n==1 else 'Only when unresolved and applicable.',
                'origin':'newly_drafted','source_refs':[{'source_id':'v4','locator':'Synthetic source'}]} for n in range(1,5 if profile=='citizen' else 4)]
            options=['Strongly disagree','Disagree','Neither agree nor disagree','Agree','Strongly agree','Not sure','Not applicable to my situation','Prefer not to answer']
            codes={'strongly_disagree':1,'disagree':2,'neither_agree_nor_disagree':3,'agree':4,'strongly_agree':5,'unsure':None,'not_applicable':None,'declined':None}
            modules.append({'id':key,'indicator_id':item['id'],'profile':profile,'scale':scale,'indicator_name':item['name'],
                'definition':item['definition'],'assessment_criterion':item['assessment_criteria'][profile]['text'],
                'definition_source':{'source_id':'v4','locator':'Synthetic definitions'},
                'criterion_source':{'source_id':'v4','locator':item['assessment_criteria'][profile]['source']['sheet']+'!'+item['assessment_criteria'][profile]['source']['cell']},'scope_note':'Synthetic scope, pending review.',
                'plain_topic':f'synthetic issue {item["number"]}',
                'anchors':[{'id':r['id'],'level':r['level'],'statement':r['statement'],'review_row_ref':r['review_row_id'],
                            'source_ref':{'source_id':'v4','locator':r['source']['sheet']+'!'+r['source']['cell']}} for r in source['statements'] if r['indicator_id']==item['id'] and r['profile']==profile],
                'questions':questions,'question_order':[q['id'] for q in questions],
                'shared_probe_ids':[p['id'] for p in probes if p['profile']==profile],
                'optional_likert_items':[{'id':key+'-l01','text':'Synthetic self-report item.', 'origin':'newly_drafted',
                    'source_refs':[{'source_id':'v4','locator':'Synthetic source'}], 'purpose':'self_report',
                    'response_type':'likert_5_with_non_substantive_options','options':options,'response_codes':codes}] if profile=='citizen' else []})
    return {'schema_version':SCHEMA,'questionnaire_version':VERSION,'status':'synthetic_fixture_only',
            'source_register':[{'id':'v4',**source['source']}],'modules':modules,'shared_probes':probes,
            'source_review_rows':[{'id':r['id'],'status':r['status'],'comment':r['comment']} for r in source['review_rows']],
            'protocol':{'sections':[{'id':f'section-{n//5+1}','indicator_ids':[f'indicator-{i:02d}' for i in range(n+1,n+6)]} for n in (0,5,10)]},
            'participant_introduction':'Synthetic configuration, not a real assessment.'}


def reading(answer, kind='reasoning', actuality='unspecified', actor='self', domain='IAM'):
    return {'meaning': 'You describe your position and reasoning.', 'observations': [{'quote': answer, 'kind': kind,
            'actor': actor, 'actuality': actuality, 'domain': domain}],
            'next_question_id':None,'follow_up_reason':'','answer_basis_quote':'','needs_answer_edit':False,'correction_notice':''}


def matching(statements, evidence, level=5, abstain=False):
    selected = next(s for s in statements if s['level'] == level)
    return {'assessments': [{'statement_id': s['id'], 'status': 'supported' if s == selected and not abstain else 'insufficient',
                            'evidence': [{'evidence_id': evidence[0]['evidence_id'], 'quote': evidence[0]['observations'][0]['quote']}] if s == selected and not abstain else []} for s in statements],
            'selected_statement_id': None if abstain else selected['id'], 'explanation': 'Synthetic fixture judgment; not live model inference.',
            'material_conflict': False, 'selection_unclear': abstain, 'gap': '',
            'alternative_statement_id':None,'alternative_distinction':''}


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
    session.indicators = IndicatorAssessment(bank(),questionnaire())
    return session


def scenario_cases():
    """Authored case cards for controller/browser tests; no private case text."""
    value=[]
    for n in range(1,7):
        value.append({'id':f'expansion-{n:02d}','title':f'Synthetic case {n}','version':'0.1.0',
            'scenario_bank_version':'2026-10-21-v0.1','type':'scenario','city':'other','locale':'en',
            'text':f'A synthetic illustrative situation {n}. No actual operations are established.',
            'unknowns':['Actual operations and responsibilities'],'source_status':'illustrative_story_in_source',
            'source_verification':'unverified_draft_adaptation','source_refs':[{'source_id':'missing','package_document':'synthetic-missing.pdf','package_sha256':'c'*64,'verification_status':'original_missing','locator':'Synthetic section'}],
            'source':{'document':'synthetic-scenarios.json','sha256':'b'*64,'version':'0.1.0','locator':f'case {n}'},
            'facts':{'current_operations':'not_established'},'illustrative_assumptions':['Hypothetical situation'],
            'applicability':{'perspectives':['personal','organisation','withheld'],'roles':['citizen','withheld','city_authority','research_academia']},
            'indicator_ids':[f'indicator-{i:02d}' for i in range(1,16)],'topic_ids':['noise'],
            'opening_question':'What issue remains unclear in this illustration?',
            'conditional_followup':{'text':'What further information would help?','ask_when':'Only if unresolved.'},
            'wording_origin':'newly_drafted','review_status':'draft_pending_review','approved_by':None,
            'situation_family':f'synthetic-{n}','derivation':'Authored synthetic illustration.','search_text':'synthetic illustrative context'})
    return value
