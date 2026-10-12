"""Actionable UI errors without exposing model output or blaming citizen input."""
from .settings import MAX_INPUT_BYTES


def user_error(exc):
    code=getattr(exc,'code',None)
    if code=='input':
        return f'Enter your response before continuing. The limit is {MAX_INPUT_BYTES} UTF-8 bytes; your draft is retained and is never cut automatically.'
    if code=='budget':
        return 'The assessment request exceeds the model’s processing limit. This includes our instructions as well as your answer. Your draft is saved; none of your words were cut.'
    if code=='evidence':
        return 'The model returned supporting passages that could not be verified. Your draft and saved answers are retained. Please retry this step; this is not a missing answer or confirmation.'
    if code=='interpretation':
        return 'The model could not complete your interpretation. Your answer is retained. Please retry the same answer; you do not need to rewrite it.'
    reasons={
        'transport':'The model service could not be reached or did not complete the request.',
        'timeout':'The model exceeded the time limit for this step.',
        'schema':'The model response did not match the required answer format.',
        'truncated':'The model response stopped before it was complete.',
        'thinking':'The model returned reasoning text instead of the required answer format.',
    }
    if code in reasons:
        return reasons[code]+' Your answers and any saved confirmation are retained. Please retry this step.'
    return 'We could not complete this step. Your draft and saved answers are retained. Please retry; if this persists, check the developer diagnostics.'
