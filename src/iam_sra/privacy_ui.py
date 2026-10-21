"""Streamlit privacy handling: transient input is received, rejected input is cleared."""
import inspect
import re
import streamlit as st
from .privacy import PrivacyError, require_clean, screened_export, safe_message, safe_diagnostics


def clear_text_widgets():
    # Called inside callbacks, before widgets are rendered again. This clears
    # application-owned text references, not browser/process forensic memory.
    for key in list(st.session_state):
        if any(tag in key for tag in ('answer','text','clarification','resolve_','boundary_','information_custom','readiness_correction_')):
            if isinstance(st.session_state.get(key), str): st.session_state[key] = ''


def preview_identity(action):
    """Structural action context only; never retain raw text or hashes of it."""
    owner=getattr(action,'__self__',None)
    question=getattr(owner,'current_question',None)
    question_id=question.get('id') if isinstance(question,dict) else None
    pending=getattr(owner,'pending',None)
    return (id(owner),getattr(owner,'session_id',None),getattr(owner,'state',None),
            getattr(owner,'version',None),len(getattr(owner,'information_exposures',[])),question_id,
            pending.get('id',pending.get('version')) if isinstance(pending,dict) else None,
            tuple(st.session_state.get(k) for k in ('baseline_perspective','baseline_stakeholder_category','baseline_city','baseline_sector')),
            tuple(st.session_state.get(k) for k in ('conversation_perspective','conversation_role','conversation_city')),
            tuple(st.session_state.get(k) for k in ('assessment_profile','assessment_city','assessment_role','assessment_status','assessment_scenario','assessment_likert','indicator_profile','indicator_scope','indicator_case_id')),
            tuple(sorted((k,st.session_state[k]) for k in st.session_state if k.startswith(('availability_','component_')))),
            tuple(sorted(k for k in st.session_state if isinstance(st.session_state.get(k),str) and st.session_state[k] and (
                any(tag in k for tag in ('answer','text','clarification','information_custom','readiness_correction_')) or
                k.startswith(('assessment_use_case','assessment_area','assessment_unit','assessment_responsibilities','assessment_object',
                              'organisation_or_unit_','responsibilities_','technical_object_','object_version_','intended_environment_'))))))


def discard_preview():
    for key in ('privacy_prepared','privacy_preview','privacy_preview_identity'):
        st.session_state.pop(key,None)


def only_private_detail_fragment(text):
    """Narrow English UI check, not a general relevance or privacy classifier."""
    if '[private detail removed]' not in text:return False
    remaining=text.replace('[private detail removed]','')
    words=re.findall(r"[\w]+",remaining.casefold())
    return not words or set(words)<=set('my home address is at i live the'.split())


def invoke(action, *args, **kwargs):
    """Prepare a cleaned preview before invoking any controller with private text."""
    discard_preview()
    bound = inspect.signature(action).bind(*args, **kwargs)
    changed = False
    try:
        for key in getattr(action, '_privacy_fields', ()):
            if key not in bound.arguments or not isinstance(bound.arguments[key], str): continue
            try: require_clean(bound.arguments[key])
            except PrivacyError as exc:
                if exc.preview is None: raise
                bound.arguments[key] = exc.preview; changed = True
        if changed:
            # Check every replaced field again. Only the cleaned action is kept.
            for key in getattr(action, '_privacy_fields', ()):
                if key in bound.arguments and isinstance(bound.arguments[key], str): require_clean(bound.arguments[key])
            # Do not offer an address-only fragment as an assessment answer.
            # Context fields retain their existing explicit preview workflow.
            if 'text' in bound.arguments and only_private_detail_fragment(bound.arguments['text']):
                raise PrivacyError('We removed private details, leaving no answer to assess. Write a new answer without an address or other identifying details, or skip this question.')
            st.session_state.privacy_preview = '\n\n'.join(bound.arguments[k] for k in getattr(action, '_privacy_fields', ()) if k in bound.arguments and isinstance(bound.arguments[k], str))
            st.session_state.privacy_prepared = (action, bound.args, bound.kwargs)
            clear_text_widgets()
            st.session_state.privacy_preview_identity=preview_identity(action)
            raise PrivacyError('Private details were removed. Check the preview above, or write a new answer without those details.')
        return action(*args, **kwargs)
    except PrivacyError as exc:
        # The submitted fields already passed screening. A rejected generated
        # interpretation is not a reason to erase that safe answer or demand a
        # new session. Rejected input still follows the clear/preview workflow.
        if exc.code=='privacy_unavailable' or getattr(exc,'boundary',None) not in {'model_output','assessment_record'}:
            clear_text_widgets()
        # Models have no valid unsafe-output cache/trace to keep after a rejection.
        for value in (*args, *kwargs.values()):
            if hasattr(value, 'last_trace'):
                value.last_trace = []; value._request_cache = {}; value._token_count_cache = {}
                value._accepted_wire = None; value.last_settings = {}
                metadata = safe_diagnostics([d for d in getattr(value, 'last_diagnostics', []) if d.get('failure') == 'privacy'])
                value.last_diagnostics = metadata if isinstance(metadata, list) else []
        raise


def preview_control(perform):
    if 'privacy_prepared' not in st.session_state: return
    action=st.session_state.privacy_prepared[0]
    if st.session_state.get('privacy_preview_identity')!=preview_identity(action):
        discard_preview();return
    st.info('Private details have been replaced with [private detail removed]. This preview has not been submitted for assessment. Confirm only if it still says what you meant; otherwise write a general description instead.')
    st.write('Your answer with private details removed')
    st.text(st.session_state.privacy_preview)
    def confirm_cleaned():
        action, args, kwargs = st.session_state.privacy_prepared
        if st.session_state.get('privacy_preview_identity')!=preview_identity(action):
            discard_preview();raise PrivacyError('This preview is no longer current. Submit your answer again.')
        discard_preview()
        st.session_state.pop('privacy_preview', None)
        # Prepared keyword fields remain bound to this screened action and revision.
        perform(action, *args, **kwargs)
    st.button('Confirm cleaned text', on_click=confirm_cleaned)
    def discard():
        discard_preview()
        for key in ('baseline_error','readiness_error','conversation_error'):
            st.session_state.pop(key,None)
    st.button('Write a general description instead', on_click=discard)


def download_button(label, data, **kwargs):
    try:
        screened_export(data)
        return st.download_button(label, data, **kwargs)
    except PrivacyError as exc:
        st.warning(safe_message(exc))
        return False
