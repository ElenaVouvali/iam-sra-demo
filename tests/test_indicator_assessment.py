from copy import deepcopy
import json
import threading
import time
import pytest
from iam_sra.assessment import AssessmentError
from iam_sra.indicator_assessment import IndicatorAssessment, resolved_scale
from iam_sra.indicator_client import validate_match, validate_reading
from iam_sra.privacy import PrivacyError
from indicator_fixtures import bank, questionnaire, Client, engine, reading, matching


def selected():
    s = engine(); s.select_indicators(['indicator-07'], 'general_understanding')
    return s


def complete(s, client=None):
    client = client or Client()
    s.indicator_answer('I propose limits to protect rest.', client)
    s.indicator_confirm(); s.indicator_finish(); s.indicator_suggest(client)
    return s.indicators.current


def test_all_fifteen_resolve_exact_citizen_scales_and_no_profile_by_profession():
    source = bank(); group = IndicatorAssessment(source,questionnaire(source))
    for indicator in source['indicators']:
        scale = group.scale(indicator['id'])
        assert [s['level'] for s in scale] == list(range(1, 10))
        assert all(s['profile'] == 'citizen' and s['scale'] == 'CRL' for s in scale)
        assert [s['statement'] for s in scale] == [s['statement'] for s in source['statements'] if s['indicator_id'] == indicator['id'] and s['profile'] == 'citizen']
    s = engine(); s.respondent['stakeholder_category'] = 'researchers'
    s.select_indicators(['indicator-01'], 'general_understanding')
    assert s.indicators.scope['response_profile'] == 'citizen'
    s.respondent['perspective'] = 'organisation'
    with pytest.raises(ValueError): s.select_indicators(['indicator-01'], 'general_understanding')
    assert s.indicator_view()['available']  # v0.2 exposes profile configuration, not an automatic citizen result.


def test_new_policy_does_not_reuse_global_participation_gate_and_opposition_is_neutral():
    s = selected(); row = complete(s)
    assert row['tool']['statement']['level'] == 5
    assert row['participant'] is None
    evidence = s.indicators.evidence(); scale = s.indicators.scale('indicator-07')
    for stance in ('I strongly oppose this service.', 'I enthusiastically support this service.'):
        more = deepcopy(evidence)
        more.append({'evidence_id': 'stance', 'answer': stance, 'observations': reading(stance, 'stance')['observations']})
        result = validate_match(matching(scale, more), scale, more)
        assert result['selected_statement_id'] == row['tool']['selected_statement_id']
        assert validate_match(matching(scale, more[-1:], abstain=True), scale, more[-1:])['selected_statement_id'] is None


@pytest.mark.parametrize('kind,actor,actuality,domain', [
    ('intention','self','hypothetical','IAM'), ('barrier','self','unspecified','IAM'),
    ('activity','organisation','actual','IAM'), ('influence','third_party','actual','IAM'),
    ('contribution','self','actual','other'), ('influence','self','hypothetical','IAM')])
def test_v2_fallible_categories_are_preserved_without_pre_excluding_statements(kind,actor,actuality,domain,monkeypatch):
    from iam_sra.indicator_client import IndicatorClient
    scale=resolved_scale(bank(),'indicator-07');quote='I would contribute if a meeting were accessible.'
    evidence=[{'evidence_id':'e1','answer':quote,'observations':reading(quote,kind,actuality,actor,domain)['observations']}]
    def request(self,http,stage,system,user,schema,validator):
        assert user['evidence'][0]['answer']==quote and user['evidence'][0]['observations']==evidence[0]['observations']
        assert len(schema['properties']['selected_statement_id']['anyOf'][0]['enum'])==9
        assert all('supported' in r['properties']['status']['enum'] for r in schema['properties']['assessments']['properties'].values())
        raw=matching(scale,evidence,abstain=True);raw['assessments']={r.pop('statement_id'):r for r in raw['assessments']}
        return validator(raw)
    monkeypatch.setattr(IndicatorClient,'_request',request)
    IndicatorClient().match(bank()['indicators'][6],{'response_profile':'citizen'},scale,evidence)


def test_exact_report_is_retained_but_fabricated_influence_citations_are_rejected():
    scale=resolved_scale(bank(),'indicator-07');quote='I attended a meeting but made no contribution.'
    evidence=[{'evidence_id':'e1','answer':quote,'observations':reading(quote,'activity','actual')['observations']}]
    raw=matching(scale,evidence,7);raw['assessments'][6]['evidence'][0]['quote']='My input changed a decision.'
    with pytest.raises(AssessmentError):validate_match(raw,scale,evidence)
    evidence[0]['answer']='My written input changed the agreed hours.'
    evidence[0]['observations']=reading(evidence[0]['answer'],'influence','actual')['observations']
    assert validate_match(matching(scale,evidence,7),scale,evidence)['selected_statement_id'].endswith('-7')


def test_barrier_neither_forces_low_level_nor_earns_a_level():
    s=selected(); row=complete(s)
    evidence=s.indicators.evidence(); quote='No accessible meeting has been offered.'
    evidence.append({'evidence_id':'barrier','answer':quote,'observations':reading(quote,'barrier')['observations']})
    scale=s.indicators.scale('indicator-07')
    assert validate_match(matching(scale,evidence),scale,evidence)['selected_statement_id'].endswith('-5')
    assert validate_match(matching(scale,evidence[-1:],abstain=True),scale,evidence[-1:])['selected_statement_id'] is None


@pytest.mark.parametrize('choice', ['endorse','select','unsure','decline'])
def test_explicit_participant_judgments_are_separate_and_never_prepopulated(choice):
    s=selected(); row=complete(s); original=deepcopy(row['tool'])
    s.indicator_review(choice,s.indicators.revision,'indicator-07-crl-3' if choice=='select' else None,'Optional disagreement.')
    assert row['tool']==original
    assert row['participant']['status']=={'endorse':'endorsed','select':'selected','unsure':'unsure','decline':'declined'}[choice]
    if choice=='select': assert row['participant']['statement']['level']==3 and row['participant']['disagrees_with_tool']
    if choice in {'unsure','decline'}: assert row['participant']['statement'] is None


def test_abstention_does_not_prevent_level_one_participant_self_selection():
    s=selected(); s.indicator_answer('',Client(),'skip'); s.indicator_suggest(Client())
    assert s.indicators.current['tool']['status']=='abstained'
    s.indicator_review('select',s.indicators.revision,'indicator-07-crl-1')
    assert s.indicators.current['participant']['statement']['level']==1
    assert s.indicators.current['tool']['selected_statement_id'] is None
    assert s.indicators.current['status']=='completed'


def test_confirmed_reasoning_is_required_and_correction_is_not_new_evidence():
    s=selected(); client=Client(); s.indicator_answer('I propose rest protections.',client)
    with pytest.raises(ValueError): s.indicator_suggest(client)
    before=s.indicators.current['pending']['text']
    class Bad(Client):
        def interpret(self,*args): return reading('This fabricated quote is not in the answer.')
    with pytest.raises(AssessmentError): s.indicator_correct('I led a project.',Bad())
    s.indicator_correct('Keep only the original meaning.',client)
    assert s.indicators.current['pending']['text']==before
    assert 'Keep only the original meaning.' not in json.dumps(s.indicators.current['pending']['reading'])


def test_answer_and_interpretation_edits_invalidate_both_judgments_and_stale_review():
    for mode in ('answer','interpretation'):
        s=selected(); row=complete(s); version=s.indicators.revision
        s.indicator_review('endorse',version)
        event=row['events'][0]
        s.indicator_edit(event['id'],mode)
        assert row['tool'] is None and row['participant'] is None
        assert s.indicators.history[-1]['participant']['status']=='endorsed'
        assert event['text']=='I propose limits to protect rest.' and not event['active']
        with pytest.raises(ValueError):s.indicator_review('endorse',version)
    s=selected(); complete(s); s.indicator_review('endorse',s.indicators.revision); s.edit_context()
    assert s.indicators.current['participant'] is None and s.indicators.current['state']=='superseded'


def test_indicator_and_scope_evidence_are_isolated_and_old_results_superseded():
    s=selected(); complete(s)
    s.select_indicators(['indicator-08'],'actual_experience')
    assert s.indicators.evidence()==[]
    assert s.indicators.results['indicator-07']['tool'] is None
    with pytest.raises(ValueError):s.select_indicators(['missing'],'general_understanding')
    with pytest.raises(ValueError):s.select_indicators(['indicator-07'],'general_understanding',reuse_answers={'indicator-08':['x']})
    with pytest.raises(ValueError):s.select_indicators(['indicator-07'],'illustrative_proposal')


def test_fabricated_ids_quotes_wrong_profiles_malformed_and_ambiguity_are_rejected():
    s=selected(); complete(s); scale=s.indicators.scale('indicator-07'); evidence=s.indicators.evidence()
    for mutation in ('id','quote','evidence','profile','conflict','ambiguity'):
        statements=deepcopy(scale); raw=matching(statements,evidence)
        if mutation=='id':raw['assessments'][0]['statement_id']='nonexistent'
        if mutation=='quote':raw['assessments'][4]['evidence'][0]['quote']='Fabricated quotation.'
        if mutation=='evidence':raw['assessments'][4]['evidence'][0]['evidence_id']='nonexistent'
        if mutation=='profile':statements[0]['profile']='organisational'
        if mutation=='conflict':raw['material_conflict']=True
        if mutation=='ambiguity':raw['selection_unclear']=True
        with pytest.raises(AssessmentError):validate_match(raw,statements,evidence)
    with pytest.raises(ValueError):validate_reading('{"meaning":2}', 'text')


@pytest.mark.parametrize('action', ['scope','answer','correction','explanation'])
def test_new_free_text_is_screened_before_state_or_model_use(action):
    s=selected(); client=Client(); secret='My password is hunter2.'
    if action=='scope':call=lambda:s.select_indicators(['indicator-07'],'general_understanding',secret)
    elif action=='answer':call=lambda:s.indicator_answer(secret,client)
    elif action=='correction':
        s.indicator_answer('I propose protections.',client);call=lambda:s.indicator_correct(secret,client)
    else:
        complete(s);call=lambda:s.indicator_review('unsure',s.indicators.revision,None,secret)
    before=deepcopy(s.indicators.view()); calls=client.calls
    with pytest.raises(PrivacyError):call()
    assert s.indicators.view()==before and client.calls==calls


def test_explicit_reuse_avoids_duplicate_understanding_question_without_leaking_to_next_indicator():
    s=engine();text='Repeated sound can interrupt rest.'
    s.general.events.append({'id':'confirmed_prior','active':True,'confirmed':True,'control':'answer',
        'context':'general_baseline','information_context':'before_information','text':text,
        'question':{'question_text':'How could the issue affect people?'},
        'claims':[{'kind':'explained_impact','subject':'respondent','span_quote':text,
                   'interpretation':'You explain an effect.','domain':'IAM','temporality':'not_applicable'}]})
    s.select_indicators(['indicator-07','indicator-08'],'general_understanding',reuse_answers={'indicator-07':['confirmed_prior']})
    assert s.indicators.question() is None  # Explicit equivalent evidence avoids the opening; matching decides sufficiency.
    assert s.indicators.evidence()[0]['information_context']=='before_information'
    s.indicator_next('indicator-08')
    assert s.indicators.evidence()==[] and s.indicators.question()['intent']=='understanding'
    with pytest.raises(ValueError):s.select_indicators(['indicator-07'],'actual_experience',reuse_answers={'indicator-07':['not-confirmed']})


def test_all_three_question_budget_and_early_stopping_are_bounded():
    s=selected();client=Client(kind='recognition',abstain=True)
    ids=[]
    while s.indicators.question():
        ids.append(s.indicators.question()['id'])
        s.indicator_answer('I recognise this issue.',client);s.indicator_confirm()
    assert len(ids)<=3 and len(ids)==len(set(ids))
    s.indicator_suggest(client)
    assert s.indicators.current['tool']['status']=='abstained'
    with pytest.raises(ValueError):s.indicator_suggest(client)


def test_missing_bank_blocks_the_new_path_without_a_global_fallback(monkeypatch):
    s=engine();s.indicators=None
    def unavailable():raise ValueError('Missing private bank')
    monkeypatch.setattr('iam_sra.indicator_assessment.load_bank',unavailable)
    view=s.indicator_view()
    assert view['available'] is False and 'import-readiness-scales.py' in view['notice']
    with pytest.raises(ValueError):s.select_indicators(['indicator-07'],'general_understanding')
    assert s._provisional is None


def test_browser_exports_omit_operational_data_and_keep_both_judgments():
    s=selected();complete(s);s.indicator_review('select',s.indicators.revision,'indicator-07-crl-2')
    data=s.browser_export();text=json.dumps(data)
    assert '/home/' not in text and 'prompts' not in text and 'base_url' not in text
    result=data['indicator_assessment']['results'][0]
    assert result['tool']['statement']['level']==5 and result['participant']['statement']['level']==2


def test_confirmed_ambiguity_is_not_discarded_to_create_support():
    s=selected();complete(s)
    evidence=s.indicators.evidence();evidence[0]['observations'][0]['ambiguities']=['Actor is unclear.']
    scale=s.indicators.scale('indicator-07')
    raw=matching(scale,evidence);raw['selection_unclear']=True
    with pytest.raises(AssessmentError):validate_match(raw,scale,evidence)


def test_wire_selection_is_constrained_to_bank_ids_or_real_json_null(monkeypatch):
    from iam_sra.indicator_client import IndicatorClient
    s=selected();complete(s);scale=s.indicators.scale('indicator-07');evidence=s.indicators.evidence()
    def request(self,http,stage,system,user,schema,validator):
        selection = schema['properties']['selected_statement_id']['anyOf']
        assert selection[1] == {'type':'null'}
        assert 'indicator-07-crl-5' in selection[0]['enum']
        assert 'indicator-07-crl-7' in selection[0]['enum']  # v2 does not gate from category/keywords.
        rows = schema['properties']['assessments']
        assert rows['required'] == [r['id'] for r in scale] and not rows['additionalProperties']
        assert rows['properties']['indicator-07-crl-7']['properties']['status']['enum'] == ['supported','insufficient','conflicting']
        assert schema['$defs']['Citation']['properties']['evidence_id']['enum']==[e['evidence_id'] for e in evidence]
        assert 'enum' not in schema['$defs']['Citation']['properties']['quote']
        wire = matching(scale,evidence,abstain=True)
        wire['assessments'] = {r.pop('statement_id'): r for r in wire['assessments']}
        return validator(__import__('json').dumps(wire))
    monkeypatch.setattr(IndicatorClient,'_request',request)
    result=IndicatorClient().match(s.indicators.indicator('indicator-07'),s.indicators.current['scope'],scale,evidence)
    assert result['selected_statement_id'] is None


@pytest.mark.parametrize('bad', ['invalid_json', 'missing_row', 'injected_id', 'invented_quote'])
def test_matching_wire_rejects_malformed_rows_and_evidence(monkeypatch, bad):
    from iam_sra.indicator_client import IndicatorClient
    s=selected();complete(s);scale=s.indicators.scale('indicator-07');evidence=s.indicators.evidence()
    def request(self,http,stage,system,user,schema,validator):
        if bad=='invalid_json': return validator('{')
        wire=matching(scale,evidence)
        wire['assessments']={r.pop('statement_id'):r for r in wire['assessments']}
        if bad=='missing_row': wire['assessments'].pop(scale[0]['id'])
        if bad=='injected_id': wire['assessments'][scale[0]['id']]['statement_id']='fake'
        if bad=='invented_quote': wire['assessments']['indicator-07-crl-5']['evidence'][0]['quote']='Invented quotation'
        return validator(__import__('json').dumps(wire))
    monkeypatch.setattr(IndicatorClient,'_request',request)
    with pytest.raises(AssessmentError):IndicatorClient().match(s.indicators.indicator('indicator-07'),{},scale,evidence)


@pytest.mark.presidio_live
def test_real_detector_allows_source_coordinates_but_still_blocks_identifying_text():
    pytest.importorskip('presidio_analyzer');pytest.importorskip('en_core_web_sm')
    from iam_sra.privacy import require_safe_data
    require_safe_data({'source':{'cell':'G63'}})
    require_safe_data({'question':{'criterion_source':{'cell':'F10'}}})
    require_safe_data({'review_row_id':'indicator-01-level-4'})
    require_safe_data({'id':'chatcmpl-'+'a'*32})
    with pytest.raises(PrivacyError):require_safe_data({'source':{'cell':'Alice Example'}})
    with pytest.raises(PrivacyError):require_safe_data({'question':{'criterion_source':{'cell':'Alice Example'}}})
    with pytest.raises(PrivacyError):require_safe_data({'review_row_id':'Alice Example'})
    with pytest.raises(PrivacyError):require_safe_data({'id':'Alice Example'})
    with pytest.raises(PrivacyError):require_safe_data({'explanation':'My PIN is 1846.'})


@pytest.mark.presidio_live
def test_actual_interpretation_prompt_passes_real_input_screening(monkeypatch):
    pytest.importorskip('presidio_analyzer');pytest.importorskip('en_core_web_sm')
    from iam_sra.indicator_client import IndicatorClient
    from iam_sra.privacy import require_safe_data
    captured = []
    def request(self, http, stage, system, user, schema, validator):
        require_safe_data({'system':system, 'user':user, 'schema':schema})
        captured.append(stage)
    monkeypatch.setattr(IndicatorClient, '_request', request)
    item = bank()['indicators'][0]
    IndicatorClient().interpret(item, {}, 'How could IAM affect people?', 'I propose protecting rest.')
    assert captured == ['indicator_interpretation']
