"""Coverage integration contracts. Scripted answers do not establish live accuracy."""
import json
from pathlib import Path
import pytest
from iam_sra.issue_mapping import extract
from iam_sra.assessment import AssessmentError
from test_issue_mapping import Client,evidence,quote

PRIVACY='perceived_safety_privacy:personal_privacy'


@pytest.fixture(autouse=True)
def experimental_coverage_policy(monkeypatch):
    """The coverage experiment is retained for replay, disabled in production."""
    from iam_sra import issue_mapping
    original=issue_mapping.config
    monkeypatch.setattr(issue_mapping,'config',lambda name:
        {**original(name),'initial_coverage_review':True} if name=='prompts' else original(name))


class CoverageClient(Client):
    def __init__(self,nominations,quotes,decisions,missing):
        super().__init__(nominations,quotes,decisions)
        self.missing=missing;self.coverage_calls=0
    def _request(self,http,stage,system,user,schema,validator):
        if 'coverage_review' in user:
            self.coverage_calls+=1
            assert stage=='coverage_review'
            return validator(json.dumps(self.missing))
        return super()._request(http,stage,system,user,schema,validator)


@pytest.mark.parametrize('text,key,position',[
    ('I would hate being watched through my bedroom window.',PRIVACY,'rejected'),
    ('Filming my family in our garden makes me uncomfortable.',PRIVACY,'rejected'),
    ('I have no privacy concerns about the navigation cameras.',PRIVACY,'accepted'),
    ('I cannot decide whether recording people is acceptable.',PRIVACY,'undecided'),
    ('Its electricity demand is unacceptable.','energy_emissions:energy_demand','rejected'),
])
def test_coverage_recovers_omitted_evidenced_aspects_without_inventing_their_position(text,key,position):
    words={'O.p001':text}
    client=CoverageClient({'O.p001':[]},
        {key:{'positions':[quote('O.p001',text)],'requirements':[],'qualifications':[]}},
        {key:{'requirement_timing':'none','current_position':position}}, {'O.p001':[key]})
    extract(client,None,evidence(words),None)
    f=client.last_original_facets[0]
    assert len(client.last_original_facets)==1
    assert f.concern_id+':'+f.facet==key
    assert f.position=={'accepted':'supported','rejected':'opposed','undecided':'uncertain'}[position]
    assert client.last_settings['preliminary_issue_selections']=={'O.p001':[]}
    assert client.last_settings['issue_selections']=={'O.p001':[key]}
    assert client.coverage_calls==1


@pytest.mark.parametrize('text',[
    'The aircraft carries a navigation camera.',
    'The hum is annoying.',
    'I oppose this entire project.',
    'I did not mean privacy; my concern is aircraft falling onto people.',
])
def test_coverage_does_not_require_privacy_when_it_is_not_evaluated(text):
    client=CoverageClient({'O.p001':[]},{},{},{'O.p001':[]})
    extract(client,None,evidence({'O.p001':text}),None)
    assert not client.last_original_facets


def test_false_positive_coverage_nomination_still_requires_subject_evidence():
    text='The aircraft carries a navigation camera.'
    client=CoverageClient({'O.p001':[]},
        {PRIVACY:{'positions':[],'requirements':[],'qualifications':[]}}, {},{'O.p001':[PRIVACY]})
    extract(client,None,evidence({'O.p001':text}),None)
    assert not client.last_original_facets
    assert client.last_settings['facet_evidence_reviews'][PRIVACY]['result']=='unsupported_nomination'


def test_shared_remedy_is_recovered_for_noise_without_rewriting_privacy():
    noise='noise:acoustic_impact'
    words={'O.p001':'The hum would ruin my rest.',
        'O.p002':'Watching my family through the windows is unacceptable.',
        'O.p003':'I would accept only if rerouting prevents both the hum and viewing into my home.'}
    nominations={'O.p001':[noise],'O.p002':[PRIVACY],'O.p003':[PRIVACY]}
    qs={key:{'positions':[quote(ref,words[ref])],
        'requirements':[quote('O.p003',words['O.p003'])],'qualifications':[]}
        for key,ref in [(noise,'O.p001'),(PRIVACY,'O.p002')]}
    client=CoverageClient(nominations,qs,
        {key:{'requirement_timing':'before_acceptance','current_position':'rejected'} for key in qs},
        {'O.p001':[],'O.p002':[],'O.p003':[noise]})
    extract(client,None,evidence(words),None)
    assert len(client.last_original_facets)==2
    assert all(f.condition_ids==['O.p003'] and f.conditional_willingness=='willing'
        for f in client.last_original_facets)


def test_exact_pdf_baseline_recovers_privacy_and_both_remedy_links():
    from iam_sra.evidence import passages
    pack=json.loads((Path(__file__).parents[1]/'manual-tests/privacy-mapping-cases.json').read_text())
    text=next(c['response'] for c in pack['cases'] if c['id']=='P02')
    assert '\n' in text and 'orsee' in text
    words={'O.'+r:t for r,t in passages(text).items()}
    ref=lambda phrase:next(r for r,t in words.items() if phrase in t)
    noise='noise:acoustic_impact';medical='welfare_equity:medical_public_benefit'
    nominations={r:[] for r in words}
    nominations[ref('hospital use')]=[medical]
    nominations[ref('constant electric hum')]=[noise]
    missing={r:[] for r in words}
    missing[ref('navigation cameras')]=[PRIVACY]
    missing[ref('industrial park')]=[noise,PRIVACY]
    qs={key:{'positions':[quote(ref(phrase),words[ref(phrase)])],
        'requirements':[quote(ref('industrial park'),words[ref('industrial park')])] if key!=medical else [],
        'qualifications':[]} for key,phrase in [(noise,'constant electric hum'),(medical,'hospital use'),(PRIVACY,'navigation cameras')]}
    client=CoverageClient(nominations,qs,
        {key:{'requirement_timing':'none' if key==medical else 'before_acceptance',
              'current_position':'accepted' if key==medical else 'rejected'} for key in qs},missing)
    result=extract(client,None,evidence(words),None)
    fs={f.concern_id+':'+f.facet:f for f in client.last_original_facets}
    assert set(fs)=={noise,medical,PRIVACY}
    assert fs[medical].position=='supported'
    for key in (noise,PRIVACY):
        assert fs[key].position=='opposed' and fs[key].condition_ids==[ref('industrial park')]
    assert result.medical_public_benefit_support.interpretation=='supported'
    for review in client.last_settings['facet_evidence_reviews'].values():
        for group in review['authored_evidence'].values():
            for q in group:assert q['quotation']==words[q['evidence_id']]


@pytest.mark.parametrize('missing',[
    {}, {'O.p999':[PRIVACY]}, {'O.p001':['invented:facet']}, {'O.p001':[PRIVACY,PRIVACY]},
])
def test_invalid_coverage_output_cannot_become_an_interpretation(missing):
    client=CoverageClient({'O.p001':[]},{},{},missing)
    with pytest.raises(AssessmentError) as error:
        extract(client,None,evidence({'O.p001':'Watching me is unacceptable.'}),None)
    assert error.value.code=='schema'


def test_live_privacy_pack_targets_registered_facets_and_requires_no_numeric_calibration():
    from iam_sra.settings import CONCERNS
    pack=json.loads((Path(__file__).parents[1]/'manual-tests/privacy-mapping-cases.json').read_text())
    assert pack['mapping_only']
    for case in pack['cases']:
        assert set(case['expected_facets'])==set(case['expected_positions'])
        for cid,facets in case['expected_facets'].items():
            assert set(facets)==set(case['expected_positions'][cid])
            assert set(facets).issubset(CONCERNS[cid]['facets'])
            assert all(score is None for score in facets.values())
