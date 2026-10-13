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
        'transport':'The model service is unavailable. Please try again after it restarts.',
        'timeout':'The model took too long to reply. Please try again.',
        'schema':'We could not finish interpreting your answer. Please try again.',
        'truncated':'The interpretation was incomplete. Please try again.',
        'thinking':'We could not finish interpreting your answer. Please try again.',
    }
    reasons['service_busy']='The model is busy. Please try again shortly.'
    reasons['service_request']='The model service could not process this request. Your answer does not need reformatting.'
    if code in reasons:
        return reasons[code]+' Your text and saved answers are unchanged.'
    return 'We could not complete this step. Your draft and saved answers are retained. Please retry; if this persists, check the developer diagnostics.'
