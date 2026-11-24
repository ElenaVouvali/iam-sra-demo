"""Unit tests for conservative adaptive helpers (no live model required)."""
from iam_sra.adaptive_interview import (explicit_priority_list, information_need_kinds,
                                        new_background, adaptive_goal)


def test_explicit_priority_repair_preserves_two_exact_issues():
    x = 'Noise and wildlife disturbance. I am unsure how they compare to regular deliveries.'
    rows = explicit_priority_list(x)
    assert [r['topic'] for r in rows] == ['Noise', 'wildlife disturbance']
    assert all(r['quote'] in x for r in rows)


def test_ambiguous_question_is_not_extracted_as_priority():
    assert explicit_priority_list('I am not sure how the service compares.') == []
    assert explicit_priority_list('I might choose noise if it becomes worse.') == []
    assert explicit_priority_list('I do not trust drones.') == []


def test_information_requests_are_specific_and_safely_bounded():
    x = 'Could you explain how medical samples are delivered?'
    assert 'delivery_basics' in information_need_kinds(x)
    kinds, background = new_background(x, [])
    assert kinds and 'does not establish' in background
    assert new_background(x, kinds) == ([], '')


def test_onboarding_cannot_be_rewritten():
    assert not adaptive_goal({'id':'area','response_type':'city'})
    assert not adaptive_goal({'id':'healthcare_awareness','response_type':'yes_no'})
    assert not adaptive_goal({'id':'drone_description','response_type':'open'})
    assert not adaptive_goal({'id':'priority_understanding','response_type':'open'})
