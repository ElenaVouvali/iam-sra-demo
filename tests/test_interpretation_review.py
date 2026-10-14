from copy import deepcopy
import json
import httpx
import pytest
from iam_sra.assessment import AssessmentError
from iam_sra.baseline import BaselineExtraction,BaselineClaim,BaselineDecision,BaselineReview,reviewed
from iam_sra.baseline_client import BaselineClient
from iam_sra.baseline_session import BaselineSession
from iam_sra.privacy import PrivacyError
from test_baseline import Extractor,claim
from test_baseline_ui import start,click


def pending():
    s=BaselineSession();s.set_context('personal','citizen','withheld')
    s.answer('little',Extractor())
    s.answer('An aircraft without a pilot on board.',Extractor([claim('concept','concept_explanation',topic_ids=[])]))
    return s


def test_interpretation_feedback_cannot_replace_the_original_answer_or_passages():
    s=pending();before=deepcopy(s.pending);evidence=deepcopy(s.evidence);client=Extractor([claim('concept','concept_explanation',topic_ids=[])])
    s.correct_interpretation('Keep only my definition; I did not describe impacts.',client)
    assert s.pending['text']==before['text'] and s.pending['id']==before['id']
    assert s.evidence==evidence and len(s.events)==1
    assert client.calls[0]['question']['interpretation_feedback'].startswith('Keep only')
    assert list(client.calls[0]['evidence'].values())==[before['text']]
    assert s.state=='review' and not s.interpretation_reviews[-1]['confirmed']
    s.confirm(True)
    assert s.interpretation_reviews[-1]['confirmed'] and s.events[-1]['text']==before['text']


def test_failed_interpretation_revision_keeps_pending_review_and_original_evidence():
    s=pending();before=deepcopy(vars(s))
    class Broken:
        def extract_baseline(self,*a,**kw):raise AssessmentError('Offline.',code='transport')
    with pytest.raises(AssessmentError):s.correct_interpretation('Please re-read my definition.',Broken())
    assert vars(s)==before


def test_feedback_is_screened_and_cannot_cite_itself_as_original_evidence():
    s=pending();before=deepcopy(vars(s));client=Extractor()
    with pytest.raises(PrivacyError):s.correct_interpretation('My PIN is 1846.',client)
    assert not client.calls and vars(s)==before
    with pytest.raises(AssessmentError):
        s.correct_interpretation('Please revise.',Extractor([claim('concept','concept_explanation',evidence_id='feedback')]))
    assert vars(s)==before


def test_summary_reopens_interpretation_with_same_answer_and_new_provenance():
    s=pending();s.confirm(True);s.finish();original=s.events[-1]['id'];snapshot=s.initial_baseline
    text=s.events[-1]['text'];s.review_interpretation(original)
    assert s.state=='review' and s.pending['text']==text and s.pending['replaces']==original
    assert s.pending['id']!=original
    assert s.events[-1]['active'] is False and s.initial_baseline==snapshot
    s.correct_interpretation('The definition is about aircraft only.',Extractor([claim('concept','concept_explanation',topic_ids=[])]))
    s.confirm(True)
    assert len({e['id'] for e in s.events})==len(s.events)
    assert s.events[-1]['text']==text


def test_blind_review_corrects_spread_absences_instead_of_repeating_them():
    source=BaselineExtraction(interaction='substantive',claims=[BaselineClaim.model_validate(claim(d,'absence',
        evidence_id='p1',interpretation='Unfamiliar with delivery uses.',topic_ids=[]))
        for d in ['concept','delivery','understanding','information','exposure','participation']])
    decisions=BaselineReview(decisions=[BaselineDecision(candidate=i,supported=True,dimension='delivery',kind='unknown',
        interpretation='You are unfamiliar with delivery uses.',subject='respondent',temporality='not_applicable',domain='IAM') for i in range(6)])
    result=reviewed(source,decisions)
    assert len(result.claims)==1 and result.claims[0].dimension=='delivery'
    s=BaselineSession();s.set_context('personal','citizen','withheld');s.answer('little',Extractor());s.answer('I do not know.',Extractor());s.confirm(True)
    s.answer('I have not learned about these deliveries.',Extractor([result.claims[0].model_dump()|{'evidence_id':''}]))
    s.confirm(True)
    assert s.current_question['id']=='understanding'


def test_reviewer_can_correct_personal_belief_subject_and_keep_undetailed_impact():
    source=BaselineExtraction(interaction='substantive',claims=[BaselineClaim.model_validate(claim('delivery','use_knowledge',subject='organisation',topic_ids=[]))])
    d=BaselineDecision(candidate=0,supported=True,dimension='understanding',kind='claim_without_detail',
        interpretation='You expect quicker deliveries, without explaining how.',subject='respondent')
    result=reviewed(source,BaselineReview(decisions=[d])).claims[0]
    assert result.subject=='respondent' and result.kind=='claim_without_detail'


def test_welcome_and_review_hide_redundant_controls_and_preserve_user_text(monkeypatch):
    app=start(monkeypatch,Extractor([claim('concept','concept_explanation',topic_ids=[],interpretation='You describe an uncrewed aircraft.')]))
    assert not any(x.label=='Sector (optional)' for x in app.selectbox)
    click(app,'Begin');app.radio(key='baseline_familiarity').set_value('little');click(app,'Continue')
    assert not any('up to' in x.value for x in app.markdown)
    assert not any('Edit your details' in e.label for e in app.expander)
    app.text_area(key='baseline_answer_text').set_value('An uncrewed aircraft.');click(app,'Continue')
    correction=app.text_area(key=f"baseline_interpretation_{app.session_state.session.pending['id']}_0")
    assert correction.value=='You describe an uncrewed aircraft.'
    correction.set_value('Keep the aircraft definition.');click(app,'Apply my correction')
    assert app.session_state.session.pending['text']=='An uncrewed aircraft.'
    click(app,'Back')
    assert app.text_area(key='baseline_answer_text').value=='An uncrewed aircraft.'


def test_transport_failure_retry_reads_same_visible_draft_without_consuming_question(monkeypatch):
    class Once(Extractor):
        def extract_baseline(self,*a,**kw):
            if not getattr(self,'failed',False):
                self.failed=True;raise AssessmentError('Offline.',code='transport')
            return super().extract_baseline(*a,**kw)
    app=start(monkeypatch,Once());click(app,'Begin');app.radio(key='baseline_familiarity').set_value('little');click(app,'Continue')
    app.text_area(key='baseline_answer_text').set_value('An uncrewed aircraft.');click(app,'Continue')
    assert app.text_area(key='baseline_answer_text').value=='An uncrewed aircraft.'
    assert not any('choose Unsure or Skip' in w.value for w in app.warning)
    assert any(b.label=='Retry this answer' for b in app.button)
    # Existing browser sessions retain the older error string without the new flag.
    app.session_state.baseline_retryable=None;app.run()
    assert any(b.label=='Retry this answer' for b in app.button)
    click(app,'Retry this answer')
    assert app.session_state.session.pending['text']=='An uncrewed aircraft.'


def test_blind_review_payload_hides_extractor_labels(monkeypatch):
    client=BaselineClient();requests=[]
    def request(self,http,stage,system,user,schema,validator):
        requests.append((stage,user))
        if stage=='readiness_evidence':return validator(json.dumps({'interaction':'substantive','claims':[{
            'evidence_id':'x','claim_type':'concept_explanation','span_quote':'An uncrewed aircraft.',
            'interpretation':'You describe an uncrewed aircraft.','subject':'respondent','domain':'IAM','effect_quote':''}]}))
        assert 'dimension' not in user['candidates'][0] and 'kind' not in user['candidates'][0] and 'subject' not in user['candidates'][0]
        return validator(json.dumps({'decisions':[{'candidate':0,'supported':True,'claim_type':'concept_explanation','effect_quote':''}],'additional_claims':[]}))
    monkeypatch.setattr(BaselineClient,'_request',request)
    s=pending();client.extract_baseline({'x':'An uncrewed aircraft.'},question=s.pending['question'],respondent=s.respondent,instrument=s.instrument,prompts=s.prompts)
    assert len(requests)==2


def test_only_the_latest_revised_interpretation_is_confirmed():
    s=pending();s.correct_interpretation('Keep the definition only.',Extractor())
    s.correct_interpretation('Please read the definition again.',Extractor())
    s.confirm(True)
    assert [r['confirmed'] for r in s.interpretation_reviews]==[False,True]


def test_optional_scenario_feedback_preserves_original_answer_and_back_restores_it():
    from iam_sra.readiness_session import ReadinessSession
    from test_readiness_evidence_mode import Extractor as Reader, record
    s=ReadinessSession();s.submit('Aircraft sound could disturb rest.',Reader([record()]))
    before=s.pending['text'];event_id=s.pending['id']
    s.correct_interpretation('I described a possible effect, not an actual measurement.',Reader([record()]))
    assert s.pending['text']==before and s.pending['id']==event_id
    assert s.back()==before and s.state=='answer'


@pytest.mark.presidio_live
def test_real_detector_allows_original_answer_bound_interpretation_feedback():
    pytest.importorskip('presidio_analyzer');pytest.importorskip('en_core_web_sm')
    s=pending()
    s.correct_interpretation('This describes a definition, not an observed effect.',
        Extractor([claim('concept','concept_explanation',topic_ids=[],interpretation='You describe an aircraft without a pilot.')]))
    s.confirm(True);s.finish();s.complete()
    result=s.export()
    assert result['interpretation_reviews'][-1]['original_answer_unchanged']
    assert result['schema_version']=='iam-baseline-2.3.1'
