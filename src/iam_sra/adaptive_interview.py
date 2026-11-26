"""Opt-in FN-guided adaptive interviewing helpers.

No maturity inference here: only explicit conversational information needs,
plainly enumerated priorities and natural presentation. The original answers,
FN evidence bank and controller retain authority.
"""
import os
import re


def interview_strategy():
    """Return the opt-in FN interview strategy; preserve the baseline default."""
    value = os.getenv('IAM_CHAT_INTERVIEW_STRATEGY', 'controller_fn').strip().lower()
    if value not in {'controller_fn', 'model_led_fn'}:
        raise ValueError('IAM_CHAT_INTERVIEW_STRATEGY must be controller_fn or model_led_fn.')
    return value


def enabled():
    return os.getenv('IAM_CHAT_ADAPTIVE_MODE', '0').strip().lower() in {'1', 'true', 'yes'}


def max_wordings(depth):
    default = '12' if depth == 'short' else '18'
    try:
        return max(0, min(30, int(os.getenv('IAM_CHAT_MAX_ADAPTIVE_QUESTIONS', default))))
    except ValueError:
        return int(default)


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
    if node.get('preface') or node.get('response_type') in {'city', 'citizen_depth', 'permission', 'yes_no',
                                     'display', 'suggested_topics', 'opinion'}:
        return False
    return node.get('id') not in {'area', 'perspective', 'drone_recognition', 'drone_description',
                                  'drone_uses', 'drone_other_uses', 'healthcare_awareness',
                                  'healthcare_detail', 'local_awareness', 'local_basis',
                                  'citizen_duration', 'drone_explanation',
                                  'open_priorities', 'open_more', 'different_impacts',
                                  'priorities', 'priority_understanding',
                                  'decisions', 'participation'}

def explicit_priority_commitment(answer):
    """Only an overt personal selection can close prioritisation early.

    'We should prioritise safety' is a proposal, not an individual's
    choice of topics for the remainder of the interview.
    """
    return bool(re.search(
        r'\b(?:my|our)\s+(?:(?:two|three|main|top|only|biggest|first)\s+){0,3}'
        r'(?:priorities|concerns|issues)\s+(?:are|would be|is)\b|'
        r'\b(?:i (?:only )?want to focus on|what matters most to me is|'
        r'the (?:one|two|three) issues? i care most about)\b', answer, re.I))


def supplementary_recognition_coverage(profile, current_goal, answer, answer_kind,
                                       supplied_information=()):
    """Conservative evidence reuse for two *factual awareness* goals only.

    These are records of what was said, not claims of correctness, proficiency,
    readiness level or local drone operation. Each is backed by the ORIGINAL
    respondent answer ID in ChatSession, not an invented quote.
    """
    if profile != 'citizen' or answer_kind in {'no', 'uncertain', 'declined'}:
        return []
    text = answer.casefold()
    if current_goal == 'drone_recognition':
        aircraft = bool(re.search(r'\b(?:aircraft|flying (?:machine|vehicle)|unmanned aerial vehicle)\b', text))
        pilot = bool(re.search(r'\b(?:without|no)\s+(?:(?:a|an|any|human|onboard)\s+){0,3}pilot\b', text))
        if aircraft and pilot and not re.search(r'\b(?:i don.t know|i do not know|no idea|not sure what)\b', text):
            return [('drone_description', 'substantive')]
    if current_goal in {'drone_uses', 'drone_other_uses'}:
        personal_prior = bool(re.search(r'\b(?:i (?:also )?(?:have |had )?heard|i (?:have |had )?(?:seen|read|known)|'
                                        r'i (?:am|was) aware|i know)\b', text))
        healthcare = bool(re.search(r'\b(?:healthcare|medical|medicin\w*|blood|laboratory samples?)\b', text))
        negation = bool(re.search(r'\b(?:never heard|not heard|haven.t heard|hadn.t heard|don.t know|do not know)\b', text))
        supplied = any(e.get('kind') in {'retrieved_source_information', 'authored_general_background'} and
                       (not e.get('categories') or 'delivery_basics' in e.get('categories', []))
                       for e in supplied_information)
        if personal_prior and healthcare and not negation and not supplied:
            return [('healthcare_awareness', 'yes')]
    return []
