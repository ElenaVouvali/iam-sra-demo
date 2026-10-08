"""Evidence-first mapping contracts; mocked outputs do not prove model accuracy."""
import json
import pytest
from iam_sra.issue_mapping import extract
from iam_sra.interpretation import EvidenceItem
from iam_sra.assessment import AssessmentError


@pytest.fixture(autouse=True)
def quotation_mapper_policy(monkeypatch):
    """These scripted clients exercise the quotation-based mapping contract."""
    from iam_sra import issue_mapping
    original_config=issue_mapping.config
    def policy(name):
        values=original_config(name)
        if name=='prompts':values['initial_mapping']='expressed_issue_then_facet'
        return values
    monkeypatch.setattr(issue_mapping,'config',policy)


@pytest.fixture(autouse=True)
def legacy_mapper_contract(monkeypatch):
    import iam_sra.issue_mapping as module
    original=module.config
    monkeypatch.setattr(module,'config',lambda n:{**original(n),'initial_mapping':'legacy_replay','initial_coverage_review':False} if n=='prompts' else original(n))


def evidence(words):
    return {r:EvidenceItem(id=r,text=t,context='original',source='citizen_original') for r,t in words.items()}


class Client:
    def __init__(self,nominations,quotes,decisions):
        self.last_settings={};self.nominations=nominations;self.quotes=quotes;self.decisions=decisions
    def _request(self,http,stage,system,user,schema,validator):
        if 'requested_passages' in user:raw={r:self.nominations[r] for r in user['requested_passages']}
        elif 'subject_grounding' in user:
            raw={n:n for n in user['subject_grounding']}
        elif 'candidate_subjects' in user:
            raw={n:'same_aspect' for n in user['candidate_subjects']}
        elif 'relevance_recheck' in user:
            raw={n:'facet_evaluation' if user['facet'] in self.decisions else 'other_facet_evaluation' for n in user['relevance_recheck']}
        elif 'relevance_check' in user:
            raw={n:user['facet'] in self.decisions for n in user['relevance_check']}
        elif 'balance_check' in user:
            d=self.decisions[user['facet']]
            raw={'position_kind':'balanced_position' if d['current_position']=='balanced' else 'no_position' if d['current_position']=='undecided' else 'one_sided_position'}
        elif 'quotations' in user:
            d=self.decisions.get(user['facet'])
            if not d:label='irrelevant'
            elif d['requirement_timing']=='before_acceptance':label='prerequisite'
            elif d['requirement_timing']=='ongoing_after_acceptance':label='ongoing_requirement'
            elif d['requirement_timing']=='information_only':label='uncertainty'
            else:label={'accepted':'acceptance','rejected':'rejection','balanced':'balanced','undecided':'uncertainty','cautious':'caution','refused_despite_changes':'categorical_refusal'}[d['current_position']]
            requirements={q['evidence_id'] for q in self.quotes[user['facet']]['requirements']}
            raw={n:('rejection' if label=='prerequisite' and q['evidence_id'] not in requirements else label) for n,q in user['quotations'].items()}
        elif 'facet' in user:raw={g:[q['evidence_id'] for q in qs] for g,qs in self.quotes[user['facet']].items()}
        else:raw={'interpretation':'unassessed','excerpts':[],'rationale':'No route stance.'}
        return validator(json.dumps(raw))


def quote(r,text):return {'evidence_id':r,'quotation':text}


def test_pdf_wrapped_fn_evidence_restores_original_passages():
    key='noise:acoustic_impact'
    words={'O.p001':"If these drones are buzzing past 15 times a day, that constant electric hum is\ngoing to drive me crazy, especially when I'm trying to relax on my balcony in\nthe evening.",
        'O.p002':"If they can\nroute them over the industrial park or high enough that I can't hear them orsee cameras looking into my property, fine."}
    normalized={r:' '.join(t.split()) for r,t in words.items()}
    c=Client({r:[key] for r in words},
        {key:{'positions':[quote('O.p001',normalized['O.p001'])],
              'requirements':[quote('O.p002',normalized['O.p002'])],'qualifications':[]}},
        {key:{'requirement_timing':'before_acceptance','current_position':'rejected'}})
    extract(c,None,evidence(words),None)
    f=c.last_original_facets[0]
    assert f.position=='opposed' and f.conditional_willingness=='willing'
    authored=c.last_settings['facet_evidence_reviews'][key]['authored_evidence']
    for group in ('positions','requirements'):
        for q in authored[group]:
            assert q['quotation'] in words[q['evidence_id']]


def test_complete_fn_answer_preserves_three_views_and_shared_conditions():
    from pathlib import Path
    from iam_sra.evidence import passages
    text=json.loads((Path(__file__).resolve().parents[1]/'eval/fn_reference.json').read_text())['citizen_text']
    words={'O.'+r:t for r,t in passages(text).items()}
    ref=lambda phrase:next(r for r,t in words.items() if phrase in t)
    medical='welfare_equity:medical_public_benefit'
    noise='noise:acoustic_impact'
    privacy='perceived_safety_privacy:personal_privacy'
    nominations={r:[] for r in words}
    positions={medical:ref('hospital use'),noise:ref('constant electric hum'),privacy:ref('navigation cameras')}
    requirement=ref('industrial park')
    for key,r in positions.items():nominations[r].append(key)
    nominations[requirement]=[noise,privacy]
    quotes={key:{'positions':[quote(r,words[r])],
        'requirements':[quote(requirement,words[requirement])] if key!=medical else [],
        'qualifications':[]} for key,r in positions.items()}
    decisions={key:{'requirement_timing':'none' if key==medical else 'before_acceptance',
        'current_position':'accepted' if key==medical else 'rejected'} for key in positions}
    class FNClient(Client):
        def _request(self,http,stage,system,user,schema,validator):
            if 'facet' in user and 'citizen_evidence' in user:
                assert set(schema['properties'])=={'requirements','positions','qualifications'}
                assert all(p['items']=={'type':'string','enum':list(words)} for p in schema['properties'].values())
            if 'subject_grounding' in user:
                assert all(p['enum']==['',n] for n,p in schema['properties'].items())
            if 'citizen_evidence' in user and 'facet' not in user:
                return validator(json.dumps({'interpretation':'opposed','excerpts':[ref('completely oppose')],
                    'rationale':'Opposes the original route unless changes address the concerns.'}))
            return super()._request(http,stage,system,user,schema,validator)
    c=FNClient(nominations,quotes,decisions)
    result=extract(c,None,evidence(words),None)
    facets={f.concern_id+':'+f.facet:f for f in c.last_original_facets}
    assert set(facets)=={medical,noise,privacy}
    assert facets[medical].position=='supported' and not facets[medical].condition_ids
    for key in (noise,privacy):
        assert facets[key].position=='opposed'
        assert facets[key].conditional_willingness=='willing'
        assert requirement in facets[key].condition_ids
    assert result.current_route_stance.interpretation=='opposed'


@pytest.mark.parametrize('source,quotation,expected',[
    ('vital public\nservice','vital public service','vital public\nservice'),
    ('vital\r\n public\tservice','vital public service','vital\r\n public\tservice'),
    ('vital\u00a0public service','vital public service','vital\u00a0public service'),
    ('orsee cameras','or see cameras',None),
    ('public service','Public service',None),
    ('public service.','public service!',None),
    ('public service','saving lives',None),
    ('public service','  ',None),
])
def test_quote_matching_only_allows_whitespace_changes(source,quotation,expected):
    from iam_sra.evidence import original_quote
    assert original_quote(source,quotation)==expected


def test_endorsement_quote_restores_pdf_whitespace():
    from iam_sra.semantic_review import endorsement
    source='I fully support the\nmedical public benefit.'
    class EndorsementClient:
        def _request(self,http,stage,system,user,schema,validator):
            assert schema['properties']['quotation']=={'type':'string','enum':[source]}
            return validator(json.dumps({'classification':'explicit_unqualified_endorsement',
                'evidence_id':'O.p001','quotation':'I fully support the medical public benefit.'}))
    result=endorsement(EndorsementClient(),None,'welfare_equity','medical_public_benefit',
        evidence({'O.p001':source}),['O.p001'])
    assert result.quotation==source


def test_qualification_is_recovered_when_nomination_omits_its_passage():
    key='noise:acoustic_impact';words={'O.p001':'The hum would ruin my rest.','O.p002':'I would agree only after it becomes quieter.'}
    c=Client({'O.p001':[key],'O.p002':[]},
        {key:{'positions':[quote('O.p001',words['O.p001'])],'requirements':[quote('O.p002',words['O.p002'])],'qualifications':[]}},
        {key:{'requirement_timing':'before_acceptance','current_position':'accepted'}})
    extract(c,None,evidence(words),None)
    f=c.last_original_facets[0]
    assert f.position=='opposed' and f.conditional_willingness=='willing' and f.condition_ids==['O.p002']
    assert c.last_settings['facet_evidence_reviews'][key]['authored_evidence']['requirements']


@pytest.mark.parametrize('text,timing,stance,expected',[
    ('I accept now, with continuing reviews required.','ongoing_after_acceptance','accepted','supported'),
    ('I need the hours changed before agreeing.','before_acceptance','rejected','opposed'),
    ('I cannot judge it until I get information.','information_only','undecided','uncertain')])
def test_requirement_timing_preserves_current_position(text,timing,stance,expected):
    key='noise:acoustic_impact';q=quote('O.p001',text)
    c=Client({'O.p001':[key]},{key:{'positions':[q],'requirements':[q],'qualifications':[]}},
        {key:{'requirement_timing':timing,'current_position':stance}})
    extract(c,None,evidence({'O.p001':text}),None)
    assert c.last_original_facets[0].position==expected
    assert bool(c.last_original_facets[0].condition_ids)==(timing!='information_only')


def test_balanced_reservation_is_not_imposed_requirement():
    key='noise:acoustic_impact';text='The advantages and drawbacks are equally persuasive.'
    c=Client({'O.p001':[key]},{key:{'positions':[quote('O.p001',text)],'requirements':[],'qualifications':[]}},
        {key:{'requirement_timing':'none','current_position':'balanced'}})
    extract(c,None,evidence({'O.p001':text}),None)
    f=c.last_original_facets[0];assert f.position=='mixed' and not f.condition_ids


def test_unknown_evidence_selection_is_rejected():
    key='noise:acoustic_impact'
    c=Client({'O.p001':[key]},{key:{'positions':[quote('O.p999','Invented acceptance')],'requirements':[],'qualifications':[]}}, {})
    with pytest.raises(AssessmentError,match='existing citizen passage'):extract(c,None,evidence({'O.p001':'The hum is acceptable.'}),None)


def test_three_issues_in_one_passage_and_unsupported_nomination():
    keys=['noise:acoustic_impact','wind_downwash:rotor_wind','energy_emissions:energy_demand'];wrong='public_awareness_trust:institutional_trust'
    text='The hum, rotor wind and electricity demand are acceptable.'
    c=Client({'O.p001':keys+[wrong]},
        {**{k:{'positions':[quote('O.p001',text)],'requirements':[],'qualifications':[]} for k in keys},wrong:{'positions':[],'requirements':[],'qualifications':[]}},
        {k:{'requirement_timing':'none','current_position':'accepted'} for k in keys})
    extract(c,None,evidence({'O.p001':text}),None)
    assert {f.concern_id+':'+f.facet for f in c.last_original_facets}==set(keys)


def test_bare_agreement_does_not_generate_facet_reviews():
    c=Client({'O.p001':[]},{},{})
    extract(c,None,evidence({'O.p001':'Yes.'}),None)
    assert not c.last_original_facets


@pytest.mark.parametrize('array,role,text,expected',[
    ('requirements','acceptance','I support the medical purpose.','supported'),
    ('qualifications','uncertainty','I have no position on emissions.','uncertain')])
def test_wrong_extraction_array_does_not_change_semantics(array,role,text,expected):
    key='welfare_equity:medical_public_benefit' if role=='acceptance' else 'energy_emissions:emissions'
    class AuditClient(Client):
        def _request(self,http,stage,system,user,schema,validator):
            if 'quotations' in user:return validator(json.dumps({n:role for n in user['quotations']}))
            return super()._request(http,stage,system,user,schema,validator)
    data={'positions':[],'requirements':[],'qualifications':[]};data[array]=[quote('O.p001',text)]
    c=AuditClient({'O.p001':[key]},{key:data},{key:{'requirement_timing':'none','current_position':'accepted' if role=='acceptance' else 'undecided'}})
    extract(c,None,evidence({'O.p001':text}),None)
    f=c.last_original_facets[0]
    assert f.position==expected and not f.condition_ids


def test_nominated_support_survives_empty_quote_extraction():
    key='welfare_equity:medical_public_benefit';text='I support the medical purpose.'
    c=Client({'O.p001':[key]},{key:{'positions':[],'requirements':[],'qualifications':[]}},
        {key:{'requirement_timing':'none','current_position':'accepted'}})
    extract(c,None,evidence({'O.p001':text}),None)
    assert c.last_original_facets[0].position=='supported'


def test_other_aspect_requirement_cannot_overturn_supported_facet():
    key='energy_emissions:energy_demand'
    words={'O.p001':'I accept the electricity demand.','O.p002':'I need a quieter service before agreeing to the route.'}
    class IsolatedClient(Client):
        def _request(self,http,stage,system,user,schema,validator):
            if 'relevance_check' in user:
                return validator(json.dumps({n:q['evidence_id']=='O.p001' for n,q in user['relevance_check'].items()}))
            if 'relevance_recheck' in user:
                return validator(json.dumps({n:'other_facet_evaluation' for n in user['relevance_recheck']}))
            if 'quotations' in user:
                assert all(q['evidence_id']=='O.p001' for q in user['quotations'].values())
                return validator(json.dumps({n:'acceptance' for n in user['quotations']}))
            return super()._request(http,stage,system,user,schema,validator)
    c=IsolatedClient({'O.p001':[key],'O.p002':[]},
        {key:{'positions':[quote('O.p001',words['O.p001'])],'requirements':[quote('O.p002',words['O.p002'])],'qualifications':[]}},
        {key:{'requirement_timing':'none','current_position':'accepted'}})
    extract(c,None,evidence(words),None)
    f=c.last_original_facets[0]
    assert f.position=='supported' and f.evidence_ids==['O.p001'] and not f.condition_ids


@pytest.mark.parametrize('wrong_role',['rejection','uncertainty'])
def test_independent_balance_review_preserves_competing_grounds(wrong_role):
    key='cost_roi_business:cost_financing';text='I see a worthwhile investment and significant drawbacks, with neither prevailing.'
    class BalancedClient(Client):
        def _request(self,http,stage,system,user,schema,validator):
            if 'quotations' in user:return validator(json.dumps({n:wrong_role for n in user['quotations']}))
            return super()._request(http,stage,system,user,schema,validator)
    c=BalancedClient({'O.p001':[key]},
        {key:{'positions':[quote('O.p001',text)],'requirements':[],'qualifications':[]}},
        {key:{'requirement_timing':'none','current_position':'balanced'}})
    extract(c,None,evidence({'O.p001':text}),None)
    f=c.last_original_facets[0]
    assert f.position=='mixed' and not f.condition_ids
    assert c.last_settings['facet_evidence_reviews'][key]['balanced_position_review']=='balanced_position'


@pytest.mark.parametrize('key,text,stance,expected',[
    ('wind_downwash:rotor_wind','The rotor airflow is acceptable to me.','accepted','supported'),
    ('cost_roi_business:cost_financing','I see worthwhile spending and financial drawbacks, equally persuasive.','balanced','mixed')])
def test_false_negative_relevance_needs_independent_subject_confirmation(key,text,stance,expected):
    class RecheckClient(Client):
        def _request(self,http,stage,system,user,schema,validator):
            if 'relevance_check' in user:return validator(json.dumps({n:False for n in user['relevance_check']}))
            return super()._request(http,stage,system,user,schema,validator)
    c=RecheckClient({'O.p001':[key]},
        {key:{'positions':[quote('O.p001',text)],'requirements':[],'qualifications':[]}},
        {key:{'requirement_timing':'none','current_position':stance}})
    extract(c,None,evidence({'O.p001':text}),None)
    assert c.last_original_facets[0].position==expected
    audit=c.last_settings['facet_evidence_reviews'][key]
    assert not any(audit['subject_relevance'].values())
    assert set(audit['subject_reconsideration'].values())=={'facet_evaluation'}


@pytest.mark.parametrize('comparison,expected',[
    ('whole_proposal_only','supported'),('different_aspect','supported'),('same_aspect','mixed')])
def test_recovery_compares_subjects_before_combining_opposite_views(comparison,expected):
    key='energy_emissions:energy_demand'
    words={'O.p001':'The electricity demand is acceptable.', 'O.p002':
        'The electricity demand is also unacceptable in important ways.' if comparison=='same_aspect' else
        'I reject the current project.' if comparison=='whole_proposal_only' else 'The appearance is unacceptable.'}
    class ConflictingClient(Client):
        def _request(self,http,stage,system,user,schema,validator):
            if 'relevance_check' in user:
                return validator(json.dumps({n:q['evidence_id']=='O.p001' for n,q in user['relevance_check'].items()}))
            if 'relevance_recheck' in user:
                return validator(json.dumps({n:'facet_evaluation' for n in user['relevance_recheck']}))
            if 'candidate_subjects' in user:
                return validator(json.dumps({n:comparison for n in user['candidate_subjects']}))
            if 'quotations' in user:
                return validator(json.dumps({n:'acceptance' if q['evidence_id']=='O.p001' else 'rejection' for n,q in user['quotations'].items()}))
            return super()._request(http,stage,system,user,schema,validator)
    c=ConflictingClient({'O.p001':[key],'O.p002':[]},
        {key:{'positions':[quote(r,t) for r,t in words.items()],'requirements':[],'qualifications':[]}},
        {key:{'requirement_timing':'none','current_position':'balanced' if comparison=='same_aspect' else 'accepted'}})
    extract(c,None,evidence(words),None)
    f=c.last_original_facets[0]
    assert f.position==expected
    assert c.last_settings['facet_evidence_reviews'][key]['subject_comparison']
    if expected=='supported':assert f.evidence_ids==['O.p001']


def test_generic_project_refusal_cannot_admit_an_unmentioned_facet():
    key='cost_roi_business:business_viability';text='I categorically oppose this entire plan.'
    class SubjectClient(Client):
        def _request(self,http,stage,system,user,schema,validator):
            if 'subject_grounding' in user:
                return validator(json.dumps({n:'' for n in user['subject_grounding']}))
            if 'quotations' in user:pytest.fail('Unmentioned facet must be rejected before polarity classification')
            return super()._request(http,stage,system,user,schema,validator)
    c=SubjectClient({'O.p001':[key]},
        {key:{'positions':[quote('O.p001',text)],'requirements':[],'qualifications':[]}},
        {key:{'requirement_timing':'none','current_position':'refused_despite_changes'}})
    extract(c,None,evidence({'O.p001':text}),None)
    assert not c.last_original_facets
    audit=c.last_settings['facet_evidence_reviews'][key]
    assert all(audit['subject_relevance'].values()) and not any(audit['subject_grounding'].values())


def test_subject_grounding_cannot_invent_an_aspect_word():
    key='cost_roi_business:business_viability';text='I oppose this plan.'
    class InventedSubjectClient(Client):
        def _request(self,http,stage,system,user,schema,validator):
            if 'subject_grounding' in user:
                return validator(json.dumps({n:'profitability' for n in user['subject_grounding']}))
            return super()._request(http,stage,system,user,schema,validator)
    c=InventedSubjectClient({'O.p001':[key]},
        {key:{'positions':[quote('O.p001',text)],'requirements':[],'qualifications':[]}},
        {key:{'requirement_timing':'none','current_position':'rejected'}})
    with pytest.raises(AssessmentError,match='grounded'):extract(c,None,evidence({'O.p001':text}),None)
