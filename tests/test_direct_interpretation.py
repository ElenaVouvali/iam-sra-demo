"""Direct initial transport and evidence contracts, not live accuracy claims."""
import copy
import json
from pathlib import Path
import httpx
import pytest
from iam_sra.assessment import AssessmentError
from iam_sra.conversation_client import ConversationClient
from iam_sra.evidence import passages
from iam_sra.interpretation import EvidenceItem
from iam_sra.session import Session,State


ROOT=Path(__file__).parents[1]


def direct_http(monkeypatch,outputs,review_scope=False):
    # Most tests isolate the mapping wire contract; relevance tests opt in.
    import iam_sra.direct_interpretation as module
    original_config=module.config
    monkeypatch.setattr(module,'config',lambda name: {**original_config(name),'initial_relevance_review':review_scope} if name=='prompts' else original_config(name))
    calls=[]
    class HTTP:
        def __init__(self,*args,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,json,**kwargs):
            calls.append((url,copy.deepcopy(json)))
            if url.endswith('/tokenize'):body={'count':1600}
            else:
                raw=outputs.pop(0)
                finish,raw=raw if isinstance(raw,tuple) else ('stop',raw)
                body={'choices':[{'finish_reason':finish,'message':{'content':raw if isinstance(raw,str) else __import__('json').dumps(raw)}}]}
            return httpx.Response(200,json=body,request=httpx.Request('POST',url))
    monkeypatch.setattr('iam_sra.conversation_client.httpx.Client',HTTP)
    return calls


def entry(ref,position='opposed',conditions=None):
    return {'position':position,'evidence_ids':[ref],'condition_ids':conditions or [],
        'conditional_willingness':'willing' if conditions else 'not_stated','rationale':'Citizen position on this aspect.'}


def output(facets,ref='O.p001'):
    return {'route':{'interpretation':'opposed','excerpts':[ref]},
        'facets':[{'facet':key,**{k:v for k,v in value.items() if k not in {'rationale','evidence_ids'}},'evidence_ids':{'primary':value['evidence_ids'][0],'additional':value['evidence_ids'][1:]}} for key,value in facets.items()]}


@pytest.mark.parametrize('quoted',[False,True])
def test_pdf_baseline_uses_one_interpretation_request_before_confirmation(monkeypatch,quoted):
    pack=json.loads((ROOT/'manual-tests/privacy-mapping-cases.json').read_text())
    text=next(c['response'] for c in pack['cases'] if c['id']=='P02')
    if quoted:text='"'+text+'"'
    words={'O.'+r:t for r,t in passages(text).items()}
    ref=lambda phrase:next(r for r,t in words.items() if phrase in t)
    remedy=ref('industrial park')
    raw=output({'noise:acoustic_impact':entry(ref('constant electric hum'),conditions=[remedy]),
        'perceived_safety_privacy:personal_privacy':entry(ref('navigation cameras'),conditions=[remedy]),
        'welfare_equity:medical_public_benefit':entry(ref('hospital use'),'supported')},ref('completely oppose'))
    calls=direct_http(monkeypatch,[raw]);client=ConversationClient()
    s=Session();s.begin();s.submit(text,client)
    assert s.state==State.INTERPRETATION and s.initial is None and s.confirmed is None
    assert len(calls)==2
    request=calls[-1][1]
    assert json.loads(request['messages'][1]['content'])['citizen_passages']==words
    assert request['temperature']==0.2 and request['chat_template_kwargs']=={'enable_thinking':False}
    assert set(request['guided_json']['properties'])=={'route','facets'}
    fields=request['guided_json']['$defs']['FacetInterpretation']['oneOf'][0]['properties']
    assert 'score' not in fields and 'rationale' not in fields
    assert request['guided_json']['properties']['facets']['type']=='array'
    assert s.draft.current_route_stance.interpretation=='opposed'
    assert len(s.original_facets)==3
    for key in ('noise:acoustic_impact','perceived_safety_privacy:personal_privacy'):
        assert s.original_facets[key].position=='opposed'
        assert s.original_facets[key].condition_ids==[remedy]
    assert s.original_facets['welfare_equity:medical_public_benefit'].position=='supported'
    assert s.inference[0]['metrics']['generation_calls']==1
    assert s.inference[0]['diagnostics'][0]['stage']=='initial_interpretation'


def test_direct_path_does_not_add_or_remove_the_models_supported_facets(monkeypatch):
    raw=output({'noise:acoustic_impact':entry('O.p001')})
    calls=direct_http(monkeypatch,[raw])
    client=ConversationClient()
    result=client.interpret({'O.p001':EvidenceItem(id='O.p001',text='The hum is annoying.',context='original',source='citizen_original')})
    assert [c.concern_id for c in result.concerns]==['noise']
    assert len(calls)==2 and len(client.last_original_facets)==1


@pytest.mark.parametrize('corruption',['unknown_ref','unknown_facet','score','duplicate'])
def test_invalid_direct_interpretations_receive_only_one_retry(monkeypatch,corruption):
    raw=output({'noise:acoustic_impact':entry('O.p001')})
    if corruption=='unknown_ref':raw['facets'][0]['evidence_ids']['primary']='invented'
    elif corruption=='unknown_facet':raw['facets'][0]['facet']='invented:facet'
    elif corruption=='score':raw['facets'][0]['score']=3
    else:raw='{"route":'+json.dumps(raw['route'])+',"facets":{},"facets":{}}'
    calls=direct_http(monkeypatch,[raw,raw]);client=ConversationClient()
    with pytest.raises(AssessmentError):
        client.interpret({'O.p001':EvidenceItem(id='O.p001',text='The hum is annoying.',context='original',source='citizen_original')})
    assert len(calls)==4 and client.last_metrics['generation_calls']==2
    assert all(d['stage']=='initial_interpretation' for d in client.last_diagnostics)


def test_direct_response_cache_still_revalidates_without_another_model_call(monkeypatch):
    calls=direct_http(monkeypatch,[output({'noise:acoustic_impact':entry('O.p001')})])
    evidence={'O.p001':EvidenceItem(id='O.p001',text='The hum is annoying.',context='original',source='citizen_original')}
    client=ConversationClient();client.bind_session('same-citizen',0)
    first=client.interpret(evidence);again=client.interpret(evidence)
    assert first.model_dump()==again.model_dump() and len(calls)==2
    assert client.last_metrics['cache_hits']==1 and client.last_metrics['generation_calls']==0


def test_truncated_output_is_rejected_then_compact_retry_completes(monkeypatch):
    raw=output({'perceived_safety_privacy:personal_privacy':entry('O.p001')})
    calls=direct_http(monkeypatch,[('length','{"route":'),raw])
    client=ConversationClient()
    result=client.interpret({'O.p001':EvidenceItem(id='O.p001',text='Recording my family is unacceptable.',context='original',source='citizen_original')})
    assert len(calls)==4 and client.last_metrics['generation_calls']==2
    assert result.concerns[0].facets==['personal_privacy']
    assert client.last_diagnostics[0]['failure']=='truncated'
    assert client.last_diagnostics[1]['evidence_pass']


def test_compact_output_cannot_repeat_a_facet(monkeypatch):
    raw=output({'noise:acoustic_impact':entry('O.p001')})
    raw['facets'].append(copy.deepcopy(raw['facets'][0]))
    calls=direct_http(monkeypatch,[raw,raw])
    with pytest.raises(AssessmentError,match='Duplicate interpreted facet'):
        ConversationClient().interpret({'O.p001':EvidenceItem(id='O.p001',text='The hum is annoying.',context='original',source='citizen_original')})
    assert len(calls)==4


def test_guided_schema_prevents_incoherent_route_and_condition_fields(monkeypatch):
    from jsonschema import Draft202012Validator
    valid=output({'noise:acoustic_impact':entry('O.p001',conditions=['O.p001'])})
    calls=direct_http(monkeypatch,[valid])
    evidence={'O.p001':EvidenceItem(id='O.p001',text='I cannot accept the noise unless it is quieter.',context='original',source='citizen_original')}
    ConversationClient().interpret(evidence)
    validator=Draft202012Validator(calls[-1][1]['guided_json'])
    assert not list(validator.iter_errors(valid))
    invalid=copy.deepcopy(valid)
    invalid['facets'][0]['conditional_willingness']='not_stated'
    assert list(validator.iter_errors(invalid))
    for stance,refs in [('opposed',[]),('unassessed',['O.p001'])]:
        invalid=copy.deepcopy(valid)
        invalid['route']={'interpretation':stance,'excerpts':refs}
        assert list(validator.iter_errors(invalid))
    valid['route']={'interpretation':'unassessed','excerpts':[]}
    assert not list(validator.iter_errors(valid))


def test_evidence_requirement_survives_guided_schema_bound_removal(monkeypatch):
    from jsonschema import Draft202012Validator
    raw=output({'noise:acoustic_impact':entry('O.p001')})
    calls=direct_http(monkeypatch,[raw])
    evidence={'O.p001':EvidenceItem(id='O.p001',text='The sound disrupts my rest.',context='original',source='citizen_original')}
    result=ConversationClient().interpret(evidence)
    validator=Draft202012Validator(calls[-1][1]['guided_json'])
    assert not list(validator.iter_errors(raw))
    for empty in [[],{}, {'additional':[]}, {'primary':'invented','additional':[]}]:
        invalid=copy.deepcopy(raw);invalid['facets'][0]['evidence_ids']=empty
        assert list(validator.iter_errors(invalid))
    assert result.concerns[0].excerpts==['O.p001']


def test_primary_and_additional_evidence_are_preserved_for_balanced_facets(monkeypatch):
    raw=output({'noise:acoustic_impact':entry('O.p001',position='mixed')})
    raw['facets'][0]['evidence_ids']['additional']=['O.p002']
    direct_http(monkeypatch,[raw]);client=ConversationClient()
    evidence={r:EvidenceItem(id=r,text=t,context='original',source='citizen_original') for r,t in [('O.p001','The sound is tolerable.'),('O.p002','But I have material reservations about its repetition.')]}
    client.interpret(evidence)
    assert client.last_original_facets[0].evidence_ids==['O.p001','O.p002']


def test_unidentified_route_receives_focused_reread_with_full_remedy_evidence(monkeypatch):
    case=next(c for c in json.loads((ROOT/'manual-tests/initial-assessment-cases.json').read_text())['cases'] if c['id']=='T02')
    words={'O.'+r:t for r,t in passages(case['response']).items()}
    ref=lambda phrase:next(r for r,t in words.items() if phrase in t)
    privacy=ref('peering');sound=ref('buzzing');benefit=ref('urgent hospital');remedy=ref('Keep the sound');route=ref('as written')
    first=output({'perceived_safety_privacy:personal_privacy':entry(privacy,'supported'),
                  'noise:acoustic_impact':entry(sound),
                  'welfare_equity:medical_public_benefit':entry(benefit,'supported')})
    first['route']={'interpretation':'unassessed','excerpts':[]}
    reviewed=output({'perceived_safety_privacy:personal_privacy':entry(privacy,conditions=[remedy]),
                     'noise:acoustic_impact':entry(sound,conditions=[remedy]),
                     'welfare_equity:medical_public_benefit':entry(benefit,'supported')},route)
    calls=direct_http(monkeypatch,[first,reviewed]);client=ConversationClient()
    s=Session();s.begin();s.submit(case['response'],client)
    assert len(calls)==4 and s.confirmed is None and s.initial is None
    assert s.draft.current_route_stance.interpretation=='opposed'
    for key in ['perceived_safety_privacy:personal_privacy','noise:acoustic_impact']:
        f=s.original_facets[key]
        assert f.position=='opposed' and f.conditional_willingness=='willing'
        assert f.condition_ids==[remedy]
    review_input=json.loads(calls[-1][1]['messages'][1]['content'])
    assert review_input['citizen_passages']==words
    assert review_input['position_review'] is True
    assert not any('score' in key for key in review_input)
    assert 'cost_roi_business:cost_financing' not in review_input['facet_definitions']
    assert s.inference[0]['settings']['initial_position_review']['first_interpretation']==first


def test_position_reread_can_retain_genuinely_unstated_route(monkeypatch):
    raw=output({'noise:acoustic_impact':entry('O.p001')})
    raw['route']={'interpretation':'unassessed','excerpts':[]}
    direct_http(monkeypatch,[raw,raw]);client=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text='The sound bothers me. I have not decided about the overall route.',context='original',source='citizen_original')}
    result=client.interpret(evidence)
    assert result.current_route_stance.interpretation=='unassessed'
    assert client.last_original_facets[0].position=='opposed'
    assert client.last_original_facets[0].condition_ids==[]



def test_one_mapping_plus_one_relevance_check_discards_unsupported_topics_before_scoring(monkeypatch):
    keys=['noise:acoustic_impact','perceived_safety_privacy:personal_privacy',
          'perceived_safety_privacy:perceived_safety','airspace_capacity:airspace_traffic',
          'visual_pollution:aesthetic_clutter','sump_integration:urban_mobility_plan',
          'welfare_equity:medical_public_benefit','welfare_equity:distributive_equity']
    raw=output({key:entry('O.p001') for key in keys})
    kept={'noise:acoustic_impact','perceived_safety_privacy:personal_privacy','welfare_equity:medical_public_benefit'}
    verdicts={'supported':{key:key in kept for key in keys}}
    calls=direct_http(monkeypatch,[raw,verdicts],review_scope=True);client=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text='I support medical delivery, but the hum disrupts my rest and cameras watching my garden bother me.',context='original',source='citizen_original')}
    result=client.interpret(evidence)
    assert len(calls)==4 and client.last_metrics['generation_calls']==2
    assert {f.concern_id+':'+f.facet for f in client.last_original_facets}==kept
    assert {c.concern_id for c in result.concerns}=={'noise','perceived_safety_privacy','welfare_equity'}
    assert client.last_settings['initial_relevance_review']['score_assigned'] is False
    review_input=json.loads(calls[-1][1]['messages'][1]['content'])
    assert review_input['citizen_passages']=={'O.p001':evidence['O.p001'].text}
    assert set(review_input['facet_definitions'])==set(keys)
    assert 'confirmed_meaning' not in review_input and 'position' not in review_input
    from jsonschema import Draft202012Validator
    validator=Draft202012Validator(calls[-1][1]['guided_json'])
    assert not list(validator.iter_errors(verdicts))
    missing=copy.deepcopy(verdicts);del missing['supported'][keys[0]]
    assert list(validator.iter_errors(missing))


def test_relevance_check_retains_explicit_uncertainty_without_inventing_new_facets(monkeypatch):
    key='energy_emissions:emissions'
    raw=output({key:entry('O.p001','uncertain')})
    direct_http(monkeypatch,[raw,{'supported':{key:True}}],review_scope=True);client=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text='I have no position on lifecycle emissions until I know more.',context='original',source='citizen_original')}
    client.interpret(evidence)
    assert len(client.last_original_facets)==1
    assert client.last_original_facets[0].position=='uncertain'


def test_no_facets_requires_no_relevance_inference(monkeypatch):
    calls=direct_http(monkeypatch,[output({})],review_scope=True);client=ConversationClient()
    client.interpret({'O.p001':EvidenceItem(id='O.p001',text='No, I reject the route.',context='original',source='citizen_original')})
    assert len(calls)==2 and client.last_original_facets==[]


@pytest.mark.parametrize('supported',[True,False])
def test_route_reread_omission_does_not_silently_delete_cited_medical_facet(monkeypatch,supported):
    key='welfare_equity:medical_public_benefit'
    first=output({key:entry('O.p001','supported')})
    first['route']={'interpretation':'unassessed','excerpts':[]}
    reread=output({},'O.p002')
    calls=direct_http(monkeypatch,[first,reread,{'supported':{key:supported}}],review_scope=True)
    c=ConversationClient()
    evidence={eid:EvidenceItem(id=eid,text=text,context='original',source='citizen_original')
        for eid,text in [('O.p001','I support the hospital delivery purpose.'),('O.p002','I oppose the route as written.')]}
    result=c.interpret(evidence)
    assert result.current_route_stance.interpretation=='opposed'
    assert c.last_settings['initial_position_review']['preserved_omitted_facets']==[key]
    assert len(calls)==6  # Existing mapping, reread and relevance requests only.
    if supported:
        assert result.medical_public_benefit_support.interpretation=='supported'
        assert result.medical_public_benefit_support.excerpts==['O.p001']
        assert len(c.last_original_facets)==1
    else:
        # Preservation cannot override an explicit relevance rejection.
        assert result.medical_public_benefit_support.interpretation=='unassessed'
        assert c.last_original_facets==[]


def test_explicit_reread_revision_is_not_overridden_by_preservation(monkeypatch):
    key='welfare_equity:medical_public_benefit'
    first=output({key:entry('O.p001','supported')})
    first['route']={'interpretation':'unassessed','excerpts':[]}
    reread=output({key:entry('O.p001','uncertain')},'O.p002')
    direct_http(monkeypatch,[first,reread])
    c=ConversationClient()
    evidence={eid:EvidenceItem(id=eid,text=text,context='original',source='citizen_original')
        for eid,text in [('O.p001','I have not decided about the medical purpose.'),('O.p002','I oppose this route.')]}
    result=c.interpret(evidence)
    assert result.medical_public_benefit_support.interpretation=='uncertain'
    assert c.last_settings['initial_position_review']['preserved_omitted_facets']==[]
