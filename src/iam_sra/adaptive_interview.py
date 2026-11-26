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
    """Map natural, explicit requests to bounded explanations; ignore mere opinions."""
    text=answer.casefold()
    cue_pattern=(r'\b(?:explain|what do you mean|what does .{1,50} mean|don.t understand|'
        r'could you|can you|tell me|how (?:does|do|would|is|are)|what (?:are|is|do|does)|'
        r'i (?:would like|want) to know|who (?:handles|is responsible)|what happens if|'
        r'not sure how|give me an example|why are you asking|why do you ask|'
        r'what would people normally do|does (?:this|that|it|the service)|'
        r'is there|are there)\b')
    # Scope topic detection to the clause containing the request cue. Otherwise
    # a concern/condition elsewhere in the same answer can spuriously trigger
    # unrelated background (for example, "explain who is responsible" plus a
    # separate proposal to compare road transport).
    clauses=[]
    for sentence in re.split(r'[.!?;\n]+',text):
        parts=re.split(r',\s*(?=(?:could you|can you|how\b|what\b|who\b|explain\b|tell me\b|give me\b))',sentence)
        for part in parts:
            clauses.extend(re.split(r'\s+(?:and|but)\s+(?=(?:could you|can you|how\b|what\b|who\b|explain\b|tell me\b|give me\b))',part))
    found=[]
    proposal_list=bool(re.match(r'\s*(?:show|compare|publish|provide|require|ensure|establish|demonstrate)\b',text))
    for clause in clauses:
        if not re.search(cue_pattern,clause):continue
        # In a list of conditions for a decision-maker, "explain who is
        # responsible" is a requested safeguard, not a question to the
        # interviewer. A separately addressed request ("could you explain")
        # remains eligible for an answer.
        direct_address=bool(re.search(r'\b(?:could|can) you\b|\bplease explain\b|\bi (?:want|would like) to know\b|\btell me\b',clause))
        if proposal_list and re.match(r'\s*(?:and\s+)?explain\s+(?:who|how|what)\b',clause) and not direct_address:
            continue
        healthcare_request=bool(re.search(r'\b(?:healthcare|medical|medicin\w*|blood|laboratory samples?|hospital|clinic|lab)\b',clause))
        if re.search(r'\b(?:complaint|complaints|escalat|who handles|who receives|responsib|decision process|'
                     r'how (?:are|is) decisions? (?:made|taken)|who decides)\b',clause):
            found.append('local_process')
        if healthcare_request:
            if (re.search(r'\b(?:how|example|for instance|what would happen)\b',clause)
                    and re.search(r'\b(?:sample|clinic|laboratory|lab|hospital)\b',clause)):
                found.append('sample_delivery_example')
            else:
                found.append('delivery_basics')
        if re.search(r'\b(?:compar|better than|worse than|regular deliveries|road deliver|vans?\b|trucks?\b)',clause):
            found.append('comparison')
        if re.search(r'\b(?:who (?:handles|is responsible)|complaint|issues if|problems? (?:occur|arise)|accountab|what happens if)\b',clause):
            found.append('accountability')
        if (re.search(r'\b(?:already|currently|local|my city|in madrid|in \w+ city)\b',clause)
                and re.search(r'\b(?:operate|operation|service|route|deliver)\b',clause)):
            found.append('local_activity')
        if re.search(r'\b(?:drones?|aircraft|fly|flying|pilot)\b',clause):
            if re.search(r'\bhow (?:does|do|can) (?:a |the )?drones?\b.*\bwork\b|\bhow it works\b',clause):
                found.append('drone_mechanics')
            elif (re.search(r'\b(?:what is|what are|explain|define) (?:a |an )?drone\b',clause)
                    or re.search(r'\bwhat (?:a |an )?drone is\b',clause)):
                found.append('drone_definition')
            elif not healthcare_request:
                found.append('drone_uses' if re.search(r'\b(?:use|used|purpose|application|example|what for)\b',clause)
                             else 'drone_definition')
        if not re.search(r'\b(?:complaint\w*|escalat\w*|responsib\w*|accountab\w*|decision\w*|healthcare|medical|'
                         r'medicin\w*|blood|sample|clinic|laboratory|lab|hospital|road|deliver|'
                         r'drones?|aircraft|fly|flying|pilot)\b',clause):
            found.append('clarify_current_question')
    return list(dict.fromkeys(found))


GENERAL_BACKGROUND = {
    'delivery_basics': (
        'Healthcare drones could transport medicines, blood, laboratory samples and other medical supplies. '
        'The precise arrangements depend on the particular service; this does not '
        'establish that such deliveries are operating in your city.'),
    'sample_delivery_example': (
        'As a general example, a healthcare team could arrange for a collected sample to be securely prepared '
        'and carried between a clinic and a laboratory, where it would be received for testing. The exact '
        'handling, route and responsibility would depend on the service. This is an illustrative possibility, '
        'not a claim that such a service operates in your city.'),
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
    'drone_definition': (
        'A drone is an aircraft that can fly without a pilot sitting inside it. Drones can have different sizes '
        'and can be used for many different purposes.'),
    'drone_uses': (
        'Drones can have different sizes and can be used for many different purposes. Healthcare transport is one possible '
        'application discussed in this interview, not evidence that a service operates locally.'),
    'local_process': (
        'I do not have verified information about the actual drone-service decision or complaint process in your '
        'city. For a real service, it would be important to identify who decides, who receives concerns, how they '
        'are investigated and how responses can affect decisions.'),
    'clarify_current_question': (
        'I can clarify the question in simpler terms. If the details are not known to you, it is fine to say so; '
        'that will be recorded as uncertainty rather than treated as a lack of readiness.'),
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
        r'(?:^|[.!?]\s*)[^.!?]{1,100}\s+(?:are|is)\s+my\s+(?:main|top|two|three)\s+priorities\b|'
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
