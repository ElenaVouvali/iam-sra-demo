"""Researcher views derived from real audits, never alternative assessment logic."""
from copy import deepcopy


def evidence_report(data):
    from .privacy import VERSION, PrivacyError, require_safe_data
    if data.get('privacy_contract') != VERSION:
        raise PrivacyError('This older export predates local privacy screening. Start a new synthetic session; the original file is unchanged.')
    require_safe_data(data)
    if data.get('assessment_mode') != 'acceptance_and_readiness_evidence':
        raise ValueError('Historical acceptance sessions are not readiness evidence.')
    citations = data['evidence']; rows = []
    displayed_text = []
    for exposure in data.get('information_exposures', []):
        content = exposure.get('content', {})
        displayed_text.extend(content.get('paragraphs', []))
        displayed_text.extend(e['quotation'] for e in content.get('excerpts', []))
    import re
    displayed_text = [sentence.strip() for text in displayed_text for sentence in re.split(r'(?<=[.!?])\s+', text) if sentence.strip()]
    for stage in ['initial_readiness_profile', 'final_readiness_profile']:
        profile = data.get(stage)
        for r in (profile or {}).get('records', []):
            rows.append({'snapshot':stage, 'quotations':[{'id':eid, 'text':citations[eid]['text']}
                for eid in r['evidence_ids'] if eid in citations],
                'interpretation':r['interpretation'], 'criterion':r['criterion_id'], 'topics':r['topic_ids'],
                'kind':r['kind'], 'status':r['status'], 'temporality':r['temporality'],
                'experience_domain':r['experience_domain'], 'proposal_context':r['proposal_context'],
                'elicitation_context':r['elicitation_context'], 'evidence_basis':r['evidence_basis'],
                'confirmation':r['confirmation_status'], 'external_truth_verified':False,
                'uncertainty':r.get('unresolved_contradictions', []),
                'scope_clarification_required':profile['criterion_coverage'][r['criterion_id']]['status']=='scope_clarification_required',
                'claim_subject':r.get('claim_subject',''), 'time_scope':r.get('time_scope',''),
                'information_relation': ('exact_repetition_detected' if any(' '.join(citations[eid]['text'].split()) == ' '.join(text.split()) for eid in r['evidence_ids'] if eid in citations for text in displayed_text) else 'post_information_independence_not_established') if r['elicitation_context']=='after_information_exposure' else 'no_exposure_recorded_before_answer',
                'caution':'Reported experience/belief or answer-demonstrated reasoning; not independently verified fact.'})
    return {'report_version':'1.1.0', 'privacy_contract':data['privacy_contract'], 'session_id':data['session_id'], 'instrument_version':data['instrument']['version'],
        'rows':rows, 'changes':deepcopy(data.get('readiness_changes')),
        'conditional_proposal_views':deepcopy(data['acceptance_profile']['optional_hypothetical_findings']),
        'coverage':deepcopy((data.get('final_readiness_profile') or data.get('initial_readiness_profile') or {}).get('criterion_coverage', {})),
        'information_exposures':deepcopy(data.get('information_exposures', [])),
        'information_acknowledgements':deepcopy(data.get('information_acknowledgements', [])),
        'confirmations':deepcopy(data.get('confirmations', [])),
        'corrections':deepcopy(data.get('corrections', [])),
        'note':'Additional answers refine assessment. Conditional acceptance and post-information reasoning are distinct; no personal development is inferred.'}


def markdown_report(data):
    report = evidence_report(data)
    lines = ['# Researcher evidence report', '', report['note'], '',
             'Confirmation checks meaning; all experience claims remain self-report unless separately verified.', '']
    for row in report['rows']:
        lines += [f"## {row['snapshot']} · {row['criterion']}", '',
                  'Quoted answer: ' + ' / '.join(q['text'] for q in row['quotations']), '',
                  'Interpretation: ' + row['interpretation'], '',
                  f"Status: {row['status']}; kind: {row['kind']}; context: {row['proposal_context']}, {row['elicitation_context']}; basis: {row['evidence_basis']}; confirmation: {row['confirmation']}.", '',
                  'Topics: ' + ', '.join(row['topics']), '', 'Information relation: ' + row['information_relation'], '', row['caution'], '']
    lines += ['## Coverage and remaining uncertainty', '']
    lines += [f"- {cid}: {item['status']} (asked: {item['asked']})" for cid,item in report['coverage'].items()]
    changes = report.get('changes') or {}
    lines += ['', '## Changes', '', f"New records: {len(changes.get('newly_recorded_evidence', []))}; superseded initial interpretations: {len(changes.get('clarified_or_corrected_interpretations', []))}; post-information records: {len(changes.get('after_information_evidence', []))}.", '',
              f"Corrections: {len(report['corrections'])}; information displays: {len(report['information_exposures'])}; reading acknowledgements: {len(report['information_acknowledgements'])}."]
    result = '\n'.join(lines) + '\n'
    from .privacy import require_clean
    require_clean(result)
    return result


def fn_reference():
    """Fixed source reference, kept out of citizen profiles and inference prompts."""
    import json
    from .settings import ROOT
    reference = json.loads((ROOT/'eval/fn_reference.json').read_text())
    return {'label':'FN concept example — historical illustrative scoring',
        'source_scores':reference['scores'], 'source_pages':reference['source_pages'],
        'source_sha256':reference['source_sha256'], 'reference_version':reference['reference_version'],
        'arithmetic':'(8 + 3 + 4 + 2) / 4 = 4.25; privacy cap = 2 + 2 = 4; min(4.25, 4) = 4',
        'source_citizen_text':reference['citizen_text'],
        'differences':[
            'Medical-purpose support does not establish equity knowledge.',
            'Low altitude and camera concerns alone do not necessarily establish visual pollution.',
            'Rerouting preferences do not establish participation or infrastructure expertise.',
            'Follow-up outcomes describe directions/ranges, not a universal executable update formula.',
            'The PDF later mentions an average of 6.0, inconsistent with its initial 4.25; preserved as a source limitation.',
            'Psychological/archetype labels in the concept are not used as citizen diagnoses.'],
        'current_model_output':None, 'current_model_output_status':'Not run; reference numbers are not actual model outputs.'}
