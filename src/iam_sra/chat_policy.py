"""Authored conversational objectives with separately registered PDF end scales.

Questions adapt the owner's brief and supplied examples. They are not verbatim
PDF questions or an approved scoring policy. The end scales remain exact extracts.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
from .settings import ROOT

POLICY = 'eva-conversation-prototype-1.2.0'
SCHEMA = 'iam-sra-chat-1.2.0'
PDFS = ['SRAA Citizen interview example 20min.pdf', 'SRAA Citizen interview example 35min.pdf',
        'SRAA Organisation interview example.pdf', 'SRAA Technology interview example.pdf']
WELCOME = ("Hello! I'm an AI assistant for an IAM-CC research conversation about healthcare drone deliveries. "
           "There are no right or wrong answers. You can say you don't know, ask for simpler wording, change topic or stop. "
           "Your answers support a provisional readiness summary at the end. Please avoid names, contact details and sensitive information. "
           "Progress is temporary: download a copy before leaving. "
           "Are you sharing your personal views, speaking about an organisation's responsibilities, or discussing a technology you work with?")
# (id, objective, neutral fallback). Source is the owner's brief, not a PDF quotation.
COMMON = [
 ('perspective', 'Establish an explicitly chosen capacity; never infer it from profession', WELCOME),
 ('area', 'Optional broad city or area; withheld is valid', 'Which city or area would you like to discuss? You can keep this general.'),
]
CITIZEN = [
 ('familiarity', 'Existing drone awareness and use knowledge, before supplied information', 'What have you heard about drones and what they are used for?'),
 ('healthcare', 'Prior healthcare delivery awareness; preserve local uncertainty', 'Have you heard about drones carrying medicines, samples or other medical supplies?'),
 ('open_priorities', 'Spontaneous benefits, concerns and questions before examples', 'What benefits, concerns or questions come to mind for you about healthcare drone deliveries?'),
 ('priorities', 'Let respondent identify two or three priorities in their own words', 'Which two or three of those issues would you most like to talk about?'),
 ('understanding', 'Explain a respondent priority and consequences without testing vocabulary', 'How could the issue that matters most to you affect people in daily life?'),
 ('decision', 'Understand decision-making and meaningful involvement without assuming actual participation', 'How do you think decisions about these services should be made?'),
 ('conditions', 'Reasoned proposed safeguards and decision criteria, distinct from completed activity', 'What would you want planners to consider before deciding whether to use these services?'),
 ('comparison', 'Compare evidence or alternatives; no supplied model answer', 'How would you compare the possible benefits and drawbacks before forming a view?'),
 ('opportunity', 'Experience, opportunity and capability are different; do not presume participation', 'What experience, if any, have you had with discussions, consultations, demonstrations or decisions about healthcare delivery drones?'),
 ('capability', 'Explore capability neutrally when no opportunity, without claiming actual influence', 'If you had an opportunity to give feedback, how would you decide what to tell the people planning the service?'),
 ('influence', 'Ask for contribution-to-change evidence rather than assuming influence', 'If you have given feedback, what do you know about whether it changed any decision? It is fine if you have not.'),
 ('accountability', 'Understanding mechanisms versus actual use; sustained involvement distinct', 'How could people find out whether agreed safeguards are working and raise a concern?'),
 ('continued', 'Extended probe about continued involvement, without claiming it happened', 'What would help you stay involved as plans and services change?'),
 ('opinion', 'Separate stance from readiness evidence', 'Separately from your experience, how do you feel about the idea of healthcare drone deliveries? You may leave this out.'),
]
CITIZEN_EXTENDED = [
 ('affected_groups', 'Explore different effects across affected groups when fairness or access is a priority', 'Who might experience different benefits or burdens, and what would you want decision-makers to consider?'),
 ('evidence_quality', 'Explore how evidence can be checked and whose information is trustworthy', 'How would you judge whether information about noise, safety or delivery benefits is reliable?'),
 ('tradeoffs', 'Probe a concrete comparison of options and competing impacts', 'If two options had different benefits and burdens, what would you compare before recommending one?'),
 ('influence_mechanisms', 'Explore meaningful mechanisms and limits on public influence', 'What would make a way to comment meaningful while the decision can still change?'),
 ('accountability_escalation', 'Explore acknowledgement, response, escalation and remedy', 'If a concern was not resolved, what response or next step would you expect?'),
 ('changing_conditions', 'Explore review when scale, route, purpose or impacts change', 'If the service changed or its impacts increased, what should trigger another review?'),
 ('monitoring', 'Explore continued access to monitoring and follow-up without assuming actual use', 'What information should remain available so people can see whether agreed conditions are working?'),
]
ORGANISATION = [
 ('scope', 'Broad organisation type, own responsibilities and limits; no name needed', 'What kind of organisation or team are you speaking about, and what responsibilities could it have for healthcare deliveries? Please use a general description.'),
 ('org_context', 'Own role in future or existing healthcare logistics', 'How, if at all, could healthcare drone deliveries relate to your team’s work?'),
 ('open_priorities', 'Spontaneous organisational priorities before prompts', 'What opportunities, concerns or preparation needs matter most within your team’s responsibilities?'),
 ('priorities', 'Select a small set within remit', 'Which two or three of those priorities should we explore?'),
 ('requirements', 'Requirements, gaps and regulatory preparedness within own remit', 'What requirements and gaps has your team identified for its own role, including any permissions or rules relevant to that role?'),
 ('plans', 'Draft versus agreed plans, assigned responsibilities and resources', 'What plans, responsibilities or resources are in place so far, and what is still proposed?'),
 ('arrangements', 'Established working arrangements versus intentions', 'Which working arrangements have actually been established within your team’s remit?'),
 ('testing', 'Realistic tests and lessons; a demonstration permission is not routine authority', 'Have those arrangements been tried in realistic conditions, and what did your team learn?'),
 ('integration', 'Embedded normal practice versus one-off pilot', 'How are these arrangements connected to normal work, and what still depends on a special trial?'),
 ('operations', 'Operational preparedness, regulatory boundaries and remaining gaps', 'What would still need to be resolved before your team could perform its role routinely?'),
 ('monitoring', 'Sustained monitoring and adaptation within own remit', 'How would your team monitor its performance and update arrangements over time?'),
]
TECHNICAL = [
 ('scope', 'Object/component versus system; version, environment and expertise limits', 'What technology or component can you discuss, including its version if known, intended use and the limits of your own knowledge? No confidential details are needed.'),
 ('tech_context', 'Object-specific healthcare logistics and environment', 'What function should this object perform, and in what intended environment?'),
 ('open_priorities', 'Spontaneous technical issues within object scope', 'What are the main technical uncertainties or remaining gaps for this object?'),
 ('priorities', 'Select relevant technical issues, not citizen attitudes', 'Which two or three of those issues would be most useful to explore?'),
 ('proof', 'Concept versus proof of concept; evidence of defined function', 'What has actually been built or demonstrated for this configuration so far?'),
 ('controlled', 'Controlled laboratory validation, conditions and outcomes', 'What was tested under controlled conditions, and what did the results show?'),
 ('relevant', 'Representative environment validation and interfaces', 'How closely did those conditions and interfaces represent the intended environment?'),
 ('integrated', 'Component versus integrated demonstration boundary', 'Was the tested object a separate component or part of an integrated system, and what was still missing?'),
 ('operational', 'Operational prototype versus planned demonstration', 'Has this configuration been demonstrated in its intended operational setting, and under what limits?'),
 ('qualification', 'Complete qualification versus demonstration permission', 'What qualification or acceptance work is complete, and what remains unresolved? Please do not share confidential reports.'),
 ('repeated_use', 'Repeated routine use, not isolated demonstration', 'What is known about repeated operational use and performance over time?'),
]


def objectives(profile, depth):
    rows = COMMON + ({'citizen': CITIZEN, 'organisational': ORGANISATION, 'technical': TECHNICAL}.get(profile, []))
    if depth == 'short':
        rows = [r for r in rows if r[0] not in {'continued'}]
    elif profile == 'citizen':
        # Conditional extended probes deepen the respondent-selected issues;
        # controller routing may skip any probe that is not relevant.
        rows = COMMON + CITIZEN[:-2] + CITIZEN_EXTENDED + CITIZEN[-2:]
    document = PDFS[(1 if depth == 'extended' else 0) if profile == 'citizen' else 2 if profile == 'organisational' else 3]
    locators = {'perspective':'pp.1–2', 'area':'pp.2–3', 'scope':'pp.2–4', 'familiarity':'pp.2–4', 'healthcare':'pp.3–4'}
    if profile=='citizen':
        locators.update({'open_priorities':'pp.4–5', 'priorities':'pp.5–6', 'understanding':'pp.6–8', 'conditions':'pp.8–11', 'comparison':'pp.9–12', 'opportunity':'pp.9–10', 'capability':'pp.10–14', 'influence':'pp.13–14' if depth=='extended' else 'pp.10,13–14', 'accountability':'pp.14–15' if depth=='extended' else 'p.11', 'continued':'pp.15–16', 'opinion':'p.16' if depth=='extended' else 'p.12',
                          'affected_groups':'pp.7–9', 'evidence_quality':'pp.10–12', 'tradeoffs':'pp.7–12',
                          'influence_mechanisms':'pp.8–9,13–14', 'accountability_escalation':'pp.14–15',
                          'changing_conditions':'p.15', 'monitoring':'pp.14–15'})
    elif profile=='organisational':
        locators.update({'org_context':'pp.3–6','open_priorities':'p.6','priorities':'p.7','requirements':'pp.8–9','plans':'pp.9–10','arrangements':'pp.10–11','testing':'pp.11–12','integration':'pp.12–13','operations':'pp.13–14','monitoring':'pp.14–15'})
    elif profile=='technical':
        locators.update({'tech_context':'pp.4–6','open_priorities':'pp.8–9','priorities':'pp.8–9','proof':'pp.6–7','controlled':'pp.7–8','relevant':'pp.9–10','integrated':'p.11','operational':'pp.12–13','qualification':'pp.13–14','repeated_use':'pp.14–15'})
    return [{'id': key, 'purpose': purpose, 'question': question,
             'source': {'document': document, 'locator': locators.get(key, 'selected profile interview body and interviewer guidance'),
                        'status': 'authored_adaptation_pending_partner_review', 'policy_version': POLICY}}
            for key, purpose, question in rows]


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
