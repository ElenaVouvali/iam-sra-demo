"""Offline and live synthetic interviews through the normal controller."""
from copy import deepcopy
from hashlib import sha256
import json
import time
from uuid import uuid4
from .settings import ROOT,config
from .conversation_session import ConversationSession
from .conversation_planner import PlannerClient
from .conversation_corpus import load_corpus
from .synthetic_respondent import ScriptedRespondent,LLMRespondent,load_personas
from .baseline_client import BaselineClient,MockBaselineClient
from .privacy import screened_export,safe_diagnostics,safe_message,PrivacyError


def synthetic_collection():
    """Small authored controller fixture; never represents a reviewed source corpus."""
    baseline=config('baseline');policy=config('conversation');questions=[]
    source={'document':'synthetic-evaluation-fixture','locator':'authored test-only question',
        'sha256':'synthetic-fixture','version':'synthetic-fixture-1.0.0'}
    for q in baseline['core_questions']+baseline['probes']:
        variants=dict(q['variants'])
        if q.get('when_exposure_already_reported'):variants['contribution_after_exposure']=q['when_exposure_already_reported']
        for variant,text in variants.items():
            questions.append({'id':'test_'+q['id']+'_'+variant,'question_id':q['id'],'variant_id':variant,
                'stage':'general','locale':'en','applicability':{'perspectives':list(baseline['perspectives']),
                'roles':list(baseline['stakeholders'])},'revised_wording':text,'wording_options':[text],
                'source':source,'search_text':str(q['dimension'])+' '+text,'permitted_use':['planner']})
    for q in policy['scenario_questions']:
        for variant in ('personal','organisation'):
            text=q[variant]
            questions.append({'id':q['id']+'_'+variant,'question_id':q['id'],'variant_id':variant,
                'stage':'scenario','locale':'en','applicability':{'perspectives':list(baseline['perspectives']),
                'roles':list(baseline['stakeholders'])},'revised_wording':text,'wording_options':[text],
                'source':source,'search_text':q['criterion']+' '+text,'permitted_use':['planner']})
    scenario=config('scenario')
    card={'id':scenario['id'],'version':'synthetic-fixture-1.0.0',
        'text':scenario['text'].split(' How do you feel')[0],'facts':scenario['illustrative_context'],
        'unknowns':['Current operating status and local measurements are not established.'],
        'topic_ids':list(scenario.get('target_concerns',[])),
        'locale':'en','source':source,'applicability':{'perspectives':list(baseline['perspectives']),
        'roles':list(baseline['stakeholders'])}}
    return {'version':'conversation-corpus-1.1.0','questions':questions,'scenarios':[card],
        'explanations':[p for p in config('readiness_corpus')['passages'] if 'citizen_explanation' in p['permitted_use']],
        'sources':[source],'coverage':{'status':'synthetic_test_fixture_not_source_validated'}}


def _summary(results,bank,seed_set,backend,model_calls):
    completed=sum(r['status']=='completed' for r in results)
    attempts=sum(r['planner_metrics']['attempts'] for r in results)
    selected=sum(r['planner_metrics']['successful_model_selections'] for r in results)
    fallbacks=sum(r['planner_metrics']['deterministic_fallbacks'] for r in results)
    recommendations=[]
    failure_classes={}
    for run in results:
        exp=run.get('session_export') or {}
        plans=exp.get('planning_actions',[]) or [t['planner_decision'] for t in run.get('turns',[]) if t.get('planner_decision')]
        for plan in plans:
            key=plan.get('failure_class')
            if key:failure_classes[key]=failure_classes.get(key,0)+1
    if fallbacks:recommendations.append({'component':'conversation_planner.py','invariant':'valid selected objective or labelled authored fallback',
        'observed_fallbacks':fallbacks,'failure_classes':failure_classes,'action':'Review failures by class and question objective; do not weaken validation to improve the rate.'})
    if any(r.get('repeated_question_count',0) for r in results):recommendations.append({'component':'conversation_session.py','invariant':'avoid repeating completed objectives',
        'action':'Inspect repeated question transcripts and route suppression.'})
    if completed<len(results):recommendations.append({'component':'synthetic_runner.py','invariant':'failed or incomplete sessions remain visible',
        'action':'Inspect safe error codes and unsupported branches; do not count incomplete sessions as complete.'})
    recommendations.append({'component':'human semantic review','invariant':'claim meaning, neutrality and concern preservation',
        'action':'Review pending expected observations against original synthetic answers and confirmed exports.'})
    return {'report_version':'synthetic-conversation-evaluation-1.0.0',
        'benchmark_version':bank['benchmark_version'],
        'backend':backend,'synthetic_only':True,'seed_set':list(seed_set),
        'runs':len(results),'completed_runs':completed,'failed_runs':len(results)-completed,
        'completion_rate':completed/len(results) if results else None,
        'planner_attempts':attempts,'model_selections':selected,'fallbacks':fallbacks,
        'planner_selection_rate':selected/attempts if attempts else None,
        'model_calls':model_calls,'semantic_accuracy':None,
        'repeated_question_count':sum(r.get('repeated_question_count',0) for r in results),
        'root_cause_recommendations':recommendations,
        'interpretation':'Completion and controller metrics are not readiness or semantic-accuracy results.',
        'provenance':{'file_sha256':{'synthetic_persona_bank':sha256(json.dumps(bank,sort_keys=True).encode()).hexdigest()}},
        'limitations':['No synthetic run is a real stakeholder response.',
            'Scripted offline mode uses empty extraction fixtures; it cannot measure semantic interpretation.',
            'Using Qwen for both simulated respondent and interviewer does not provide independent validation.']}


def run_evaluation(output,persona_ids=None,repetitions=1,seed_set=(11,),backend='scripted',offline=False,
                   policy_version='1.2',synthetic_fixture=False):
    bank=load_personas();personas=bank['personas'];wanted=set(persona_ids or [p['persona_id'] for p in personas])
    unknown=wanted-{p['persona_id'] for p in personas}
    if unknown:raise ValueError('Unknown persona IDs: '+', '.join(sorted(unknown)))
    if repetitions<1 or repetitions>10:raise ValueError('Repetitions must be between one and ten.')
    seeds=list(seed_set)
    if not seeds:raise ValueError('At least one fixed seed is required.')
    if offline and not synthetic_fixture:
        raise ValueError('Offline runs require --synthetic-fixture; no private source corpus is substituted.')
    collection=synthetic_collection() if synthetic_fixture else load_corpus()
    from .conversation_session import ConversationSession
    run_id=str(uuid4());root=ROOT/output if not output.is_absolute() else output
    root.mkdir(parents=True,exist_ok=True)
    results=[];calls=0
    for persona in personas:
        if persona['persona_id'] not in wanted:continue
        for repeat in range(repetitions):
            for seed in seeds:
                started=time.monotonic();s=ConversationSession(collection)
                s.set_context(persona['perspective'],persona['stakeholder_role'],persona['city'])
                responder=ScriptedRespondent(persona,seed) if backend=='scripted' else LLMRespondent(persona)
                client=MockBaselineClient() if offline else BaselineClient()
                planner=None if offline else PlannerClient()
                s.instrument['planner_policy_version']=policy_version
                turns=[];status='incomplete';error=None
                history=[]
                try:
                    for _ in range(32):
                        if s.stage=='final':status='completed';break
                        if s.stage=='offer':
                            if persona['scenario_preference'].startswith('decline'):s.decline_scenario()
                            else:s.accept_scenario(planner)
                        elif s.stage=='final_review':s.confirm_final(actor='automation')
                        elif s.phase.state=='baseline_review':
                            if s.stage=='general':s.confirm_general(actor='automation')
                            else:s.confirm_final(actor='automation')
                        elif s.phase.state=='interview':
                            q=deepcopy(s.current_question)
                            if q['format']=='selection':
                                level=persona['knowledge_level']
                                value={'heard_term_only':'term','low':'little','limited':'little','acoustics':'lot',
                                    'planning':'little','operational_general':'little','regulatory_general':'little',
                                    'moderate':'little','some':'little','healthcare_context':'little'}.get(level,'unsure')
                                answer={'text':value,'control':'answer'}
                            else:answer=responder.respond(q,history)
                            before=len(getattr(client,'last_diagnostics',[]));turn_started=time.monotonic()
                            s.answer(answer['text'],client,planner,answer['control'])
                            turn={'sequence':len(turns)+1,'stage':s.stage,'question':q,
                                'synthetic_answer':answer['text'],'control':answer['control'],
                                'interpretation':deepcopy(s.pending['claims']) if s.pending else [],
                                'latency_seconds':round(time.monotonic()-turn_started,3),
                                'planner_decision':deepcopy(s.plans[-1]) if s.plans and s.plans[-1].get('sequence') else None,
                                'diagnostics':safe_diagnostics(getattr(client,'last_diagnostics',[])[before:])}
                            turns.append(turn);history.append({'question':q['question_text'],'answer':answer['text']})
                            if s.pending:
                                s.confirm_answer(planner,actor='automation')
                                turn['confirmation']={'confirmed':True,'actor':'automation','outcome':'synthetic_scripted_review'}
                            else:turn['confirmation']={'confirmed':True,'actor':'structured_selection','outcome':'structured_choice'}
                        else:raise ValueError('Unexpected controller state: '+s.state)
                    else:raise RuntimeError('Synthetic interview exceeded its bounded turn count.')
                    if s.stage=='final_review':s.confirm_final(actor='automation')
                    if s.stage!='final':status='incomplete'
                    try:export=s.export()
                    except Exception:export=None
                except Exception as exc:
                    error={'code':getattr(exc,'code','runtime_error'),'type':type(exc).__name__,'message':safe_message(exc)}
                    try:export=s.export()
                    except Exception:export=None
                    status='failed'
                client_calls=getattr(client,'session_metrics',{}).get('generation_calls',0)
                planner_calls=getattr(planner,'session_metrics',{}).get('generation_calls',0) if planner is not None else 0
                responder_calls=getattr(responder,'session_metrics',{}).get('generation_calls',0)
                session_calls=client_calls+planner_calls+responder_calls
                calls+=session_calls
                record={'run_id':run_id,'persona_id':persona['persona_id'],'persona_version':persona['persona_version'],
                    'synthetic':True,'seed':seed,'repetition':repeat+1,'policy_version':policy_version,
                    'model_version':config('model')['model'],'scenario_id':s.card['id'] if s.card else None,
                    'status':status,'error':error,'duration_seconds':round(time.monotonic()-started,3),
                    'turns':turns,'planner_metrics':export.get('planner_metrics',{}) if export else {},
                    'objective_coverage':sorted({p.get('objective_id') for p in export.get('planning_actions',[]) if p.get('objective_id')}) if export else [],
                    'semantic_review':'pending_human_review','semantic_results':None,
                    'manual_reference_expectations':deepcopy(persona['expected_observations']),
                    'backend':responder.backend,'model_calls':session_calls,
                    'repeated_question_count':len([t['question']['question_text'] for t in turns
                        if t.get('question')])-len(set(t['question']['question_text'] for t in turns if t.get('question'))),
                    'question_quality_status':'semantic_judgement_not_run',
                    'evidence_invariant_status':'not_scored_with_empty_fixture' if offline else 'pending_review',
                    'model_latency_seconds':sum(x.get('latency_seconds',0) for x in (
                        getattr(client,'session_metrics',{}),getattr(planner,'session_metrics',{}),getattr(responder,'session_metrics',{})))}
                results.append(record)
                artifact=root/f"{persona['persona_id']}-r{repeat+1}-s{seed}.json"
                if export is not None:
                    session_artifact=root/f"session-{len(results):04d}.json"
                    try:
                        synthetic_export=deepcopy(export)
                        synthetic_export.update(synthetic=True,data_classification='SYNTHETIC_TEST_ONLY',
                            persona_id=persona['persona_id'],persona_version=persona['persona_version'],
                            evaluation_run_id=run_id,evaluation_seed=seed,policy_version=policy_version)
                        session_artifact.write_text(json.dumps(screened_export(synthetic_export),ensure_ascii=False,indent=2)+'\n')
                        record['session_export_file']=session_artifact.name
                    except PrivacyError:
                        record['artifact_status']='withheld_by_privacy';record['session_export_file']=None
                try:serializable=screened_export(record)
                except PrivacyError as exc:
                    # Fail closed: retain a minimal screened diagnostic record,
                    # never bypass screening or write the blocked transcript.
                    record.update(artifact_status='withheld_by_privacy',turns=[],
                        error={'code':'privacy_export_withheld','details_withheld':True})
                    serializable=screened_export({k:record[k] for k in (
                        'run_id','persona_id','persona_version','synthetic','seed','repetition',
                        'policy_version','model_version','status','artifact_status','backend')})
                else:record['artifact_status']='screened'
                artifact.write_text(json.dumps(serializable,ensure_ascii=False,indent=2)+'\n')
    summary=_summary(results,bank,seeds,backend,calls);summary['policy_version']=policy_version
    summary['implementation_commit']=s.provenance.get('code_commit') if results else None
    summary['model_provenance']=deepcopy(config('model'))
    summary['provenance']=deepcopy(s.provenance) if results else {}
    (root/'summary.json').write_text(json.dumps(screened_export(summary),ensure_ascii=False,indent=2)+'\n')
    (root/'evaluation-results.jsonl').write_text(''.join(json.dumps(screened_export(r),ensure_ascii=False,separators=(',',':'))+'\n' for r in results))
    lines=['# Synthetic conversational assessment evaluation','',
        'Internal synthetic controller test only; this is not stakeholder data, population readiness, or validation.','',
        f"- Policy: {policy_version}; benchmark: {bank['benchmark_version']}",
        '- Implementation commit and dirty-tree flag, model/revision, corpus/configuration hashes: see summary.json provenance fields.',
        f"- Runs: {summary['runs']}; completed: {summary['completed_runs']}; failed: {summary['failed_runs']}",
        f"- Planner selections: {summary['model_selections']}; fallbacks: {summary['fallbacks']}; attempts: {summary['planner_attempts']}",
        f"- Model calls: {calls}; semantic accuracy: not scored",'',
        '## Root-cause recommendations','']+[f"- {r['component']}: {r['action']}" for r in summary['root_cause_recommendations']]+[
        '','## Limitations','']+[f'- {v}' for v in summary['limitations']]
    from .privacy import require_clean
    markdown='\n'.join(lines)+'\n';require_clean(markdown)
    (root/'summary.md').write_text(markdown)
    return summary
