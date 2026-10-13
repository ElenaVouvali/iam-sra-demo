"""Benchmark driver tests use explicit model and detector doubles, not live scores."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
from iam_sra.baseline_benchmark import (HISTORICAL_SHA256, UnsupportedBranch, check_versions,
    file_hash, load_bank, resolve_answer, run_case, semantic_results, structural_results)
from iam_sra.baseline_client import MockBaselineClient
from iam_sra.settings import ROOT
from test_baseline import Extractor, claim

BANK=ROOT/'eval/benchmarks/baseline_adaptive_v3.json'


def bank():return load_bank(BANK)
def case(name):return deepcopy(next(c for c in bank()['cases'] if c['id']==name))
def run(c,client=None):return run_case(c,client or MockBaselineClient(),check_versions(bank()))


def test_historical_bank_unchanged_and_successor_matches_current_policy():
    assert file_hash(ROOT/'eval/benchmarks/baseline_seed_v1.json')==HISTORICAL_SHA256
    assert all(check_versions(bank()).values())
    original=json.loads((ROOT/'eval/benchmarks/baseline_seed_v1.json').read_text())
    assert {c['id'] for c in original['cases']} <= {c['id'] for c in bank()['cases']}


@pytest.mark.parametrize('c',bank()['cases'],ids=lambda c:c['id'])
def test_every_file_driven_empty_fixture_journey_preserves_separate_results(c):
    r=run(c)
    assert r['execution_status']=='completed',r.get('error')
    assert r['routing_pass'] is True
    assert r['invariants_pass'] is True
    assert r['semantic_pass'] is None
    assert r['semantic_review_status']=='pending'
    for phase in r['phases']:
        assert phase['interpretation_errors'] is None
        for e in phase['extraction']:
            assert e['result'] in {None,'not_exercised'}
        assert phase['actual_output']['state']=='complete'
    for turn in r['turns']:
        assert turn['question']['id'] and turn['question']['variant_id']
        assert turn['answer_ref'] in c['answer_sets']
        assert turn['confirmation']['actor'] in {'automation','structured_selection'}


def test_variant_mapping_requires_explicit_equivalence():
    c=case('authority_seminar_no_contribution')
    ref,_=resolve_answer(c,{'id':'experience','variant_id':'organisation_authority'})
    assert ref=='experience'
    with pytest.raises(UnsupportedBranch):resolve_answer(c,{'id':'experience','variant_id':'organisation_operations'})
    with pytest.raises(UnsupportedBranch):resolve_answer(c,{'id':'new_question','variant_id':'personal'})
    c['equivalent_variants']['scope']={'subject':'activity','activity':'subject'}
    with pytest.raises(ValueError):resolve_answer(c,{'id':'scope','variant_id':'subject'})


def test_missing_answer_reports_actual_unsupported_branch_without_fallback():
    c=case('novice_enthusiastic_personal');del c['answer_bindings']['concept']
    r=run(c)
    assert r['execution_status']=='unsupported_benchmark_branch'
    assert r['presented_questions'][-1]['question']['id']=='concept'
    assert len(r['turns'])==1
    assert r['phases'][0]['actual_output']['state']=='interview'


def test_early_stop_leaves_unsupplied_meanings_not_exercised():
    r=run(case('novice_early_stop'));p=r['phases'][0]
    assert len(r['turns'])==2 and p['actual_output']['stop_reason']=='user_finish'
    assert next(e for e in p['extraction'] if e['id']=='meaning_experience')['result']=='not_exercised'
    assert next(e for e in p['extraction'] if e['id']=='meaning_concept')['result'] is None
    assert r['routing_pass']


def test_skipped_and_declined_text_does_not_exercise_extraction():
    r=run(case('novice_skip_and_decline'));p=r['phases'][0]
    assert next(e for e in p['extraction'] if e['id']=='meaning_delivery')['result']=='not_exercised'
    assert next(e for e in p['extraction'] if e['id']=='meaning_understanding')['result']=='not_exercised'


def test_unjustified_omission_is_routing_failure_even_when_evidence_unexercised():
    c=case('novice_early_stop');r=run(c);p=r['phases'][0]
    bad=deepcopy(p['actual_output']);bad['stop_reason']='completed'
    routes,_=structural_results(c,r['turns'],bad,'initial',check_versions(bank()))
    assert next(e for e in routes if e['id']=='core_objectives')['result']=='fail'
    assert next(e for e in p['extraction'] if e['id']=='meaning_experience')['result']=='not_exercised'


def test_role_variant_cannot_be_silently_used_for_personal_respondent():
    c=case('operator_personal_transferable');r=run(c)
    turn=deepcopy(next(t for t in r['turns'] if t['question']['id']=='experience'))
    turn['question']['variant_id']='organisation_operations'
    routes,_=structural_results(c,[turn],r['phases'][0]['actual_output'],'initial',check_versions(bank()))
    assert next(e for e in routes if e['id']=='variant_scope')['result']=='fail'


def test_correction_retains_initial_output_and_uses_consistent_replacement_probes():
    c=case('opponent_corrected_to_listener');r=run(c)
    assert [p['name'] for p in r['phases']]==['initial','corrected']
    initial,corrected=[p['actual_output'] for p in r['phases']]
    assert 'suggested moving' in next(e['text'] for e in initial['events'] if e['question']['id']=='experience')
    replacement=next(e for e in corrected['events'] if e['active'] and e['question']['id']=='experience')
    assert 'did not speak' in replacement['text']
    assert initial['initial_baseline_snapshot']==corrected['initial_baseline_snapshot']
    assert r['phases'][0]['interpretation_errors'] is None
    ref,a=resolve_answer(c,{'id':'contribution','variant_id':'personal'},corrected=True)
    assert ref=='corrected_contribution' and 'did not speak' in a['text']


def test_information_variant_records_exposure_without_prior_knowledge_credit():
    r=run(case('novice_definition_exposure'));p=r['phases'][0]['actual_output']
    assert len(p['information_exposures'])==1 and p['pre_information_snapshots']
    concept=next(t for t in r['turns'] if t['question']['id']=='concept')
    assert 'definition you just showed' in concept['answer']
    assert concept['actual_event']['information_context']=='after_information'


class ContributionClient:
    def extract_baseline(self,evidence,**kwargs):
        q=kwargs['question']['id']
        rows=[claim('participation','contribution',subject='respondent',temporality='actual',domain='transferable',
                    interpretation='Reports a contribution to a bus consultation.',topic_ids=[])] if q=='experience' else []
        return Extractor(rows).extract_baseline(evidence,**kwargs)


def test_actual_selected_probe_gets_its_case_specific_answer():
    c=case('reasoned_opponent_transferable');r=run(c,ContributionClient())
    t=next(t for t in r['turns'] if t['question']['id']=='influence')
    assert t['answer']=='I do not know whether my suggestion changed the bus-route decision.'
    assert t['question']['triggering_evidence_ids']
    assert r['routing_pass'],r['phases'][0]['routing']


def test_evidence_relationship_matching_ignores_generated_wording_and_fixed_ids():
    c=case('reasoned_opponent_transferable');r=run(c,ContributionClient());p=r['phases'][0]
    output=deepcopy(p['actual_output']);output['current_profile']['claims'][1]['interpretation']='A paraphrase.'
    rows=semantic_results(c['expectations']['extraction'],r['turns'],output)
    meaning=next(e for e in rows if e['id']=='meaning_experience')
    assert meaning['candidate_claims'] and meaning['result'] is None


def test_transport_error_retains_preceding_interpretations_and_question():
    class Broken:
        def extract_baseline(self,*args,**kwargs):
            from iam_sra.assessment import AssessmentError
            raise AssessmentError('Unavailable.',code='transport')
    r=run(case('novice_enthusiastic_personal'),Broken())
    assert r['execution_status']=='failed' and r['error']['code']=='transport'
    assert r['turns'][-1]['question']['id']=='concept'
    assert r['phases'][0]['actual_output']['events'][0]['confirmed']


def test_sensitive_fixture_is_not_retained_in_report_or_sent_to_client():
    c=case('novice_enthusiastic_personal');c['answer_sets']['concept']['text']='My PIN is 1234'
    r=run(c)
    assert r['execution_status']=='failed' and r['error']['code']=='privacy'
    assert '1234' not in json.dumps(r)


def test_rejected_context_is_not_retained_in_run_report():
    c=case('authority_seminar_no_contribution');c['context']['function']='My PIN is 1234'
    r=run(c)
    assert r['execution_status']=='failed' and r['error']['code']=='privacy'
    assert r['context'] is None and '1234' not in json.dumps(r)


def test_incompatible_bank_never_calls_model_factory(tmp_path):
    from iam_sra.baseline_benchmark import report
    b=bank();b['target_routing']='different-policy'
    path=tmp_path/'incompatible.json';path.write_text(json.dumps(b))
    def never():raise AssertionError('No client may be created for incompatible versions.')
    result=report(b,path,b['cases'],never)
    assert result['execution_status']=='incompatible_benchmark'
    assert not result['cases'] and result['semantic_pass'] is None


def test_combined_expectation_is_not_reviewable_from_only_one_source():
    c=case('novice_early_stop');r=run(c)
    item=next(e for e in r['phases'][0]['extraction'] if e['id']=='capture_2')
    assert item['source_exercise']=={'concept':True,'delivery':False}
    assert item['result']=='not_exercised'


def test_contextual_benchmark_filename_exception_does_not_exempt_answers():
    from iam_sra.privacy import require_safe_data, PrivacyError
    require_safe_data({'benchmark_path':'eval/benchmarks/baseline_adaptive_v3.json'})
    with pytest.raises(PrivacyError):
        require_safe_data({'benchmark_path':'eval/benchmarks/baseline_adaptive_v3.json',
                           'answer':'My PIN is 1234'})


def test_only_the_current_bound_answer_reaches_the_extractor():
    class Recording:
        def __init__(self):self.calls=[]
        def extract_baseline(self,evidence,**kwargs):
            self.calls.append(deepcopy({'evidence':evidence,**kwargs}))
            return Extractor().extract_baseline(evidence,**kwargs)
    client=Recording();c=case('novice_enthusiastic_personal');r=run(c,client)
    for call in client.calls:
        turn=next(t for t in r['turns'] if t['question']['id']==call['question']['id'])
        # The controller can segment one answer into passages, but no other
        # benchmark answer or expected interpretation enters the model request.
        assert all(text in turn['answer'] for text in call['evidence'].values())
        assert 'expectations' not in call and 'answer_sets' not in call


def test_artifacts_are_separately_screened_versioned_and_hash_linked(tmp_path):
    from iam_sra.baseline_benchmark import report, write_report
    b=bank();data=report(b,BANK,[case('novice_early_stop')],MockBaselineClient,True)
    output=tmp_path/'index.json';index=write_report(data,output)
    path=Path(index['case_reports_directory'])/'novice_early_stop.json'
    artifact=json.loads(path.read_text())
    assert artifact['run_id']==data['run_id'] and artifact['phases']
    # Stable expectation IDs join the versioned bank; author-written expected
    # prose is not duplicated as respondent/session content.
    assert all('meaning' not in e for p in artifact['phases'] for e in p.get('extraction',[]))
    assert index['cases'][0]['artifact_sha256']==file_hash(path)
    next_data=report(b,BANK,[case('novice_early_stop')],MockBaselineClient,True)
    next_index=write_report(next_data,output)
    assert next_index['case_reports_directory']!=index['case_reports_directory'] and path.exists()


def test_unsafe_case_artifact_is_withheld_and_cannot_claim_export_success(tmp_path):
    from iam_sra.baseline_benchmark import report, write_report
    b=bank();data=report(b,BANK,[case('novice_early_stop')],MockBaselineClient,True)
    data['cases'][0]['unsafe_text']='My PIN is 1234'
    index=write_report(data,tmp_path/'index.json')
    assert index['artifact_status']=='incomplete'
    assert index['cases'][0]['artifact_status']=='withheld'
    assert '1234' not in json.dumps(index)
    assert index['cases'][0]['failure_record_status']=='written'
    failure=next(Path(index['case_reports_directory']).glob('*.failure.json'))
    assert '1234' not in failure.read_text()
    assert not list(Path(index['case_reports_directory']).glob('novice_early_stop.json'))


def test_probe_cannot_override_an_explicit_topic_skip():
    from iam_sra.baseline_benchmark import probe_supported
    c=case('reasoned_opponent_transferable');r=run(c,ContributionClient())
    turn=next(t for t in r['turns'] if t['question']['id']=='influence')
    earlier=deepcopy(turn['prior_events'])
    earlier.append({'active':True,'confirmed':True,'control':'skip','interaction':'substantive',
                    'claims':[],'question':{'covers':['influence']}})
    assert not probe_supported(turn['question'],earlier,r['context'])


def test_confirmed_question_repetition_is_a_routing_failure():
    c=case('novice_enthusiastic_personal');r=run(c)
    turn=deepcopy(r['turns'][0]);turn['prior_events']=[turn['actual_event']]
    routes,_=structural_results(c,[turn],r['phases'][0]['actual_output'],'initial',check_versions(bank()))
    assert next(e for e in routes if e['id']=='budgets_and_stop')['result']=='fail'


def test_failed_session_export_cannot_abort_the_remaining_benchmark_cases():
    from iam_sra.baseline_session import BaselineSession
    from iam_sra.privacy import PrivacyError
    class WithheldExport(BaselineSession):
        def export(self):raise PrivacyError('Sensitive content was withheld.')
    r=run_case(case('novice_early_stop'),MockBaselineClient(),check_versions(bank()),WithheldExport)
    assert r['execution_status']=='failed'
    assert r['partial_export_status']=='withheld'
    assert r['phases'][0]['actual_output'] is None
    assert r['invariants_pass'] is False
