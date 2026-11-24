"""Opt-in FN-guided adaptive interviewing helpers.

No maturity inference here: only explicit conversational information needs,
plainly enumerated priorities and natural presentation. The original answers,
FN evidence bank and controller retain authority.
"""
import os
import re


def enabled():
    return os.getenv('IAM_CHAT_ADAPTIVE_MODE', '0').strip().lower() in {'1', 'true', 'yes'}


def max_wordings(depth):
    default = '12' if depth == 'short' else '18'
    try:
        return max(0, min(30, int(os.getenv('IAM_CHAT_MAX_ADAPTIVE_QUESTIONS', default))))
    except ValueError:
        return int(default)


def optional_topic_probes_unneeded(concerns):
    """Avoid suggested topic inventory after two real respondent-raised topics.

    Suggestions with no original evidence are not respondent-raised concerns.
    """
    found = set()
    for row in concerns:
        if row.get('evidence_ids') and (row.get('spontaneously_raised') or row.get('selected_priority')):
            found.add(row['topic'].casefold().strip())
    return len(found) >= 2


def explicit_priority_list(answer):
    """Conservative repair of plainly enumerated first-clause priority choices.

    Never infer concerns from arbitrary discussion; otherwise return [].
    Examples: 'Noise and wildlife disturbance. I would need more evidence.'
    """
    first = re.split(r'[.?!;\n]', answer.strip(), maxsplit=1)[0].strip()
    if not first or len(first) > 180:
        return []
    first = re.sub(
        r'^(?:my (?:main )?(?:issues|priorities|concerns) (?:are|would be)|'
        r'i (?:would |would rather |want to )?(?:choose|pick|focus on)|'
        r'i care (?:most )?about|for me[, ]+|mostly|mainly)\s*[:,-]?\s*',
        '', first, flags=re.I)
    if re.search(r'\b(?:not sure|don.t know|do not know|maybe|perhaps|whether|if|because|why|how|could you|would you)\b', first, re.I):
        return []
    parts = re.split(r'\s*,\s*|\s+and\s+|\s*/\s*', first, flags=re.I)
    if len(parts)==1 and re.match(r'^(?:i|we|you|they|it|there|this|that|the service|the drone)\b', first, re.I):
        return []
    if not 1 <= len(parts) <= 3:
        return []
    result = []
    for part in parts:
        label = part.strip(' \t:,-')
        if not label or not re.fullmatch(r"[\w][\w' -]{0,69}", label, flags=re.U):
            return []
        if len(label.split()) > 5 or len(label) > 70:
            return []
        result.append({'topic':label, 'quote':label, 'matches_topic':None})
    return result


def information_need_kinds(answer):
    """Detect explicit general questions only, not a concern stated as an opinion."""
    text = answer.casefold()
    cue = bool(re.search(r'\b(?:explain|tell me|could you|can you|how (?:does|would|do|is)|'
                         r'i (?:would|d) (?:like|want) to know|i want to know|who (?:handles|is responsible)|'
                         r'what happens if|how (?:it|they) (?:work|compare)|not sure how)\b', text))
    if not cue:
        return []
    found = []
    if re.search(r'\b(?:transport|deliver|medicine|medicines|blood|samples)\b', text) and \
            re.search(r'\b(?:how|explain|work|process|would|could)\b', text):
        found.append('delivery_basics')
    if re.search(r'\b(?:compar|better than|worse than|regular deliveries|road deliver|vans?\b|trucks?\b)', text):
        found.append('comparison')
    if re.search(r'\b(?:who (?:handles|is responsible)|complaint|issues if|problems? (?:occur|arise)|accountab|what happens if)\b', text):
        found.append('accountability')
    if re.search(r'\b(?:already|currently|local|my city|in madrid|in \w+ city)\b', text) and \
            re.search(r'\b(?:operate|operation|service|route|deliver)\b', text):
        found.append('local_activity')
    return list(dict.fromkeys(found))


GENERAL_BACKGROUND = {
    'delivery_basics': (
        'In the healthcare-drone example, the aircraft transports items such as medicines, blood or '
        'laboratory samples. The precise arrangements depend on the particular service; this does not '
        'establish that such deliveries are operating in your city.'),
    'comparison': (
        'Whether a drone delivery is preferable to road delivery depends on the route and comparable '
        'evidence about travel time, reliability, noise, environmental effects and cost. We cannot '
        'conclude which option is better without that evidence.'),
    'accountability': (
        'For a real service, it is important to establish who receives complaints, who investigates '
        'problems and how responses affect decisions. I do not have verified details about those '
        'responsibilities for a service in your city.'),
    'local_activity': (
        'I do not have verified information establishing that this service operates in your city. '
        'We can keep that as an open question rather than assume a local operation exists.'),
}


def new_background(answer, previously_supplied):
    """Return bounded, conservative authored background or nothing.

    This is never classified as pre-existing citizen knowledge.
    """
    kinds = [k for k in information_need_kinds(answer) if k not in previously_supplied]
    if not kinds:
        return [], ''
    kinds = kinds[:2]
    return kinds, ' '.join(GENERAL_BACKGROUND[k] for k in kinds)


def adaptive_goal(node):
    """Never rewrite source-critical onboarding, literal-choice or scale questions."""
    if node.get('response_type') in {'city', 'citizen_depth', 'permission', 'yes_no',
                                     'display', 'opinion'}:
        return False
    return node.get('id') not in {'area', 'perspective', 'drone_recognition', 'drone_description',
                                  'drone_uses', 'drone_other_uses', 'healthcare_awareness',
                                  'healthcare_detail', 'local_awareness', 'local_basis',
                                  'citizen_duration', 'drone_explanation'}
