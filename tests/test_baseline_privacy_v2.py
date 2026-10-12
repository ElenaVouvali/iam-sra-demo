"""Bounded recogniser coverage; synthetic names/addresses, no personal data."""
from copy import deepcopy
import pytest
from iam_sra.privacy import PrivacyError, require_clean, contextual_findings

ADDRESSES=[
 'I live at 42 example street.', 'I live at 42 EXAMPLE STREET.',
 'I live at example street 42.', 'I live at EXAMPLE ROAD 42, apt 2, 12345.',
 'My address is 42 example street, apartment 2, postcode 12345.',
 'I live at calle ejemplo 42, piso 2, 28013.',
 'I live at CALLE EJEMPLO 42.', 'I live at 42 calle ejemplo.',
 'I live at via esempio 42, interno 2, 00100.',
 'I live at RUA EXEMPLO 42, andar 2, 3000-123.',
 'I live at οδός παραδείγματος 42, διαμέρισμα 2, 12345.',
 'I live at ΟΔΟΣ ΠΑΡΑΔΕΙΓΜΑΤΟΣ 42.',
 'I live at Πατησίων 42.',
]
BENIGN=['near my home','Madrid','Milan','Coimbra region','Athens','Lisbon',
        '15 flights at 60 meters in 2026','My role is planning.','Healthcare / pharmacy',
        'The public hospital and industrial park','I work in an apartment building.',
        'The community needs opportunities, not a score.', 'reason at most 100 characters',
        'The first 15 flights', 'A request for 2026 results']


@pytest.mark.parametrize('text',ADDRESSES)
def test_case_and_local_address_formats_masked_with_confirmation(text):
    with pytest.raises(PrivacyError) as exc:require_clean(text)
    assert exc.value.preview and '[private detail removed]' in exc.value.preview
    assert '42' not in exc.value.preview
    assert text not in str(exc.value)
    require_clean(exc.value.preview)


@pytest.mark.parametrize('text',BENIGN)
def test_broad_places_and_context_not_address(text):
    assert not contextual_findings(text)
    assert require_clean(text)==text


@pytest.mark.presidio_live
def test_actual_installed_detector_bounded_address_and_benign_cases():
    pytest.importorskip('presidio_analyzer');pytest.importorskip('en_core_web_sm')
    for text in ADDRESSES:
        with pytest.raises(PrivacyError) as exc:require_clean(text)
        assert exc.value.preview and '42' not in exc.value.preview
    for text in BENIGN:assert require_clean(text)==text


def test_stale_context_preview_not_applied_after_navigation(monkeypatch):
    from test_baseline_ui import start,click
    app=start(monkeypatch)
    app.selectbox(key='baseline_city').select('other').run()
    app.text_input(key='baseline_place_text').set_value('my address is 42 example street')
    click(app,'Begin')
    assert app.session_state.session.state=='welcome'
    assert any(b.label=='Confirm cleaned text' for b in app.button)
    # Changing a controlled context field reruns UI; previous cleaned action must expire.
    app.selectbox(key='baseline_city').select('madrid').run()
    assert not any(b.label=='Confirm cleaned text' for b in app.button)
    assert 'privacy_prepared' not in app.session_state
    assert app.session_state.session.state=='welcome'


def test_stale_answer_preview_not_applied_to_next_question(monkeypatch):
    from test_baseline_ui import start,click
    app=start(monkeypatch);click(app,'Begin')
    app.radio(key='baseline_familiarity').set_value('little');click(app,'Continue')
    app.text_area(key='baseline_answer_text').set_value('Email alice@example.com')
    click(app,'Continue')
    assert any(b.label=='Confirm cleaned text' for b in app.button)
    click(app,'Skip')
    assert app.session_state.session.current_question['id']=='delivery'
    assert not any(b.label=='Confirm cleaned text' for b in app.button)
    assert not any('alice@example.com' in e['text'] for e in app.session_state.session.events)


def test_new_input_invalidates_prepared_preview_without_retaining_new_text(monkeypatch):
    from test_baseline_ui import start,click
    app=start(monkeypatch);click(app,'Begin')
    app.radio(key='baseline_familiarity').set_value('little');click(app,'Continue')
    app.text_area(key='baseline_answer_text').set_value('Email alice@example.com');click(app,'Continue')
    assert any(b.label=='Confirm cleaned text' for b in app.button)
    app.text_area(key='baseline_answer_text').set_value('A new general description.').run()
    assert not any(b.label=='Confirm cleaned text' for b in app.button)
    assert app.session_state.session.current_question['id']=='concept'
    assert len(app.session_state.session.events)==1


@pytest.mark.parametrize('separator_in_span',[False,True])
def test_uuid_person_false_positive_does_not_disable_contextual_secret_blocking(monkeypatch,separator_in_span):
    from iam_sra.privacy import Finding
    uuid='73734a8e-cfbb-4eb1-847f-4a6d7685109b'
    class FalsePerson:
        def analyze(self,*,text,**kwargs):
            start=text.find(uuid)
            return [] if start<0 else [Finding('PERSON',start,min(len(text),start+len(uuid)+(2 if separator_in_span else 0)))]
    monkeypatch.setattr('iam_sra.privacy.detector',lambda:FalsePerson())
    assert require_clean(uuid)==uuid
    from iam_sra.privacy import require_safe_data
    require_safe_data({'session_id':uuid,'state':'complete'})
    with pytest.raises(PrivacyError):require_clean('My password is '+uuid)
