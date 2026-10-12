"""Synthetic policy and boundary tests. Flow doubles are not live NLP validation."""
import json
from copy import deepcopy
import time
import httpx
import pytest
from iam_sra.privacy import (PrivacyError, VERSION, require_clean, require_safe_data,
                            contextual_findings, screened_export, safe_message)
from iam_sra.session import Session
from iam_sra.readiness_client import ReadinessClient
from iam_sra.readiness_retrieval import retrieve, corpus, ExplanationClient
from iam_sra.readiness_report import evidence_report
from test_readiness_evidence_mode import Extractor, confirmed, record
from test_readiness_evidence_ui import start, click, confirm

SECRETS = [
    'My PIN is 1846.', 'PIN 1846', 'My password is synthetic-secret-xyz.',
    'api_key: synthetic-key-abcdef', 'Bank account: 123456789012.',
    'My card number is 4111 1111 1111 1111.', 'GB82 WEST 1234 5698 7654 32',
    'My patient number is SYNTHETIC123.',
]
PRIVATE = ['Email me at alice@example.com.', 'Call +1 202-555-0123.',
           'I am Alice Example.', 'I live at 42 Example Street.']
BENIGN = ['60 meters; 15 flights a day; reference 2026 and project 101271620.',
          'The industrial park and central hospital.', 'Meetings conflict with caring responsibilities.',
          'I prefer a quiet route and do not know whether I can participate.',
          'The year is 1846, not a credential.',
          'A bank account is unnecessary for this discussion.']


@pytest.mark.parametrize('text', SECRETS)
def test_secrets_block_without_echo_or_masked_preview(text):
    with pytest.raises(PrivacyError) as result: require_clean(text)
    assert result.value.preview is None
    assert text not in str(result.value)


@pytest.mark.parametrize('text', PRIVATE)
def test_private_details_offer_only_a_screened_preview(text):
    with pytest.raises(PrivacyError) as result: require_clean(text)
    cleaned = result.value.preview
    assert cleaned and '[private detail removed]' in cleaned
    assert require_clean(cleaned) == cleaned
    assert text not in str(vars(result.value))


@pytest.mark.parametrize('text', BENIGN)
def test_general_context_and_numbers_survive(text):
    assert require_clean(text) == text


@pytest.mark.parametrize('path', ['initial','followup','correction','rag','mitigation'])
def test_rejection_precedes_any_controller_mutation_or_call(path):
    class Never:
        def __getattr__(self, name):
            raise AssertionError('No client access before screening: ' + name)
    text = SECRETS[0]
    s = Session(assessment_mode="acceptance_and_readiness_evidence") if path=='initial' else confirmed()
    if path in {'correction','mitigation'}: s.finish()
    if path=='correction': s.edit_answer(s.events[0]['id'])
    before=deepcopy(vars(s))
    with pytest.raises(PrivacyError):
        if path=='initial': s.submit(text,Never())
        elif path=='followup': s.respond(text,Never())
        elif path=='correction': s.correct(text,Never())
        elif path=='rag': s.ask_information(text,Never())
        elif path=='mitigation': s.explore_acceptance('acoustic_impact','Unsure',text,Never())
    assert vars(s)==before
    assert text not in repr(vars(s))


def test_direct_client_is_blocked_before_tokenize_generation_or_cache():
    c=ReadinessClient();c._start();c.bind_session('synthetic-session',0)
    calls=[]
    with httpx.Client(transport=httpx.MockTransport(lambda req:calls.append(req))) as http:
        with pytest.raises(PrivacyError):
            c._request(http,'readiness_evidence','Return JSON.',{'answer':SECRETS[0]}, {},lambda raw:raw)
    assert not calls and not c.last_trace and not c._request_cache and not c._token_count_cache
    assert SECRETS[0] not in repr(vars(c))


def test_generated_secret_withheld_before_trace_validator_and_cache():
    c=ReadinessClient();c._start();c.bind_session('synthetic-session',0)
    calls=[];validated=[]
    def transport(req):
        calls.append(req.url.path)
        if req.url.path=='/tokenize':return httpx.Response(200,json={'count':10})
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'answer':SECRETS[1]})}}]})
    with httpx.Client(transport=httpx.MockTransport(transport)) as http:
        with pytest.raises(PrivacyError): c._request(http,'readiness_evidence','Return JSON.',{'answer':'I oppose the route.'},{},lambda raw:validated.append(raw))
    assert calls==['/tokenize','/v1/chat/completions']
    assert not validated and not c.last_trace and not c._request_cache
    assert c._accepted_wire is None
    assert SECRETS[1] not in repr(vars(c))


def test_detector_failure_is_closed_and_does_not_keep_unsafe_exception(monkeypatch):
    class Broken:
        def analyze(self,**kwargs):raise RuntimeError(SECRETS[0])
    s=Session(assessment_mode="acceptance_and_readiness_evidence")
    monkeypatch.setattr('iam_sra.privacy.detector',lambda:Broken())
    with pytest.raises(PrivacyError,match='setup-privacy.sh') as error:s.submit('I support it.',Extractor())
    assert error.value.code=='privacy_unavailable'
    assert not s.events and not s.inference and not s.draft_text
    assert SECRETS[0] not in str(error.value)


def test_corpus_and_queries_screen_before_retrieval_or_composition():
    c=corpus();c['passages'][0]['text']=SECRETS[0]
    with pytest.raises(PrivacyError):retrieve('What does the scenario specify?',collection=c)
    with pytest.raises(PrivacyError):retrieve(PRIVATE[0])


def test_export_and_report_gate_withholds_tampered_or_older_records():
    s=confirmed();s.finish();data=s.export()
    assert data['privacy_contract']==VERSION and data['schema_version']=='6.4.0'
    data['questions_and_answers'][0]['text']=SECRETS[0]
    with pytest.raises(PrivacyError):screened_export(data)
    with pytest.raises(PrivacyError):evidence_report(data)
    del s.privacy_contract
    with pytest.raises(PrivacyError,match='older session'):s.export()
    with pytest.raises(PrivacyError):s.submit('I support it.',Extractor())


def test_controller_resubmission_after_block_is_normal():
    s=Session(assessment_mode="acceptance_and_readiness_evidence")
    with pytest.raises(PrivacyError):s.submit(SECRETS[0],Extractor())
    s.submit('I oppose the route.',Extractor());s.confirm(True)
    assert len(s.events)==1 and s.events[0]['text']=='I oppose the route.'
    assert s.initial_readiness['numerical_crl'] is None


def test_ui_clears_secret_draft_and_allows_safe_resubmission(monkeypatch):
    app=start(monkeypatch,Extractor())
    app.text_area(key='readiness_answer').set_value(SECRETS[0]);click(app,'Continue')
    assert app.text_area(key='readiness_answer').value==''
    assert SECRETS[0] not in repr(app.session_state.session.export())
    assert not app.session_state.session.inference
    app.text_area(key='readiness_answer').set_value('I oppose the route.');click(app,'Continue')
    assert app.session_state.session.state=='review'


def test_ui_only_cleaned_preview_is_confirmed_and_retained(monkeypatch):
    app=start(monkeypatch,Extractor())
    app.text_area(key='readiness_answer').set_value(PRIVATE[0]);click(app,'Continue')
    assert app.session_state.session.state=='answer'
    assert app.text_area(key='readiness_answer').value==''
    assert PRIVATE[0] not in app.session_state.privacy_preview
    click(app,'Confirm cleaned text')
    assert app.session_state.session.pending['text']=='Email me at [private detail removed].'
    assert PRIVATE[0] not in repr(app.session_state.session.export())


def test_diagnostics_do_not_echo_sensitive_exception():
    assert '1846' not in safe_message(ValueError(SECRETS[0]))


@pytest.mark.presidio_live
def test_pinned_presidio_integration_when_installed():
    pytest.importorskip('presidio_analyzer')
    pytest.importorskip('en_core_web_sm')
    from iam_sra.privacy import detector
    detector.cache_clear()
    for text in SECRETS + PRIVATE:
        with pytest.raises(PrivacyError):require_clean(text)
    for text in BENIGN:require_clean(text)


def test_ui_rag_rejection_clears_question_and_records_no_exposure(monkeypatch):
    app=start(monkeypatch,Extractor())
    app.text_area(key='readiness_answer').set_value('I oppose the route.');click(app,'Continue');confirm(app)
    before=deepcopy(app.session_state.session.information_exposures)
    app.text_input(key='information_custom').set_value(SECRETS[0]);click(app,'Show sourced answer')
    assert app.text_input(key='information_custom').value==''
    assert app.session_state.session.information_exposures==before
    assert SECRETS[0] not in repr(app.session_state.session.export())


def test_ui_correction_rejection_preserves_pending_and_clears_widget(monkeypatch):
    app=start(monkeypatch,Extractor())
    app.text_area(key='readiness_answer').set_value('I oppose the route.');click(app,'Continue')
    before=deepcopy(app.session_state.session.pending)
    key='readiness_correction_'+str(before['version'])
    app.text_area(key=key).set_value(SECRETS[0]);click(app,'Save correction')
    assert app.text_area(key=key).value==''
    assert app.session_state.session.pending==before


def test_new_bad_submission_discards_an_earlier_cleaned_preview(monkeypatch):
    app=start(monkeypatch,Extractor())
    app.text_area(key='readiness_answer').set_value(PRIVATE[0]);click(app,'Continue')
    assert app.session_state.privacy_preview
    app.text_area(key='readiness_answer').set_value(SECRETS[0]);click(app,'Continue')
    assert not any(b.label=='Confirm cleaned text' for b in app.button)
    assert app.session_state.session.state=='answer'




def test_repetition_after_information_is_not_new_readiness_without_reasoning():
    # Existing evidence/exposure semantics remain independent of screening.
    s=confirmed();initial=s.initial_readiness
    s.display_information();s.acknowledge_information(s.information_exposures[-1]['exposure_id'])
    assert s.current_profile==initial
    assert s.pre_information_snapshot==initial


def test_unsafe_diagnostic_metadata_is_withheld():
    from iam_sra.privacy import safe_diagnostics
    assert safe_diagnostics({"detail":SECRETS[0]}) == {"details_withheld":True,"reason":"privacy_screening"}


def test_reviewed_citation_locations_are_metadata_not_private_people(monkeypatch):
    from iam_sra.privacy import reviewed_bibliographic_values
    class Cells:
        def analyze(self,*,text,**kwargs):
            return [type('Finding',(),{'entity_type':'PERSON','start':m.start(),'end':m.end()})() for m in __import__('re').finditer(r'J8|L13',text)]
    monkeypatch.setattr('iam_sra.privacy.detector',lambda:Cells())
    reviewed_bibliographic_values.cache_clear()
    corpus()
    with pytest.raises(PrivacyError):require_safe_data({'text':'Unreviewed person J8'})


@pytest.mark.presidio_live
def test_real_detector_allows_complete_fn_extraction_request(monkeypatch):
    pytest.importorskip('presidio_analyzer')
    pytest.importorskip('en_core_web_sm')
    from iam_sra.interpretation import EvidenceItem
    from iam_sra.assessment import AssessmentError
    calls=[];real=httpx.Client
    def endpoint(req):
        calls.append(req.url.path)
        return httpx.Response(503,json={'error':'Synthetic unavailable model'})
    monkeypatch.setattr('iam_sra.readiness_client.httpx.Client',lambda **kw:real(transport=httpx.MockTransport(endpoint)))
    text=json.loads(__import__('pathlib').Path('eval/privacy_sample.json').read_text())['citizen_text']
    client=ReadinessClient()
    with pytest.raises(AssessmentError) as error:
        client.extract_readiness({'x':EvidenceItem(id='x',text=text,context='original',source='citizen_original')})
    assert error.value.code=='transport', 'Privacy screening must allow the complete synthetic FN request'
    assert calls==['/tokenize']


@pytest.mark.presidio_live
def test_real_detector_allows_fn_extraction_and_grounding_envelopes(monkeypatch):
    pytest.importorskip('presidio_analyzer')
    pytest.importorskip('en_core_web_sm')
    from test_readiness_evidence_client import install, claim, verdict, evidence
    text=json.loads(__import__('pathlib').Path('eval/privacy_sample.json').read_text())['citizen_text']
    calls=install(monkeypatch,{'interaction':'substantive','claims':[claim(quotation=text)]},[verdict()])
    result=ReadinessClient().extract_readiness(evidence(text))
    assert result.acceptance.stance=='opposed'
    assert [path for path,_ in calls]==['/tokenize','/v1/chat/completions','/tokenize','/v1/chat/completions']


@pytest.mark.presidio_live
def test_all_meeting_cases_real_privacy_end_to_end_with_controlled_extractor():
    pytest.importorskip('presidio_analyzer')
    pytest.importorskip('en_core_web_sm')
    import importlib.util
    from pathlib import Path
    from test_readiness_retrieval import Composer
    spec=importlib.util.spec_from_file_location('meeting_privacy_smoke',Path('scripts/smoke-readiness-evidence.py'))
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    cases=json.loads(Path('eval/meeting_cases.json').read_text())['cases']
    require_safe_data(cases)
    for case in cases:
        for information in (False,True):
            result=runner.run_meeting_case(case,Extractor(stance='not_stated'),Composer(),information=information)
            screened_export(result)
            assert result['actual_output']['state']=='final'
            assert result['actual_output']['numerical_crl'] is None


def test_json_wrapping_cannot_hide_secret_or_contact():
    with pytest.raises(PrivacyError):require_safe_data({'content':json.dumps({'password':'synthetic-secret-xyz'})})
    with pytest.raises(PrivacyError):require_safe_data({'content':json.dumps({'interpretation':'Contact alice@example.com'})})


@pytest.mark.presidio_live
def test_model_json_labels_are_structure_but_prose_is_still_screened():
    pytest.importorskip('presidio_analyzer');pytest.importorskip('en_core_web_sm')
    require_safe_data({'content':json.dumps({'kind':'concern','interpretation':'You are concerned about noise disrupting evening rest.','evidence_id':'R1_1.p001'})})
    with pytest.raises(PrivacyError):require_safe_data({'content':json.dumps({'interpretation':'Email alice@example.com'})})


@pytest.mark.parametrize('setting', [None, '0', '1'])
def test_privacy_is_mandatory_and_environment_cannot_bypass(monkeypatch, setting):
    from iam_sra.privacy import screening_enabled
    if setting is None: monkeypatch.delenv('IAM_PRIVACY_ENABLED', raising=False)
    else: monkeypatch.setenv('IAM_PRIVACY_ENABLED', setting)
    assert screening_enabled()
    with pytest.raises(PrivacyError): require_clean(SECRETS[0])
    with pytest.raises(PrivacyError): require_safe_data({'content': PRIVATE[0]})
