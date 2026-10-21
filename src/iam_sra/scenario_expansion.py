"""Explicit adaptation of six private draft cases into the existing scenario bank."""
from copy import deepcopy
from hashlib import sha256
import json
from .settings import ROOT, config
from .questionnaire import load_questionnaire, VERSION
from .privacy import require_clean,PrivacyError

VERSION_SCENARIOS='2026-10-21-v0.1'
TOPICS=['sump_integration','infrastructure_land_use','energy_emissions','cost_roi_business',
        'accessibility','multimodality_congestion','noise','visual_pollution','perceived_safety_privacy',
        'technical_safety_security_privacy','wind_downwash','airspace_capacity','welfare_equity',
        'public_awareness_trust','competence_building']


def expansion_cards(value, questionnaire, register, root=ROOT):
    """Validate mappings and report differing/missing originals without inventing matches."""
    spec=register['scenario_expansion_v01'];originals={r['document']:r for r in register['sources']}
    if (value.get('schema_version')!='iam-sra-scenario-expansion-0.1.0'
            or value.get('scenario_bank_version')!=VERSION_SCENARIOS
            or value.get('compatible_questionnaire_version')!=questionnaire['questionnaire_version']):
        raise ValueError('Incompatible scenario expansion/questionnaire version.')
    cases=value['scenarios']
    if len(cases)!=6 or {c['id'] for c in cases}!={f'expansion-{n:02d}' for n in range(1,7)}:
        raise ValueError('Expected six distinct expansion cases.')
    packages={s['id']:s for s in value['source_register']}
    if set(packages)!=set(spec['source_resolution']):raise ValueError('Unresolved scenario source identities.')
    sources=[];references={}
    used_sources={r['source_id'] for case in cases for r in case['source_refs']}
    for key,entry in packages.items():
        resolution=spec['source_resolution'][key];name=resolution['local_document']
        ref={'source_id':key,'package_document':entry['document'],'package_sha256':entry['sha256'],
             'verification_status':resolution['status'],'verification_note':resolution['verification_note']}
        if name:
            local=originals.get(name)
            if not local or not (root/local['local_path']).is_file():raise ValueError('Registered scenario original unavailable: '+name)
            actual=sha256((root/local['local_path']).read_bytes()).hexdigest()
            if actual!=local['sha256']:raise ValueError('Registered scenario source changed: '+name)
            equal=actual==entry['sha256']
            if (resolution['status']=='verified_hash')!=equal or resolution['status'] not in {'verified_hash','local_text_checked_binary_differs'}:
                raise ValueError('Scenario source verification status does not match its hashes.')
            ref.update(local_document=name,local_sha256=actual)
            if key in used_sources:sources.append({'document':name,'path':local['local_path'],'sha256':actual})
        elif resolution['status']!='original_missing':raise ValueError('Missing source must remain explicitly unverified.')
        references[key]=ref
    module_keys={(m['indicator_id'],m['profile']) for m in questionnaire['modules']}
    base=config('baseline');cards=[]
    for case in cases:
        summary=case['source_basis_summary'];redacted=False
        try:require_clean(summary)
        except PrivacyError as exc:
            if exc.preview is None:raise
            summary=exc.preview;require_clean(summary);redacted=True
        ids=case['indicator_ids']
        if not ids or len(set(ids))!=len(ids) or any((key,profile) not in module_keys for key in ids for profile in ('citizen','organisational','technical')):
            raise ValueError('Scenario routing indicator does not exist in questionnaire v0.2.')
        if case['approved_by'] is not None or not case['significant_unknowns'] or not case['text'].strip():
            raise ValueError('Draft cases require unknowns and cannot acquire approval during import.')
        refs=[]
        for item in case['source_refs']:
            if item['source_id'] not in references or not item['locator'].strip():raise ValueError('Unknown scenario source/locator.')
            refs.append({**deepcopy(references[item['source_id']]),'locator':item['locator']})
        verification=('unverified_draft_adaptation' if all(r['verification_status']=='original_missing' for r in refs) else
            'partly_verified_draft_adaptation' if any(r['verification_status']=='original_missing' for r in refs) else 'locally_checked_draft_adaptation')
        city={'expansion-01':'coimbra','expansion-02':'milan','expansion-03':'madrid'}.get(case['id'],'illustrative')
        cards.append({'id':case['id'],'type':'scenario','title':case['title'],'version':case['version'],
            'scenario_bank_version':VERSION_SCENARIOS,'locale':case['locale'],'city':city,'area':case['area'],
            'text':case['text'],'unknowns':deepcopy(case['significant_unknowns']),
            'source_status':case['source_status'],'source_verification':verification,'source_refs':refs,
            'source':{'document':spec['document'],'sha256':spec['json_sha256'],'version':VERSION_SCENARIOS,
                'locator':'scenario '+case['id'],'source_status':'authored_draft_adaptation'},
            'facts':{'context_status':case['source_status'],'current_operations':'not_established',
                'scenario_reasoning_is_not_actual_activity':True},
            'illustrative_assumptions':['Discuss the supplied situation as an illustration; no local operation or personal experience is established.'],
            'applicability':{'perspectives':list(base['perspectives']),'roles':list(base['stakeholders'])},
            'indicator_ids':ids,'topic_ids':[TOPICS[int(key.split('-')[1])-1] for key in ids],
            'target_criterion':'contextual_application','situation_family':case['id'],
            'opening_question':case['opening_question'],'conditional_followup':deepcopy(case['conditional_followup']),
            'wording_origin':case['wording_origin'],'derivation':'Supplied draft paraphrase and newly drafted reflection prompts; not verbatim original extraction.',
            'source_basis_summary':summary,'summary_privacy_redacted':redacted,'review_status':case['review_status'],'approved_by':None,
            'permitted_use':['illustrative_scenario','researcher_reference'],
            'search_text':case['title']+' '+case['area']+' '+' '.join(ids)})
    return cards,sources


def load_expansion():
    register=json.loads((ROOT/'references/source-register.json').read_text());spec=register['scenario_expansion_v01']
    path=ROOT/spec['local_path'];raw=path.read_bytes()
    if sha256(raw).hexdigest()!=spec['json_sha256']:raise ValueError('Scenario configuration differs from its registered hash; review the input.')
    cards,sources=expansion_cards(json.loads(raw),load_questionnaire(),register)
    sources.append({'document':spec['document'],'path':spec['local_path'],'sha256':spec['json_sha256']})
    q=register['questionnaire_v02'];qpath='references/private/questionnaire-v0.2/'+q['document']
    if sha256((ROOT/qpath).read_bytes()).hexdigest()!=q['json_sha256']:raise ValueError('Questionnaire configuration changed; review and restart.')
    sources.append({'document':q['document'],'path':qpath,'sha256':q['json_sha256']})
    identity={'version':VERSION_SCENARIOS,'json_sha256':spec['json_sha256'],
        'resolution_sha256':sha256(json.dumps(spec['source_resolution'],sort_keys=True).encode()).hexdigest(),
        'questionnaire_sha256':q['json_sha256']}
    return cards,sources,identity


def presented_card(card):
    keys=('id','title','version','scenario_bank_version','text','unknowns','source','source_refs','source_status',
          'source_verification','illustrative_assumptions','indicator_ids','facts','opening_question','conditional_followup','wording_origin','city')
    return {k:deepcopy(card[k]) for k in keys if k in card}
