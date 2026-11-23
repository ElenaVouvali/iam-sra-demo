"""FN wording and transparent product adaptations; no approved scoring formula."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
from .settings import ROOT

POLICY = 'fn-adaptive-interview-1.1.0'
SCHEMA = 'iam-sra-chat-2.0.0'
INTRODUCTION = (
    "Thank you for taking part. I'm an AI assistant for this IAM-CC research interview.\n\n"
    "We would like to hear your views and experiences to help us understand how ready society is to use "
    "and engage with new and emerging technologies. In this interview, we will talk about drones and services that use drones.\n\n"
    "There are no right or wrong answers. Your opinions and your own experiences matter. "
    "You can skip any question, pause, correct an answer, stop or withdraw at any time.\n\n"
    "Please avoid personal names, addresses, contact details and sensitive information. Messages are screened "
    "before processing, but screening can miss personal details. Progress is held temporarily in memory; "
    "download a copy if you want to keep it. Contact follow-up and cross-day resume are unavailable."
)
PERSPECTIVE = (
    "Which point of view would you like to use in this conversation?\n\n"
    "A. Citizen\nA member of the public answering from their own point of view. For example, a resident, "
    "patient, service user, worker, member of a community organisation, or anyone who could be affected by drone services.\n\n"
    "B. Organisation or institution\nSomeone answering on behalf of an organisation involved in planning, "
    "providing, regulating, supporting or overseeing drone services. For example, a municipality, regional "
    "authority, regulator, policymaker, city planner, transport authority, healthcare organisation, logistics "
    "organisation or infrastructure provider.\n\n"
    "C. Technology expert or researcher\nSomeone working directly with drone technology or related technical "
    "systems. For example, a drone operator, manufacturer, engineer, researcher, technology developer, "
    "take-off and landing infrastructure developer or airspace-service provider.\n\n"
    "If more than one applies, please choose the perspective you would prefer to use today."
)
WELCOME = INTRODUCTION + '\n\n' + PERSPECTIVE
ACKNOWLEDGEMENTS = {
    'citizen': "Thank you. I will ask the questions from a citizen's point of view.",
    'organisational': 'Thank you. I will ask the following questions from the perspective of your organisation.',
    'technical': 'Thank you. I will ask the following questions from a technical perspective.',
}
CITIZEN_DURATION = (
    "How much time would you like to spend on this conversation?\n\n"
    "A. Around 20 minutes — a shorter conversation focusing on the most relevant issues.\n\n"
    "B. Around 35 minutes — a more detailed conversation exploring selected issues, decision-making, "
    "evidence, participation and influence more deeply.\n\n"
    "If you're not sure, we can use the shorter version. These are interview styles, not deadlines; "
    "you can ask for more detail, shorten, pause or stop later."
)
EASA_BASICS = {
    'id':'easa_basics', 'label':'Read the EASA guide to drones and air mobility',
    'url':'https://www.easa.europa.eu/en/domains/drones-air-mobility/drones-air-mobility-landscape/basics-explained',
}


def citizen_depth_choice(text, letters=False):
    """Administrative choice only; never interprets readiness or profession."""
    import re
    value=text.strip().casefold().rstrip('.!?')
    if letters and value in {'a','b'}:return ('short' if value=='a' else 'extended','participant_choice')
    short=bool(re.search(r'\b(?:20|twenty|short|shorter|brief|less detail)\b',value))
    extended=bool(re.search(r'\b(?:35|thirty[ -]five|extended|longer|detailed|more detail|in depth)\b',value))
    if short != extended:return ('short' if short else 'extended','participant_choice')
    if letters and re.fullmatch(r"(?:i (?:do not|don.t) know|(?:i.m |i am )?not sure(?: how much time)?|unsure|uncertain|(?:i have )?no preference|whatever|default|you choose|either(?: is fine)?)",value):
        return 'short','default_after_uncertainty'
    return None


def educational_choice(text):
    import re
    value=text.strip().casefold().rstrip('.!?')
    negated=bool(re.search(r'\b(?:do not|don.t|not|never)\s+(?:want to )?(?:finish|stop|end|read|open)',value))
    resource=(value in {'resource','the resource','easa','link','the link','the link please'}
        or bool(re.match(r"(?:i(?:.d| would)? (?:like|prefer|rather|want) (?:to )?|please |let.s )?(?:read|open|use|choose)\b.*\b(?:resource|link|guide|easa)\b",value)))
    finish=bool(re.match(r"(?:i (?:want|prefer|choose|would like) to |i.d (?:like to |rather )|i.ll |i will |let.s )(?:finish|stop|end)\b",value))
    if not negated and (value=='b' or re.match(r'b\s*[.:—-]\s+',value) or resource or finish):return 'finish'
    if value in {'no','no thanks','no thank you'} or re.search(r'\b(?:without|no|skip|decline) (?:the |an )?explanation\b|\b(?:don.t|do not) (?:want|need) (?:the |an )?explanation\b',value):return 'skip_explanation'
    if value=='a' or re.match(r'a\s*[.:—-]\s+',value) or re.search(r'\b(?:explanation|explain|continue)\b',value):return 'explain'
    return None


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
