"""Authored conversational objectives with separately registered PDF end scales.

Questions adapt the owner's brief and supplied examples. They are not verbatim
PDF questions or an approved scoring policy. The end scales remain exact extracts.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
from .settings import ROOT

POLICY = 'fn-adaptive-interview-1.0.0'
SCHEMA = 'iam-sra-chat-2.0.0'
WELCOME = ("Hello! I'm an AI assistant for an IAM-CC research conversation about drones and healthcare deliveries. "
           "There are no right or wrong answers. You may skip, pause, correct, stop or withdraw at any time. "
           "Please avoid names, addresses, contact details and sensitive information. Messages are screened; "
           "progress is temporary, so download a copy to keep it. "
           "The short citizen conversation is the default; type ‘extended conversation’ for more depth.\n\n"
           "Which point of view would you like to use in this conversation?\n"
           "A — Citizen\nB — Organisation or institution\nC — Technology expert or researcher\n"
           "If more than one applies, please choose the perspective you would prefer to use today.")


def objectives(profile, depth):
    """The single FN specification also supplies retrieval/fallback provenance."""
    from .fn_interview import specification, flow_key
    key = flow_key(profile, depth)
    stages = specification()['flows'].get(key, [])
    if not stages: return []
    source = load_rubrics()[1]['sources'][key]
    return [{'id':s['id'], 'purpose':s['purpose'],
             'question':s['questions'][0]['canonical_question'],
             'source':{**deepcopy(source), 'locator':s['source_locator'],
                       'status':'prototype pending partner review', 'policy_version':POLICY}}
            for s in stages]


def load_rubrics():
    register = json.loads((ROOT/'references/chat-source-register.json').read_text())
    for row in register['sources'].values():
        if sha256((ROOT/'references/private'/row['document']).read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Interview PDF differs from its reviewed source identity.')
    raw = (ROOT/register['derived']['path']).read_bytes()
    if sha256(raw).hexdigest() != register['derived']['sha256']:
        raise ValueError('Extracted interview anchors differ from their reviewed identity.')
    scales = json.loads(raw)
    for key, anchors in scales.items():
        if len(anchors)!=9 or [a['level'] for a in anchors]!=list(range(1,10)) or any(a['id']!=key+'-'+str(a['level']) or not a['description'] for a in anchors):
            raise ValueError('Incomplete interview scale.')
    return scales, register


def rubric(bank, profile, depth):
    scales, register = load_rubrics()
    key = 'citizen_'+depth if profile=='citizen' else profile
    return {'policy_version': POLICY, 'rubric_version': register['version'],
            'status': 'supplied_example_prototype_pending_partner_review',
            'anchors': deepcopy(scales[key]), 'source': deepcopy(register['sources'][key]),
            'reference_scale': deepcopy(bank['generic_scales'][{'citizen':'CRL','organisational':'ORL','technical':'TRL'}[profile]]),
            'reference_source': deepcopy(bank['source']),
            'reference_notice': 'The interview scale is shown below. The legacy workbook remains a separate reference.',
            'guidance': {
              'citizen': 'The full meanings are capability-oriented through discussion, safeguards and evaluation; no blanket past-participation gate. No opportunity does not establish inability. The example result nevertheless distinguishes communicating a possible argument from actual contribution to a changed decision (20min pp.13–14; 35min pp.18–19). For influence, established mechanisms and sustained involvement, distinguish demonstrated capability, opportunities, reported actual effects and continued activity; explain remaining uncertainty or abstain. Level 9 is Sustained involvement, unlike v4 Sustained agency. No acceptance/trust/fluency bonus.',
              'organisational': 'Assess only the stated unit responsibilities. Distinguish draft plans, prepared arrangements, realistic testing with lessons, adoption into ordinary processes, routine operational readiness and sustained monitoring. Permission for a demonstration does not establish routine compliance (pp.11–17,19–20).',
              'technical': 'Assess the same object/configuration, not the respondent or a different integrated system. Distinguish experimental proof, controlled validation, representative validation, integrated demonstration, operational prototype, complete qualification and proven operational use. A mature component or demonstration permission cannot establish whole-system qualification (pp.6–15,18–23).'
            }[profile]}
