"""Streamlit privacy handling: transient input is received, rejected input is cleared."""
import inspect
import streamlit as st
from .privacy import PrivacyError, require_clean, screened_export, safe_message, safe_diagnostics


def clear_text_widgets():
    # Called inside callbacks, before widgets are rendered again. This clears
    # application-owned text references, not browser/process forensic memory.
    for key in list(st.session_state):
        if any(tag in key for tag in ('answer','text','clarification','resolve_','boundary_','information_custom','readiness_correction_')):
            if isinstance(st.session_state.get(key), str): st.session_state[key] = ''


def invoke(action, *args):
    """Prepare a cleaned preview before invoking any controller with private text."""
    st.session_state.pop('privacy_prepared', None)
    st.session_state.pop('privacy_preview', None)
    bound = inspect.signature(action).bind(*args)
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
            st.session_state.privacy_preview = '\n\n'.join(bound.arguments[k] for k in getattr(action, '_privacy_fields', ()) if k in bound.arguments and isinstance(bound.arguments[k], str))
            st.session_state.privacy_prepared = (action, bound.args, bound.kwargs)
            clear_text_widgets()
            raise PrivacyError('Review the cleaned version below before it is processed.')
        return action(*args)
    except PrivacyError:
        clear_text_widgets()
        # Models have no valid unsafe-output cache/trace to keep after a rejection.
        for value in args:
            if hasattr(value, 'last_trace'):
                value.last_trace = []; value._request_cache = {}; value._token_count_cache = {}
                value._accepted_wire = None; value.last_settings = {}
                metadata = safe_diagnostics([d for d in getattr(value, 'last_diagnostics', []) if d.get('failure') == 'privacy'])
                value.last_diagnostics = metadata if isinstance(metadata, list) else []
        raise


def preview_control(perform):
    if 'privacy_prepared' not in st.session_state: return
    st.write('Cleaned version — check that the meaning is still correct')
    st.text(st.session_state.privacy_preview)
    def confirm_cleaned():
        action, args, kwargs = st.session_state.pop('privacy_prepared')
        st.session_state.pop('privacy_preview', None)
        # UI calls currently use positional controller arguments only.
        if kwargs: raise PrivacyError('Please resubmit the cleaned text directly.')
        perform(action, *args)
    st.button('Confirm cleaned text', on_click=confirm_cleaned)
    def discard():
        st.session_state.pop('privacy_prepared', None); st.session_state.pop('privacy_preview', None)
    st.button('Write a general description instead', on_click=discard)


def download_button(label, data, **kwargs):
    try:
        screened_export(data)
        return st.download_button(label, data, **kwargs)
    except PrivacyError as exc:
        st.warning(safe_message(exc))
        return False
