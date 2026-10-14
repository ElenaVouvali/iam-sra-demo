"""File-driven meeting journeys through the normal conversational controller."""
from copy import deepcopy
import json
from pathlib import Path
import time
import httpx
from .settings import ROOT,BASE_URL,MODEL,config
from .baseline import validate_canonical_source,CanonicalReview,reviewed_canonical
from .baseline_client import BaselineClient,MockBaselineClient
from .baseline_benchmark import provenance,checked_fixture_answer,UnsupportedBranch
from .conversation_planner import PlannerClient
from .conversation_session import ConversationSession
from .privacy import screened_export,PrivacyError,safe_diagnostics
from .readiness_retrieval import ExplanationClient,Composition


def load_cases(path):
    bank=json.loads(Path(path).read_text())
    if bank['schema_version']!='conversation-meeting-cases-1.0.0':raise ValueError('Unsupported meeting case file.')
    return bank


def resolve(case,question):
    ref=case['bindings'].get(question['id'],{}).get(question['variant_id'])
    if ref not in case['answers']:raise UnsupportedBranch('Unsupported meeting branch: '+question['id']+'/'+question['variant_id'])
    answer,preview=checked_fixture_answer(case,ref,case['answers'][ref])
    return ref,answer,preview


class FixtureClient:
    """Authored controlled claims, never a model accuracy result or production path."""
    def __init__(self,case):self.case=case;self.last_diagnostics=[];self.last_metrics={}
    def extract_baseline(self,evidence,*,question,**kwargs):
        ref=self.case['bindings'].get(question['id'],{}).get(question['variant_id'])
        if ref is None:raise UnsupportedBranch('No controlled extraction for this branch.')
        claims=[]
        for row in self.case['answers'][ref]['fixture_claims']:
            from .evidence import original_quote
            eid=next((key for key,text in evidence.items() if original_quote(text,row['span_quote']) is not None),None)
            if eid is None:raise ValueError('A fixture claim is not supported by the supplied answer.')
            claims.append({**row,'evidence_id':eid})
        source=validate_canonical_source({'interaction':'substantive','claims':claims},evidence)
        review=CanonicalReview(decisions=[{'candidate':i,'supported':True,'claim_type':claims[i]['claim_type']} for i in range(len(claims))])
        return reviewed_canonical(source,review,evidence)


class FixtureComposer:
    def compose(self,question,passages):
        return Composition(excerpts=[{'passage_id':p['id'],'quotation':p['text']} for p in passages[:3]])


def run_case(case,client,planner=None,composer=None,collection=None,decline=False):
    s=ConversationSession(collection);context=case['context'];s.set_context(context['perspective'],context['role'],context['city'],function=context.get('function',''))
    turns=[];information_done=False;started=time.monotonic();error=None
    try:
        for _ in range(32):
            if s.stage=='final':break
            if s.stage=='offer':
                if decline:s.decline_scenario()
                else:s.accept_scenario(planner)
            elif s.stage=='final_review':s.confirm_final(actor='automation')
            elif s.phase.state=='baseline_review':
                if s.stage=='general':s.confirm_general(actor='automation')
                else:s.confirm_final(actor='automation')
            elif s.phase.state=='interview':
                q=s.current_question;ref,answer,preview=resolve(case,q);t=time.monotonic()
                s.answer(answer['text'],client,planner,answer['control'])
                turns.append({'sequence':len(turns)+1,'stage':s.stage,'question':deepcopy(q),'answer_ref':ref,
                    'answer':answer['text'],'control':answer['control'],'cleaned_preview_confirmed_by':'automation' if preview else None,
                    'initial_interpretation_before_correction':deepcopy(s.pending['claims']) if s.pending else [],
                    'latency_seconds':round(time.monotonic()-t,3),'diagnostics':safe_diagnostics(deepcopy(getattr(client,'last_diagnostics',[]))),
                    'model_calls':deepcopy(getattr(client,'last_metrics',{}))})
                if s.pending:s.confirm_answer(planner,actor='automation')
                if s.stage=='scenario' and case['optional_information'] and not information_done and s.pending is None:
                    s.ask_information(case['information_question'],composer);s.start_reflection();information_done=True
            else:raise ValueError('Unexpected meeting controller state.')
        else:raise ValueError('Meeting run exceeded its bounded turn limit.')
        before_correction=s.export()
        if case['correction'] and s.scenario and not decline:
            target=next(e for e in s.scenario.events if e['active'] and e['control']=='answer')
            s.edit_answer('scenario',target['id'])
            s.answer(target['text']+case['correction_suffix'],client,planner)
            corrected=deepcopy(s.pending['claims']);s.confirm_answer(planner,actor='automation')
            # Explicit early finish after the corrected response; no unseen
            # follow-up answers or automatic semantic repairs are invented.
            if s.phase.state=='interview':s.finish()
            s.confirm_final(actor='automation')
            turns.append({'stage':'scenario','action':'correction','original_event_id':target['id'],
                'answer':target['text']+case['correction_suffix'],'corrected_interpretation':corrected,'confirmation':'automation'})
        output=s.export()
        invariant={'final_confirmed':s.stage=='final','null_approved_numbers':all(output[k] is None for k in ('numerical_crl','numerical_srl','numerical_orl','numerical_trl')),
            'baseline_scenario_contexts_separate':all(c['context']=='general_baseline' and c['scenario_id'] is None for c in output['baseline']['current_profile']['claims']),
            'general_budget':len([e for e in s.general.events if e['active']])<=8,
            'scenario_budget':not s.scenario or len([e for e in s.scenario.events if e['active']])<=5,
            'initial_snapshot_preserved':output['initial_confirmed_profile']==before_correction['initial_confirmed_profile']}
        status='completed'
    except (ValueError,PrivacyError,RuntimeError,KeyError,TypeError) as exc:
        error={'code':getattr(exc,'code','unsupported_branch' if isinstance(exc,UnsupportedBranch) else 'execution'),
               'privacy_findings':list(getattr(exc,'findings',()))}
        if isinstance(exc,UnsupportedBranch) and s.current_question:
            error['unsupported_question']={'id':s.current_question['id'],'variant_id':s.current_question['variant_id']}
        try:output=s.export()
        except PrivacyError:output=None;error['export_withheld']=True
        invariant={};status='recoverable_partial' if output else 'export_withheld'
    return {'case_id':case['id'],'status':status,'turns':turns,'actual_output':output,
        'checks':invariant,'error':error,'latency_seconds':round(time.monotonic()-started,3),
        'scripted_confirmation':'automation, not actual citizen validation',
        'semantic_review':{'status':'pending_human_review','expected_evidence':case['expected_evidence'],
            'must_not_infer':case['must_not_infer']}}


def run_bank(path,output_path,*,fixtures=False,mock=False,case_ids=None,decline=False):
    bank=load_cases(path);output_path=Path(output_path);output_path.parent.mkdir(parents=True,exist_ok=True)
    report={'schema_version':'conversation-meeting-report-1.0.0','benchmark_version':bank['benchmark_version'],
        'mode':'authored_fixture' if fixtures else 'empty_mock' if mock else 'live_requested',
        'provenance':provenance(bank,path,fixtures or mock),'cases':[],'semantic_review_status':'pending_human_review'}
    report['provenance']['instrument']=config('conversation')['version']
    if not fixtures and not mock:
        try:
            with httpx.Client(timeout=3,trust_env=False) as http:
                response=http.get(BASE_URL.rstrip('/')+'/v1/models');response.raise_for_status()
                if not any(m.get('id')==MODEL for m in response.json().get('data',[])):raise ValueError('Expected served alias unavailable.')
        except (httpx.HTTPError,ValueError):
            report.update(status='blocked_model_endpoint_unreachable',semantic_review_status='not_run')
            output_path.write_text(json.dumps(screened_export(report),indent=2)+'\n');return report
    for case in bank['cases']:
        if case_ids and case['id'] not in case_ids:continue
        client=FixtureClient(case) if fixtures else MockBaselineClient() if mock else BaselineClient()
        try:
            row=run_case(case,client,None if fixtures or mock else PlannerClient(),FixtureComposer() if fixtures or mock else ExplanationClient(),decline=decline)
        except (PrivacyError,ValueError,RuntimeError) as exc:
            report['cases'].append({'case_id':case['id'],'status':'initialisation_blocked',
                'error_code':getattr(exc,'code','source_collection_unavailable'),'export_path':None,
                'privacy_findings':list(getattr(exc,'findings',())),'semantic_review':{'status':'not_run'}})
            continue
        artifact=output_path.with_name(output_path.stem+'-'+case['id']+'.json')
        try:
            if row['actual_output'] is not None:
                artifact.write_text(json.dumps(screened_export(row['actual_output']),ensure_ascii=False,indent=2)+'\n')
            else:artifact=None
            summary={k:v for k,v in row.items() if k!='actual_output'}
            summary['export_path']=str(artifact) if artifact else None
            report['cases'].append(screened_export(summary))
        except PrivacyError as exc:
            report['cases'].append({'case_id':case['id'],'status':'export_withheld','error_code':exc.code,
                'privacy_findings':list(exc.findings),'export_path':None,'semantic_review':{'status':'not_run'}})
        print(json.dumps({'case':case['id'],'status':report['cases'][-1]['status']}),flush=True)
    report['status']='completed' if report['cases'] and all(r['status']=='completed' and all(r['checks'].values()) for r in report['cases']) else 'partial'
    output_path.write_text(json.dumps(screened_export(report),ensure_ascii=False,indent=2)+'\n')
    return report
