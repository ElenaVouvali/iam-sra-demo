"""Logic regression doubles are not validation of live model semantics."""
from copy import deepcopy
import json
import pytest
from iam_sra.session import Session,State
from iam_sra.reporting import citizen_summary,clarification_needs
from iam_sra.interpretation import reconcile_original
from iam_sra.updates import FacetMeaning,modified_facets,facet_availability
from test_confirmation import Fake,meaning,initially_scored
from test_updates import answer_all,FacetFake


def profile():
    m=meaning(scores=('noise','perceived_safety_privacy','welfare_equity'),facets={'perceived_safety_privacy':['personal_privacy'],'welfare_equity':['medical_public_benefit']})
    m.concerns[-1].position='supported'
    m.medical_public_benefit_support.interpretation='supported';m.medical_public_benefit_support.excerpts=['O.p001'];m.medical_public_benefit_support.rationale='You support lifesaving medical deliveries.'
    return m


class ContextFake(Fake):
    def interpret(self,evidence,*args,**kwargs):
        result=super().interpret(evidence,*args,**kwargs)
        for dim in [result.awareness_understanding,result.medical_public_benefit_support]:
            if dim.interpretation!='unassessed':dim.excerpts=[next(iter(evidence))]
        return result


def ready():
    s,c=initially_scored(ContextFake(profile()));s.begin_followups();answer_all(s,c)
    return s,c


def test_joint_acceptance_keeps_tested_choices_and_explicit_unchanged_benefit():
    s,c=ready();original=deepcopy(s.initial)
    s.record_joint('accept',[],'',c,['welfare_equity:medical_public_benefit'])
    assert all(facet_availability(s,f) for f in s.facet_meanings)
    assert {(f.facet,f.position) for f in s.facet_meanings}=={('personal_privacy','supported'),('acoustic_impact','supported'),('medical_public_benefit','supported')}
    privacy=next(f for f in s.facet_meanings if f.facet=='personal_privacy')
    assert any(s.evidence[r].source=='citizen_prior_gate' and s.evidence[r].question_id=='q1' for r in privacy.evidence_ids)
    assert s.joint['history_links'] and not clarification_needs(s)
    s.continue_final(True,c)
    assert s.conditional['aggregate']['trace']['denominator']==3 and s.initial==original
    assert not citizen_summary(s)['remaining_objections']
    assert s.export()['schema_version']=='5.3.0'


def test_no_implicit_inheritance_of_untested_medical_meaning():
    s,c=ready();s.record_joint('accept',[],'',c)
    assert not facet_availability(s,next(f for f in s.facet_meanings if f.facet=='medical_public_benefit'))
    assert any(n['facet']=='medical_public_benefit' and n['context']=='modified' for n in clarification_needs(s))


def test_equity_uncertainty_preserves_medical_support_and_original_score():
    s,c=initially_scored(Fake(profile()));s.begin_followups();s.stop_followups()
    patch=meaning('C1.testimony',scores=('welfare_equity',),position='uncertain',facets={'welfare_equity':['distributive_equity']})
    c.next=patch;s.correct('welfare_equity','I am unsure whether underserved areas benefit fairly.','Clarify equity only.',c)
    assert s.original_facets['welfare_equity:medical_public_benefit'].position=='supported'
    assert s.original_facets['welfare_equity:distributive_equity'].position=='uncertain'
    welfare=next(x for x in s.draft.concerns if x.concern_id=='welfare_equity')
    assert welfare.position=='supported' and welfare.facets==['medical_public_benefit']
    s.continue_final(True,c)
    assert next(x['score'] for x in s.final['assessment']['concerns'] if x['concern_id']=='welfare_equity')==8
    assert any('medical purpose' in line for line in citizen_summary(s)['lines'])


def test_broad_uncertainty_does_not_erase_previously_distinct_meanings():
    original=profile();_,ledger=reconcile_original(None,original,{})
    patch=meaning('D.text',scores=('welfare_equity',),position='uncertain',facets={'welfare_equity':['medical_public_benefit','distributive_equity']})
    result,ledger=reconcile_original(original,patch,ledger)
    assert ledger['welfare_equity:medical_public_benefit'].position=='supported'
    assert ledger['welfare_equity:distributive_equity'].position=='uncertain'


def test_metadata_sufficiency_cannot_erase_scoped_concern_evidence():
    from test_discovery import DiscoveryFake
    from iam_sra.discovery import DiscoveryFacts
    c=DiscoveryFake(profile());c.facts=DiscoveryFacts(reasons_explicit=False)
    s=Session();s.begin();s.submit('I support saving lives but object to hum and private cameras.',c)
    assert len(s.draft.concerns)==3 and s.discovery_question['kind']!='reasons'


def test_established_positions_have_no_redundant_original_check():
    s,c=initially_scored(Fake(profile()));s.begin_followups()
    assert not any(q['id'].startswith('u_original_') for q in s.questions)
    assert all(q['contract']['selection_reason'] for q in s.questions)


def test_edit_completed_gate_invalidates_results_keeps_initial_and_old_evidence():
    s,c=ready();s.record_joint('accept',[],'',c,['welfare_equity:medical_public_benefit']);s.continue_final(True,c)
    initial=deepcopy(s.initial);old=s.evidence['q1.choice'];old_confirmations=len(s.confirmations)
    s.rewind('q1')
    assert s.state==State.FOLLOWUPS and s.current_question['id']=='q1'
    assert s.final is None and s.conditional is None and s.updated_confirmed is None and s.joint is None
    assert s.initial==initial and s.evidence['q1.choice']==old and len(s.confirmations)==old_confirmations
    s.respond(s.current_question['choices'][-1],'',c)
    assert s.responses[-1]['evidence_ids'][1]=='q1.v2.choice'
    assert s.revision_history[0]['snapshots']['conditional_modified'] is not None


def test_edit_initial_answer_preserves_immutable_snapshot_and_testimony():
    s,c=ready();initial=s.initial;old=s.evidence['O.p001'];s.rewind('initial_answer')
    c.initial=meaning(scores=('noise',),position='supported')
    s.submit('The original hum is fine with me.',c);s.finish_discovery();s.continue_initial(True,c)
    assert s.initial==initial and s.evidence['O.p001']==old and 'O2.p001' in s.evidence
    assert all(r not in s.responses for r in s.revision_history[0]['answers'])


def test_privacy_does_not_resolve_safety_or_security():
    m=profile();m.concerns[1].facets=['personal_privacy','perceived_safety']
    s,c=initially_scored(Fake(m));s.begin_followups();answer_all(s,c)
    s.record_joint('accept',[],'',c,['welfare_equity:medical_public_benefit'])
    facts={f.facet:f for f in s.facet_meanings}
    assert facet_availability(s,facts['personal_privacy']) and not facet_availability(s,facts['perceived_safety'])
    assert any(n['facet']=='perceived_safety' for n in clarification_needs(s))


def test_no_question_nomination_from_q1_or_q2_assumptions():
    s,c=ready()
    assert all(not r.get('choice_meaning') or not any(x['concern_id'] in {'visual_pollution','technical_safety_security_privacy'} for x in r['choice_meaning']['concerns']) for r in s.responses)


@pytest.mark.parametrize('cid,kind', [('infrastructure_land_use','flight_routing_only'),('visual_pollution','private_space_viewing_only')])
def test_independent_attribution_excludes_false_positive_generic_scope(monkeypatch,cid,kind):
    from iam_sra.conversation_client import ConversationClient
    from iam_sra.interpretation import EvidenceItem
    from test_client import fake_client
    mapped=meaning('O.p001',scores=(cid,));mapped.awareness_understanding.interpretation='unassessed'
    responses=[mapped.model_dump(),{'supported':True,'rationale':'Generic reviewer falsely accepted this inference.'}, {'kind':kind,'rationale':'The statement is only a routing/privacy condition.'}]
    choices=[{'finish_reason':'stop','message':{'content':json.dumps(d)}} for d in responses]
    calls=fake_client(monkeypatch,choices)
    client=ConversationClient();result=client.interpret({'O.p001':EvidenceItem(id='O.p001',text='Please reroute away from homes so cameras cannot look into my windows.',context='original',source='citizen_original')})
    assert result.concerns==[] and client.last_candidate_projections[-1]['supported'] is False
    assert 'candidate' not in json.loads(calls[-1][1]['messages'][1]['content'])


def test_scope_exclusion_cannot_survive_as_required_modified_topic(monkeypatch):
    from iam_sra.conversation_client import ConversationClient
    from iam_sra.interpretation import EvidenceItem
    from test_client import fake_client
    raw=meaning('O.p001',scores=('infrastructure_land_use',))
    fake_client(monkeypatch,[{'finish_reason':'stop','message':{'content':raw.model_dump_json()}},{'finish_reason':'stop','message':{'content':json.dumps({'supported':False,'rationale':'No land or facility claim.'})}}])
    assert ConversationClient().interpret({'O.p001':EvidenceItem(id='O.p001',text='Move the flights away from homes.',context='original',source='citizen_original')}).concerns==[]


def test_new_joint_question_only_nomination_does_not_create_a_requirement():
    s,c=ready()
    c.next=meaning('J1.choice',scores=('infrastructure_land_use',))
    s.record_joint('accept',[],'',c,['welfare_equity:medical_public_benefit'])
    assert not any(cid=='infrastructure_land_use' for cid,f in modified_facets(s))


def test_completed_initial_edit_removes_superseded_topic_scores_in_final():
    s,c=ready();s.record_joint('unsure',[],'',c);s.continue_final(True,c)
    initial=s.initial;s.rewind('initial_answer');c.initial=meaning(scores=('noise',),position='supported')
    s.submit('I accept the noise.',c);s.finish_discovery();s.continue_initial(True,c)
    while s.state==State.FOLLOWUPS:s.skip_followup()
    s.continue_final(True,c)
    assert s.initial==initial
    assert all(x['score'] is None for x in s.final['assessment']['concerns'] if x['concern_id']!='noise')


def test_completed_modified_edit_retains_other_established_facet():
    c=FacetFake(meaning(scores=('perceived_safety_privacy',),facets={'perceived_safety_privacy':['personal_privacy','perceived_safety']}))
    s,c=initially_scored(c);s.begin_followups();answer_all(s,c);s.record_joint('accept',[],'I accept privacy and physical safety under the changes.',c)
    c.positions={'personal_privacy':'supported','perceived_safety':'supported'}
    before=deepcopy(next(f for f in s.facet_meanings if f.facet=='personal_privacy'))
    c.next=meaning('M1.testimony',scores=('perceived_safety_privacy',),position='uncertain',facets={'perceived_safety_privacy':['perceived_safety']})
    c.positions={'perceived_safety':'uncertain'}
    s.correct_modified('perceived_safety_privacy','I am unsure about physical safety.','Only safety changed.',c)
    assert next(f for f in s.facet_meanings if f.facet=='personal_privacy')==before


def test_completed_ui_has_one_summary_and_editable_answers(monkeypatch):
    from test_ui import fresh,click,assert_simple
    app=fresh(monkeypatch,ContextFake(profile()));click(app)
    app.text_area(key='citizen_answer').set_value('I support medical deliveries but oppose noise and cameras.');click(app)
    click(app,'Finish these questions');app.checkbox(key='confirm_1').check().run();click(app)
    s=app.session_state.session
    while s.state==State.FOLLOWUPS:
        q=s.current_question
        assert not any(r.label=='Your added words describe' for r in app.radio)
        app.radio(key='choice_'+q['id']).set_value(q['choices'][0]);click(app);assert_simple(app)
    app.radio(key='joint_choice').set_value('accept')
    app.radio(key='applies_welfare_equity:medical_public_benefit').set_value('yes');click(app)
    lines=' '.join(e.value for e in app.markdown)
    assert 'You support its medical purpose' in lines and 'would accept the route' in lines
    assert not any('boundary' in e.value or 'facet' in e.value for e in app.markdown)
    app.checkbox(key='updated_confirm_'+str(s.version)).check().run();click(app,'Confirm and finish')
    assert len(app.metric)==1 and s.export()['final_summary']['selected_profile']=='conditional_modified'
    initial=s.initial;click(app,'Edit your first answer')
    assert s.state==State.ANSWER and s.final is None and s.initial==initial
    assert app.text_area(key='citizen_answer').value=='I support medical deliveries but oppose noise and cameras.'


def test_back_to_previous_question_preserves_answer_draft(monkeypatch):
    from test_ui import fresh,click
    app=fresh(monkeypatch,ContextFake(profile()));click(app)
    app.text_area(key='citizen_answer').set_value('I object to the hum.');click(app);click(app,'Finish these questions')
    app.checkbox(key='confirm_1').check().run();click(app)
    s=app.session_state.session;q=s.current_question
    app.radio(key='choice_'+q['id']).set_value(q['choices'][0]);click(app)
    click(app,'← Back to previous question')
    assert s.current_question['id']==q['id'] and app.radio(key='choice_'+q['id']).value==q['choices'][0]
    assert s.initial is not None and s.joint is None


def test_discovery_answer_revision_uses_new_evidence_ids_and_same_question():
    from test_discovery import DiscoveryFake
    c=DiscoveryFake(meaning(scores=()));s=Session();s.begin();s.submit('I reject.',c)
    q=s.discovery_question;s.respond_discovery(['noise'],'',c)
    old=s.evidence[q['id']+'.selection1'];s.rewind(q['id'])
    assert s.discovery_question['text']==q['text']
    s.respond_discovery(['perceived_safety_privacy'],'',c)
    assert s.evidence[q['id']+'.selection1']==old
    assert s.discovery_responses[-1]['evidence_ids']==[q['id']+'.v2.selection1']


def test_correction_choice_requires_explanation():
    s,c=initially_scored(Fake(meaning(scores=('cost_roi_business',))));s.begin_followups()
    q=s.current_question
    from iam_sra.assessment import AssessmentError
    with pytest.raises(AssessmentError):s.respond(q['choices'][1],'',c)
    assert not s.responses and s.initial is not None


def test_explicit_broad_unsure_edit_requires_scope_without_erasing_clear_support():
    s,c=initially_scored(Fake(profile()));s.begin_followups();s.stop_followups()
    c.next=meaning('C1.testimony',scores=('welfare_equity',),position='uncertain',facets={'welfare_equity':['medical_public_benefit','distributive_equity']})
    s.correct('welfare_equity','I am unsure about welfare and equity.','Clarify uncertainty.',c)
    assert s.original_facets['welfare_equity:medical_public_benefit'].position=='supported'
    assert 'original:welfare_equity' in s.conflicts
    with pytest.raises(ValueError):s.confirm_updated(True)


def test_rejected_medical_scope_is_not_renominated_via_root_dimension(monkeypatch):
    from iam_sra.conversation_client import ConversationClient
    from iam_sra.interpretation import EvidenceItem
    from test_client import fake_client
    raw=profile();raw.concerns=raw.concerns[-1:]
    fake_client(monkeypatch,[{'finish_reason':'stop','message':{'content':raw.model_dump_json()}}, {'finish_reason':'stop','message':{'content':json.dumps({'supported':False,'rationale':'Citizen recognized hospital purpose but did not endorse it.'})}}])
    client=ConversationClient();mapped=client.interpret({'O.p001':EvidenceItem(id='O.p001',text='The route is for the hospital.',context='original',source='citizen_original')})
    normalized,ledger=reconcile_original(None,mapped,{})
    assert not normalized.concerns and not ledger and normalized.medical_public_benefit_support.interpretation=='unassessed'


def test_root_medical_display_agrees_with_preserved_facet_after_equity_uncertainty():
    original=profile();_,ledger=reconcile_original(None,original,{})
    patch=meaning('C1.testimony',scores=('welfare_equity',),position='uncertain',facets={'welfare_equity':['distributive_equity']})
    result,ledger=reconcile_original(original,patch,ledger,explicit=True)
    assert result.medical_public_benefit_support.interpretation==ledger['welfare_equity:medical_public_benefit'].position=='supported'


def test_unknown_original_aspect_is_visible_in_domain_export_without_erasing_score():
    s,c=ready();s.record_joint('unsure',[],'',c)
    c.next=meaning('C1.testimony',scores=('welfare_equity',),position='uncertain',facets={'welfare_equity':['distributive_equity']})
    s.correct('welfare_equity','I do not know whether benefits reach underserved areas.','Add equity uncertainty.',c)
    s.continue_final(True,c)
    data=s.export();domain=next(d for d in data['domain_assessments'] if d['concern_id']=='welfare_equity')
    assert {f['facet']:f['position'] for f in domain['original_aspect_meanings']}=={'medical_public_benefit':'supported','distributive_equity':'uncertain'}
    assert domain['profiles']['final_original']['score']==8
    assert data['dialogue_and_confirmations']['interpretation_versions'][-1]['original_facet_meanings']


def test_remaining_topic_selection_does_not_establish_a_numeric_position():
    s,c=ready();s.record_joint('accept',['noise'],'',c)
    key='J1.remaining'
    f=FacetMeaning(concern_id='noise',facet='acoustic_impact',position='opposed',evidence_ids=[key],applicability_explicit=True,rationale='A topic was selected, without severity.')
    assert not facet_availability(s,f)


def test_full_original_acceptance_correction_removes_superseded_conditions():
    m=meaning();m.concerns[0].conditional_willingness='willing';m.concerns[0].conditions=['O.p001'];m.acceptance_conditions=['O.p001']
    class ConditionFake(Fake):
        def interpret(self,evidence,*args,**kwargs):
            first=self.next is None
            result=super().interpret(evidence,*args,**kwargs)
            if first and all(v.source=='citizen_original' for v in evidence.values()):
                result.concerns[0].conditions=[next(iter(evidence))]
                result.acceptance_conditions=[next(iter(evidence))]
            return result
    c=ConditionFake(m);s,c=initially_scored(c);s.begin_followups();s.stop_followups()
    c.next=meaning('C1.testimony',position='supported')
    s.correct('noise','I now accept the original sound without any change.','Clarify sound acceptance.',c)
    assert not s.draft.concerns[0].conditions and not s.draft.acceptance_conditions
    assert s.draft.concerns[0].conditional_willingness=='not_stated'
