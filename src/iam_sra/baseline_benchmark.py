"""File-driven synthetic journeys; structural audit is separate from semantic review.

No benchmark expectation or answer bank is passed to a model. Only the selected
answer goes through the normal screened session/controller/client path.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import re
import subprocess
import time
from importlib.metadata import PackageNotFoundError, version as package_version
from uuid import UUID, uuid4
from .baseline_session import BaselineSession
from .privacy import VERSION, PrivacyError, require_clean, safe_message, screened_export
from .settings import ROOT, config

RUNNER_VERSION = 'baseline-benchmark-2.1.0'
HISTORICAL_SHA256 = 'b35c306764ede2b67f276b68f43addabf564f44dcb2849b3683819cdb415dbcb'


class UnsupportedBranch(ValueError):
    pass


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def load_bank(path):
    bank = json.loads(Path(path).read_text())
    if bank.get('schema_version') != 'adaptive-benchmark-2.0.0':
        raise ValueError('Unsupported benchmark format. Use a schema-versioned adaptive bank; historical banks remain read-only.')
    if len({c['id'] for c in bank['cases']}) != len(bank['cases']):
        raise ValueError('Duplicate benchmark case IDs.')
    for case in bank['cases']:
        if not re.fullmatch(r'[a-z][a-z0-9_]*',case['id']):raise ValueError('Case IDs must be safe lowercase identifiers.')
        for bindings, corrected in [(case['answer_bindings'], False), (case.get('corrected_bindings', {}), True)]:
            for question, variants in bindings.items():
                for variant, ref in variants.items():
                    if ref not in case['answer_sets']: raise ValueError('Unknown answer reference: '+ref)
                    resolve_answer(case, {'id': question, 'variant_id': variant},
                                   corrected=corrected)
        for question, variants in case.get('equivalent_variants', {}).items():
            for variant in variants:
                resolve_answer(case, {'id':question, 'variant_id':variant})
        ids=[e['id'] for group in case['expectations'].values() for e in group]
        if len(ids)!=len(set(ids)): raise ValueError('Duplicate expectation IDs.')
    return bank


def resolve_answer(case, question, corrected=False):
    """Exact ID+variant or an explicitly declared equivalent; never a fallback."""
    qid, variant = question['id'], question.get('variant_id')
    if variant is None: raise UnsupportedBranch('Selected question has no variant: '+qid)
    bindings = case['corrected_bindings'] if corrected else case['answer_bindings']
    aliases = case.get('equivalent_variants', {}).get(qid, {})
    visited=set(); selected=variant
    while selected not in bindings.get(qid, {}):
        if selected in visited: raise ValueError('Cyclic equivalent-variant mapping.')
        visited.add(selected)
        if selected not in aliases:
            raise UnsupportedBranch('No authored answer for '+qid+' / '+variant)
        selected=aliases[selected]
    ref=bindings[qid][selected]
    return ref, deepcopy(case['answer_sets'][ref])


def checked_fixture_answer(case, answer_ref, answer):
    """Only confirm a cleaned preview when the benchmark explicitly expects it."""
    try:
        require_clean(answer['text'])
        return deepcopy(answer), False
    except PrivacyError as exc:
        expected=case.get('privacy_preview_confirmations',{}).get(answer_ref)
        if not expected or not exc.preview or exc.preview!=expected:
            raise
        require_clean(expected)
        cleaned=deepcopy(answer);cleaned['text']=expected
        return cleaned, True


def provenance(bank, path, mock):
    def git(*args):
        return subprocess.check_output(['git',*args], cwd=ROOT, stderr=subprocess.DEVNULL)
    files=[ROOT/'app.py', *sorted((ROOT/'src/iam_sra').glob('*.py')),
           *sorted((ROOT/'configs').glob('*.json')), *sorted((ROOT/'prompts').glob('*.txt')),
           ROOT/'scripts/smoke-baseline.py']
    hashes={str(p.relative_to(ROOT)):file_hash(p) for p in files}
    try:
        head=git('rev-parse','HEAD').decode().strip()
        dirty=bool(git('status','--porcelain'))
    except subprocess.CalledProcessError:
        head=None;dirty=None
    def installed(name):
        try:return package_version(name)
        except PackageNotFoundError:return None
    return {'code_commit':head,'working_tree_dirty':dirty,'file_sha256':hashes,
            'code_snapshot_sha256':sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest(),
            'python':platform.python_version(),'model':config('model'),
            'model_identity_verified':False,'model_mode':'empty_fixture' if mock else 'live_requested',
            'benchmark_path':str(Path(path).resolve().relative_to(ROOT)) if Path(path).resolve().is_relative_to(ROOT) else str(Path(path).resolve()),
            'benchmark_version':bank['benchmark_version'],
            'benchmark_sha256':file_hash(path),'instrument':config('baseline')['version'],
            'instrument_sha256':file_hash(ROOT/'configs/baseline.json'),
            'routing_policy':deepcopy(config('baseline')['routing']),
            'prompt_version':config('baseline')['prompt_version'],
            'prompt_sha256':{k:file_hash(ROOT/f'prompts/baseline-{k}.txt') for k in ['evidence','grounding']},
            'privacy_contract':VERSION,'runner_version':RUNNER_VERSION,
            'inference_settings':{'temperature':0.2,'top_p':0.8,'enable_thinking':False,
                'context_tokens':4096,'stage_output_limits':{'readiness_evidence':1600,'readiness_grounding':1400},
                'guided_decoding_backend':'xgrammar:no-fallback,disable-any-whitespace',
                'attempts_per_stage':2,'stage_deadline_seconds':180},
            'privacy_dependencies':{'presidio_analyzer':installed('presidio-analyzer'),
                'spacy':installed('spacy'),'en_core_web_sm':installed('en-core-web-sm')}}


def check_versions(bank):
    instrument=config('baseline')
    return {'instrument':instrument['version']==bank['target_instrument'],
            'schema':instrument['schema_version']==bank['target_schema'],
            'routing':instrument['routing']['version']==bank['target_routing'],
            'config_hash':file_hash(ROOT/'configs/baseline.json')==bank['target_config_sha256'],
            'historical_bank_unchanged':file_hash(ROOT/'eval/benchmarks/baseline_seed_v1.json')==HISTORICAL_SHA256}


def semantic_results(expectations, turns, snapshot):
    supplied={t['answer_ref'] for t in turns if t.get('submitted') and t['control']=='answer'}
    rows=[]
    for e in expectations:
        exercised=set(e['sources_all'])<=supplied if e.get('sources_all') else bool(supplied.intersection(e['sources_any']))
        related=[t for t in turns if t.get('submitted') and t['answer_ref'] in e['sources_any']]
        event_ids={t.get('event_id') for t in related}
        # Relationships are retrieved by actual source events, never fixed ID strings.
        candidates=[c for c in snapshot['current_profile']['claims'] if c.get('event_id') in event_ids]
        rows.append({**deepcopy(e),'result':None if exercised else 'not_exercised',
                     'review_status':'pending' if exercised else 'not_exercised',
                     'source_exercise':{ref:ref in supplied for ref in e['sources_any']},
                     'supporting_turns':[t['sequence'] for t in related],
                     'candidate_claims':deepcopy(candidates),
                     'review_note':'Review meaning and source scope, including missed or invented claims; no lexical match is a semantic pass.'})
    return rows


# Independent structural requirement checks; deliberately do not call the selector
# or its requirement-state functions to grade their own decisions.
KINDS={'concept':{'concept_explanation'},'delivery':{'use_knowledge'},
       'understanding':{'explained_impact'},'experience':{'learning_exposure','contribution'},
       'needs':{'information_need'},'opportunity':{'opportunity','barrier','intention'}}
DIMS={'concept':{'concept'},'delivery':{'delivery'},'understanding':{'understanding'},
      'experience':{'exposure','participation'},'needs':{'information'},'opportunity':{'opportunity'}}


def applicable_subject(claim, respondent):
    subjects={'respondent','organisation'} if respondent['perspective']=='organisation' else {'respondent'}
    return claim.get('subject') in subjects


def core_justification(q, previous, respondent):
    active=[e for e in previous if e['active'] and e['confirmed']]
    if any(e['question']['id']==q['id'] for e in active): return 'answered'
    if respondent['perspective'] not in q['applicable_perspectives'] or respondent['stakeholder_category'] not in q['applicable_roles']:
        return 'not_applicable'
    if any((e['control'] in {'skip','unsure','decline'} or e.get('interaction') in {'unsure','declined','confused','already_answered'})
           and q['dimension'] in e['question'].get('covers',[]) for e in active): return 'explicit_control'
    claims=[c for e in active for c in e['claims'] if applicable_subject(c,respondent) and not c.get('clarified_by_evidence_ids')]
    for c in claims:
        if c.get('ambiguities'): continue
        if c['dimension'] not in DIMS.get(q['id'],{q['dimension']}): continue
        if c['kind'] in {'absence','unknown'}: return 'explicit_absence_or_unknown'
        if c['status']=='supported' and c['kind'] in KINDS.get(q['id'],set()):
            if q['id']=='experience' and c['temporality']!='actual':continue
            return 'confirmed_claim_structurally_covers'
    return None


def same_scope(a,b):
    if a['subject']!=b['subject']:return False
    if a['domain'] in {'IAM','transferable'} and b['domain'] in {'IAM','transferable'} and a['domain']!=b['domain']:return False
    aa=(a.get('activity_quote') or '').strip().casefold();bb=(b.get('activity_quote') or '').strip().casefold()
    if not aa or not bb or aa!=bb:return False
    if a.get('time_quote') and b.get('time_quote') and a['time_quote'].casefold()!=b['time_quote'].casefold():return False
    return True


def probe_supported(q, previous, respondent):
    if any(e['active'] and e['confirmed'] and q['dimension'] in e['question'].get('covers',[])
           and (e['control'] in {'skip','unsure','decline'} or e.get('interaction') in {'unsure','declined','confused','already_answered'}) for e in previous):return False
    claims=[c for e in previous if e['active'] and e['confirmed'] for c in e['claims'] if applicable_subject(c,respondent)]
    trigger=set(q.get('triggering_evidence_ids',[]))
    candidates=[c for c in claims if c['evidence_id'] in trigger]
    if not candidates:return False
    actual=lambda c:c['status']=='supported' and c['temporality']=='actual'
    if q['id']=='influence':
        return any(actual(c) and c['kind']=='contribution' and not any(
            same_scope(c,d) and (d['dimension']=='influence' or d['dimension']=='participation' and d['kind']=='absence')
            for d in claims) for c in candidates)
    if q['id']=='reasoning':
        return any(c['kind']=='claim_without_detail' and c['status']=='supported' for c in candidates) and not any(c['kind']=='explained_impact' and c['status']=='supported' for c in claims)
    if q['id']=='domain':return any(actual(c) and c['kind'] in {'learning_exposure','contribution'} and c['domain']=='unknown' for c in candidates)
    if q['id']=='contribution':return any(actual(c) and c['kind']=='learning_exposure' and not any(
        d['dimension']=='participation' and d['kind']!='intention' and same_scope(c,d) for d in claims) for c in candidates)
    if q['id']=='scope':
        all_claims=[c for e in previous if e['active'] and e['confirmed'] for c in e['claims']]
        return any(c.get('ambiguities') or c['subject']=='unknown' for c in candidates) or any(
            a['dimension']==b['dimension'] and same_scope(a,b) and actual(a) and b['kind']=='absence'
            for a in candidates for b in all_claims)
    return False


def structural_results(case, turns, snapshot, phase, version_checks, initial_output=None):
    instrument=snapshot['instrument'];respondent=snapshot['respondent_context'];policy=instrument['routing']
    cores=instrument['core_questions'];faults={k:[] for k in ['core_accounting','probe_prerequisites','variant_scope','budgets_and_stop']}
    for t in turns:
        q=t['question'];previous=t['prior_events'];active=[e for e in previous if e['active'] and e['confirmed']]
        if not t.get('editing'):
            if any(e['question']['id']==q['id'] for e in active):faults['budgets_and_stop'].append({'turn':t['sequence'],'reason':'A confirmed question was repeated without an explicit edit.'})
            for core in cores:
                if core['priority']>=q['priority'] and not q['is_probe']:continue
                reason=core_justification(core,previous,respondent)
                # Probes may precede missing cores, subject to reserved slots.
                if not q['is_probe'] and reason is None:
                    faults['core_accounting'].append({'turn':t['sequence'],'question_id':core['id'],'reason':'Missing earlier core omitted without supporting confirmed evidence.'})
            if q['is_probe']:
                if not probe_supported(q,previous,respondent):faults['probe_prerequisites'].append({'turn':t['sequence'],'question_id':q['id']})
                missing=sum(core_justification(core,previous,respondent) is None for core in cores)
                if active and active[-1]['question']['is_probe'] or sum(e['question']['is_probe'] for e in active)>=policy['maximum_probes'] or policy['maximum_questions']-len(active)<=missing:
                    faults['budgets_and_stop'].append({'turn':t['sequence'],'reason':'Probe interleaving, limit or core reservation violated.'})
            if len(active)>=policy['maximum_questions']:faults['budgets_and_stop'].append({'turn':t['sequence'],'reason':'Question presented after budget.'})
        expected='personal' if respondent['perspective']!='organisation' else 'organisation'
        if q['id']=='experience' and expected=='organisation':expected+='_'+policy['role_mapping'][respondent['stakeholder_category']]
        allowed={expected}
        if q['id']=='scope':allowed|={'subject','activity','time','meaning','contradiction'}
        if q['id']=='experience':
            if any(c['kind']=='learning_exposure' and c['status']=='supported' and c['temporality']=='actual' and applicable_subject(c,respondent) for e in active for c in e['claims']):allowed.add('contribution_after_exposure')
        if q['variant_id'] not in allowed:faults['variant_scope'].append({'turn':t['sequence'],'variant':q['variant_id'],'expected':sorted(allowed)})
    active=[e for e in snapshot['events'] if e['active'] and e['confirmed']]
    if snapshot['state']=='complete' and snapshot['stop_reason']=='user_finish' and not case.get('journey',{}).get('finish_after_answers'):
        faults['budgets_and_stop'].append({'reason':'Unexpected early stopping outside the authored journey.'})
    if snapshot['state']=='complete' and snapshot['stop_reason']=='completed':
        for core in cores:
            if core_justification(core,active,respondent) is None:
                faults['core_accounting'].append({'question_id':core['id'],'reason':'Natural stop omitted a missing applicable core.'})
    if snapshot['state']=='complete' and snapshot['stop_reason']=='question_budget' and len(active)<policy['maximum_questions']:
        faults['budgets_and_stop'].append({'reason':'Budget stop before reaching question limit.'})
    if len(active)>policy['maximum_questions'] or sum(e['question']['is_probe'] for e in active)>policy['maximum_probes']:
        faults['budgets_and_stop'].append({'reason':'Final active question/probe count exceeded.'})
    rows=[]
    for e in case['expectations']['routing']:
        if e['check']=='early_finish':
            issues=[] if snapshot['stop_reason']=='user_finish' and len(active)==e['after_answers'] else [{'reason':'Authored early finish was not respected.'}]
        else:issues=faults[e['check']]
        # Incomplete execution cannot establish complete routing correctness.
        result='fail' if issues else 'pass' if snapshot['state']=='complete' else 'not_exercised'
        rows.append({**deepcopy(e),'result':result,'issues':issues,'scope':'structural; evidence sufficiency still needs semantic review'})
    checks={
      'export_context':snapshot['context']=='general_baseline' and snapshot['scenario_id'] is None,
      'null_scores':all(snapshot[k] is None for k in ['numerical_crl','numerical_orl','numerical_trl','numerical_srl']),
      'evidence_relationships':all(c['evidence_id'] in snapshot['evidence'] and c['event_id']==e['id'] and c['question_id']==e['question']['id']
          and c['confirmation_status']=='confirmed' and c['external_verification'] is False for e in snapshot['events'] for c in e['claims']),
      'privacy_contract':snapshot['privacy_contract']==VERSION and snapshot.get('privacy_screening_enabled') is True,
      'versioning':all(version_checks.values()) and snapshot['schema_version']==instrument['schema_version'] and snapshot['routing_version']==instrument['routing']['version'],
      'automation_labels':all(c['actor'] in {'automation','structured_selection'} for c in snapshot['confirmations']) and all(x['actor']=='automation' for x in snapshot['completed_snapshot_history']),
    }
    exposures=snapshot['information_exposures']
    exposure_requested=case.get('journey',{}).get('definition_before')
    checks['exposure_provenance']=bool(exposures) and bool(snapshot['pre_information_snapshots']) and all(x.get('displayed_at') and x.get('version') and x.get('text') for x in exposures) and all(c.get('independent_prior_knowledge') is False for e in snapshot['events'] if e['information_context']=='after_information' for c in e['claims']) if exposures else None if exposure_requested else True
    correction=case.get('journey',{}).get('correction')
    checks['correction_invalidation']=None if phase=='initial' or not correction else bool(snapshot['corrections']) and any(not e['active'] for e in snapshot['events']) and all(c['event_id'] in {e['id'] for e in active} for c in snapshot['current_profile']['claims'])
    if exposures:
        definition=instrument['definition']
        checks['exposure_provenance'] &= all(e['id']==definition['id'] and e['version']==definition['version'] and e['text']==definition['text'] for e in exposures)
    if phase=='corrected' and correction and initial_output is not None:
        target=next(e for e in initial_output['events'] if e['active'] and e['question']['id']==correction['question_id'])
        dependent={e['id'] for e in initial_output['events'] if e['active'] and e['version']>=target['version']}
        checks['correction_invalidation'] &= not dependent.intersection(e['id'] for e in active)
        checks['correction_invalidation'] &= snapshot['initial_baseline_snapshot']==initial_output['initial_baseline_snapshot']
        checks['correction_invalidation'] &= snapshot['completed_snapshot_history'][:len(initial_output['completed_snapshot_history'])]==initial_output['completed_snapshot_history']
    invariants=[{**deepcopy(e),'result':'not_exercised' if checks[e['check']] is None else 'pass' if checks[e['check']] else 'fail'} for e in case['expectations']['invariants']]
    return rows,invariants


def phase_result(case, name, turns, snapshot, versions, initial_output=None):
    expectations=case.get('corrected_extraction',case['expectations']['extraction']) if name=='corrected' else case['expectations']['extraction']
    routing,invariants=structural_results(case,turns,snapshot,name,versions,initial_output)
    extraction=semantic_results(expectations,turns,snapshot)
    return {'name':name,'actual_output':deepcopy(snapshot),'extraction':extraction,
            'routing':routing,'invariants':invariants,'semantic_review_status':'pending',
            'semantic_pass':None,'interpretation_errors':None,
            'interpretation_error_note':'Pending human review of this phase; later correction never erases earlier errors.'}


def run_case(case, client, versions, session_factory=BaselineSession):
    started=time.monotonic();s=session_factory();turns=[];phases=[]
    row={'case_id':case['id'],'context':None,'execution_status':'running',
         'turns':turns,'phases':phases,'actions':[],'presented_questions':[],'semantic_review_status':'pending','semantic_pass':None,
         'confirmation_policy':'automation; not citizen validation, truth verification or semantic approval'}
    def drive(phase):
        count=0
        while s.state=='interview':
            if count>=24:raise UnsupportedBranch('Session did not stop within the benchmark safety limit.')
            if phase=='initial' and case.get('journey',{}).get('finish_after_answers')==count:
                s.finish();row['actions'].append({'action':'finish','phase':phase,'after_answers':count});break
            q=s.current_question
            if q is None:raise UnsupportedBranch('Interview state has no selected question.')
            if phase=='initial' and case.get('journey',{}).get('definition_before')==q['id'] and not s.information_exposures:
                s.show_definition();row['actions'].append({'action':'show_definition','phase':phase,'before_question':q['id']})
            q=s.current_question
            row['presented_questions'].append({'phase':phase,'question':deepcopy(q),'presented_at':datetime.now(timezone.utc).isoformat()})
            ref,answer=resolve_answer(case,q,corrected=phase=='corrected')
            # Apply the same cleaned-preview confirmation flow as the UI. A
            # fixture must explicitly declare the exact expected safe preview.
            row['_active_stage']='answer_input_screening'
            answer,confirmed_preview=checked_fixture_answer(case,ref,answer)
            if confirmed_preview:
                row['actions'].append({'action':'confirm_cleaned_preview','phase':phase,'question_id':q['id'],
                    'answer_ref':ref,'actor':'automation','meaning_review':'not_citizen_validation',
                    'preview_sha256':sha256(answer['text'].encode()).hexdigest()})
            turn={'sequence':len(turns)+1,'phase':phase,'question':deepcopy(q),
                  'answer_ref':ref,'answer':answer['text'],'control':answer['control'],
                  'editing':bool(s._editing),'prior_events':deepcopy(s.events),
                  'presented_at':datetime.now(timezone.utc).isoformat(),'submitted':False}
            turns.append(turn);tick=time.monotonic()
            try:
                row['_active_stage']='interpretation_and_grounding'
                turn['submitted']=True
                s.answer(answer['text'],client,control=answer['control']);turn['processing_completed']=True
                turn['pending_interpretation']=deepcopy(s.pending)
                if s.state=='review':s.confirm(True,actor='automation')
                event=s.events[-1];turn['event_id']=event['id'];turn['actual_event']=deepcopy(event)
                turn['confirmation']=deepcopy(s.confirmations[-1])
                turn['model_diagnostics']=deepcopy(getattr(client,'last_diagnostics',[]))
                turn['model_settings']=deepcopy(getattr(client,'last_settings',{}))
                turn['model_metrics']=deepcopy(getattr(client,'last_metrics',{}))
            finally:
                turn['model_diagnostics']=deepcopy(getattr(client,'last_diagnostics',[]))
                turn.setdefault('model_metrics',deepcopy(getattr(client,'last_metrics',{})))
                turn['latency_seconds']=round(time.monotonic()-tick,4)
            count+=1
        if s.state!='baseline_review':raise UnsupportedBranch('Unexpected session state: '+s.state)
        row['_active_stage']='session_export'
        s.complete(actor='automation');s.handoff()
        snapshot=s.export()
        phase_turns=[t for t in turns if t['phase']==phase]
        # Unchanged earlier answers remain sources in corrected profiles.
        if phase=='corrected':
            active_ids={e['id'] for e in snapshot['events'] if e['active']}
            phase_turns=[t for t in turns if t['phase']==phase or t.get('event_id') in active_ids]
        phases.append(phase_result(case,phase,phase_turns,snapshot,versions,phases[0]['actual_output'] if phase=='corrected' else None))
    try:
        context=case['context'];s.set_context(context['perspective'],context['stakeholder_category'],context['city'],context.get('place',''),context.get('function',''),context.get('sector','none'))
        row['context']=deepcopy(s.respondent)
        drive('initial')
        correction=case.get('journey',{}).get('correction')
        if correction:
            target=next((e for e in s.events if e['active'] and e['question']['id']==correction['question_id']),None)
            if target is None:raise UnsupportedBranch('Correction target was not exercised: '+correction['question_id'])
            previous=s.export();s.edit_answer(target['id'])
            row['actions'].append({'action':'edit_answer','phase':'corrected','question_id':correction['question_id'],
                'replaced_event_id':target['id'],'previous_output_sha256':sha256(json.dumps(previous,sort_keys=True).encode()).hexdigest()})
            drive('corrected')
        row['execution_status']='completed'
    except Exception as exc:
        row['execution_status']='unsupported_benchmark_branch' if isinstance(exc,UnsupportedBranch) else 'failed'
        row['error']={'code':getattr(exc,'code','unsupported_branch' if isinstance(exc,UnsupportedBranch) else 'execution'),
                      'exception_type':type(exc).__name__,'message':safe_message(exc)}
        diagnostics=deepcopy(getattr(client,'last_diagnostics',[]))
        privacy_diag=next((d for d in reversed(diagnostics) if d.get('failure')=='privacy'),None)
        if isinstance(exc,PrivacyError):
            row['failure_stage']=privacy_diag.get('stage') if privacy_diag else row.get('_active_stage','input_or_export_screening')
            row['privacy_boundary']=privacy_diag.get('privacy_boundary') if privacy_diag else row.get('_active_stage','input_or_export_screening')
            if privacy_diag:row['privacy_findings']=list(exc.findings) or list(privacy_diag.get('privacy_findings',[]))
            elif row.get('_active_stage')=='answer_input_screening':
                row['privacy_findings']=[{'field_path':'answer.text',**finding} for finding in exc.findings]
            else:row['privacy_findings']=list(exc.findings)
        if s.respondent is not None:
            name='corrected' if any(a['action']=='edit_answer' for a in row['actions']) else 'initial'
            try:
                snapshot=s.export()
            except PrivacyError as export_error:
                row['partial_export_status']='withheld'
                row['partial_export_error_code']=export_error.code
                if not phases or phases[-1]['name']!=name:
                    expected=case.get('corrected_extraction',case['expectations']['extraction']) if name=='corrected' else case['expectations']['extraction']
                    extraction=semantic_results(expected,[t for t in turns if t['phase']==name],{'current_profile':{'claims':[]}})
                    phases.append({'name':name,'actual_output':None,'actual_output_status':'withheld',
                        'extraction':extraction,'routing':[{**deepcopy(e),'result':'not_exercised','issues':[]} for e in case['expectations']['routing']],
                        'invariants':[{'id':'session_export_screening','result':'fail'}],
                        'semantic_pass':None,'semantic_review_status':'pending','interpretation_errors':None})
            else:
                if not phases or phases[-1]['name']!=name:
                    phases.append(phase_result(case,name,[t for t in turns if t['phase']==name],snapshot,versions))
    row['latency_seconds']=round(time.monotonic()-started,3)
    metrics=[t.get('model_metrics',{}) for t in turns]
    row['model_calls']=sum(m.get('generation_calls',0) for m in metrics)
    row['tokenize_calls']=sum(m.get('tokenize_calls',0) for m in metrics)
    row['cache_hits']=sum(m.get('cache_hits',0) for m in metrics)
    row['model_retries']=sum(request.get('retries',0) for t in turns
        for request in t.get('model_settings',{}).get('request_metrics',[]))
    row.pop('_active_stage',None)
    routing_values=[e['result'] for p in phases for e in p['routing']]
    row['routing_pass']=False if 'fail' in routing_values else True if routing_values and all(v=='pass' for v in routing_values) else None
    row['invariants_pass']=all(e['result']!='fail' for p in phases for e in p['invariants']) if phases else None
    return row


def report(bank,path,cases,client_factory,mock=False,progress=None):
    versions=check_versions(bank);rows=[]
    metadata=provenance(bank,path,mock)
    if not all(versions.values()):
        return {'runner':RUNNER_VERSION,'run_id':str(uuid4()),'provenance':metadata,
                'compatibility':versions,'execution_status':'incompatible_benchmark',
                'semantic_pass':None,'semantic_review_status':'pending','cases':[]}
    for case in cases:
        if progress:progress('started',case['id'])
        row=run_case(case,client_factory(),versions);rows.append(row)
        if progress:progress(row['execution_status'],case['id'])
    return {'runner':RUNNER_VERSION,'run_id':str(uuid4()),'created_at':datetime.now(timezone.utc).isoformat(),
            'provenance':metadata,'compatibility':versions,'mock':mock,
            'execution_status':'completed' if all(r['execution_status']=='completed' for r in rows) else 'incomplete',
            'semantic_pass':None,'semantic_review_status':'pending','cases':rows}


def write_report(data, output):
    """Each respondent is a separate screening boundary and review artifact."""
    output=Path(output)
    run_id=str(UUID(data['run_id']))
    case_directory=output.parent/(output.stem+'_cases')/run_id
    index=deepcopy({k:v for k,v in data.items() if k!='cases'})
    index['case_reports_directory']=str(case_directory)
    index['cases']=[]
    case_directory.mkdir(parents=True,exist_ok=True)
    for row in data['cases']:
        if not re.fullmatch(r'[a-z][a-z0-9_]*',row['case_id']):raise ValueError('Unsafe report case ID.')
        artifact={'run_id':data['run_id'],'benchmark_sha256':data['provenance']['benchmark_sha256'],
                  'provenance':deepcopy(data['provenance']),**deepcopy(row)}
        # Authored expectation prose is kept in the versioned benchmark file
        # and joined by stable expectation ID. Do not duplicate it into a
        # session artifact: the NLP privacy detector can mistake common noun
        # phrases there for PERSON, and the benchmark text is not respondent
        # evidence. Actual outputs and per-expectation outcomes remain here.
        for phase in artifact.get('phases',[]):
            for expectation in phase.get('extraction',[]):
                expectation.pop('meaning',None)
        try:
            screened_export(artifact)
        except PrivacyError as exc:
            # Retain only screened structural failure metadata, not an unsafe
            # failed download. Other respondent artifacts remain independently usable.
            summary={'case_id':row['case_id'],'execution_status':row['execution_status'],
                     'artifact_status':'withheld','export_error_code':getattr(exc,'code','export'),
                     'routing_pass':row['routing_pass'],'invariants_pass':row['invariants_pass'],
                     'semantic_pass':None}
            failure={'schema_version':'baseline-safe-failure-1.0.0','run_id':data['run_id'],
                'case_id':row['case_id'],'execution_status':row['execution_status'],
                'error_code':row.get('error',{}).get('code','export'),
                'failure_stage':row.get('failure_stage','export_screening'),
                'privacy_boundary':row.get('privacy_boundary','export_screening'),
                'privacy_findings':list(exc.findings) or row.get('privacy_findings',[]),
                'latency_seconds':row.get('latency_seconds'),
                'semantic_review_status':'pending','semantic_pass':None}
            try:
                screened_export(failure)
                failure_path=case_directory/(row['case_id']+'.failure.json')
                failure_path.write_text(json.dumps(failure,ensure_ascii=False,indent=2)+'\n')
                summary['failure_record_status']='written'
                summary['failure_record_sha256']=file_hash(failure_path)
            except PrivacyError:
                summary['failure_record_status']='withheld'
            index['cases'].append(summary)
            continue
        target=case_directory/(row['case_id']+'.json')
        target.write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n')
        index['cases'].append({'case_id':row['case_id'],'execution_status':row['execution_status'],
            'artifact_status':'written','artifact_sha256':file_hash(target),
            'routing_pass':row['routing_pass'],'invariants_pass':row['invariants_pass'],
            'semantic_pass':None,'semantic_review_status':'pending'})
    index['artifact_status']='complete' if all(c['artifact_status']=='written' for c in index['cases']) else 'incomplete'
    screened_export(index)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
    return index
