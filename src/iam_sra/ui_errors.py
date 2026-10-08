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
    if code=='confirmation':
        return 'The interpretation has changed. Please review it and confirm “This reflects what I meant” again before continuing.'
    instructions={
        'Explicit confirmation is required before scoring.':'Tick “This reflects what I meant” before continuing.',
        'Explicit updated-meaning confirmation is required.':'Review your follow-up answers and tick “This reflects what I meant” before finishing.',
        'Choose an offered answer.':'Select one answer to this follow-up question, or choose Skip.',
        'Choose an answer, add your own words, or Skip.':'Choose an answer, explain your view, or choose Skip.',
        'Select an offered answer.':'Select one of the offered answers.',
        'Select one answer for this question.':'Select one answer for this question.',
        'Unknown joint response':'Choose Accept, Reject or Unsure for the combined proposal.',
        'Choose an explicit applicability answer.':'Answer whether your earlier view still applies, or choose Skip.',
        'Please explain what should be corrected.':'Explain what should be corrected in the answer box, or choose another answer.',
        'Resolve the targeted clarification questions before confirmation.':'Please resolve the displayed conflicting interpretation before confirming.',
        'Resolve conflicting answers before confirming.':'Please resolve the displayed conflicting answers before confirming.',
        'Answer the next discovery question, Skip it, or Finish discovery before confirming.':'Answer the clarification question, choose Skip, or select Finish these questions before confirming.',
        'Choose unsure on its own, or explain your position instead.':'Choose Unsure without an explanation, or clear that choice and explain your position.',
        'Confirm no reservations on its own, or describe your reservations instead.':'Confirm no reservations on its own, or choose another answer and describe your reservations.',
    }
    if str(exc) in instructions:return instructions[str(exc)]+' Your draft is retained.'
    if code=='clarification':
        return 'We could not establish the indicated meaning. Please clarify your position on that topic. Your draft and earlier answers are retained.'
    return 'We could not complete this step. Your draft and saved answers are retained. Please retry; if this persists, check the developer diagnostics.'
