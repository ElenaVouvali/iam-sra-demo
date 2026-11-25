"""Recognition is not necessarily knowledge of what a drone is."""
from iam_sra.chat_client import ChatClient
from iam_sra.fn_interview import FNInterview, explicit_unknown_drone_description
from fn_fixture import reply
from test_fn_interpretation import opening, install_http


def test_explicit_inability_is_not_partial_demonstrated_definition():
    assert explicit_unknown_drone_description(
        "I recognise them, but I don't know how to describe them.")
    assert explicit_unknown_drone_description('I do not know what a drone is.')
    assert not explicit_unknown_drone_description(
        "I know it's an aircraft without a pilot, but can't explain the electronics.")
    assert not explicit_unknown_drone_description('A kind of flying machine.')


def test_fn_offer_after_recognition_yes_but_unknown_description():
    fn = FNInterview()
    node = fn.current('citizen','short','drone_explanation')
    fn.record('drone_recognition','m1','explored','yes')
    fn.record('drone_description','m2','unknown','uncertain')
    assert fn.applicable(node, [])
    fn.record('drone_description','m3','explored','substantive')
    assert not fn.applicable(node, [])


def test_live_contract_integration_preserves_unknown_and_offers_single_explanation(monkeypatch):
    def output(payload, _attempt):
        result = reply(payload,kind='partial',status='explored')
        result['interpretation']['current_goal_addressed'] = True
        return result
    install_http(monkeypatch, output)
    s = opening()
    s.send("I recognise them, but I don't know how to describe them.",ChatClient())
    assert s.fn.coverage['drone_description']['status'] == 'unknown'
    assert s.fn.facts['drone_description'] == 'uncertain'
    assert s.objective == 'drone_uses'  # Prior knowledge is checked before explanations.
    s.send("I can't think of any examples.",ChatClient())
    assert s.objective == 'drone_explanation'
    s.send('yes',ChatClient())
    assert s.objective == 'healthcare_awareness'
    assert len([x for x in s.exposures if x['kind']=='FN_explanation']) == 1
    assert s.fn.coverage['drone_description']['status'] == 'unknown'
