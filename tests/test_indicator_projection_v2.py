import json
from pathlib import Path

import pytest

from iam_sra.indicator_projection import project_concerns, validate_projection
from iam_sra.readiness_bank import load_bank
from iam_sra.chat_session import ChatSession


def projection(quote, topic='respondent concern', *, active=True, status='respondent_provided'):
    bank=load_bank(); eid='respondent-1'
    message={'id':eid,'role':'respondent','active':active,'evidence_status':status,'text':quote}
    concern={'topic':topic,'evidence_ids':[eid],'spontaneously_raised':True,
        'suggested_by_interviewer':False,'selected_priority':True,'explored':False}
    return project_concerns([concern],[message],bank)['results'][0]


def ids(row):
    return {item['indicator_id'] for item in row['candidate_mappings']}


def test_official_definition_grounded_rules_cover_indicator_bank_without_inventing_ids():
    bank=load_bank(); known={row['id'] for row in bank['indicators']}
    cases=json.loads((Path(__file__).resolve().parents[1]/'eval/iam_indicator_concern_holdout_v2.json').read_text())['cases']
    outputs=[projection(row['evidence']) for row in cases]
    assert known=={f'indicator-{i:02d}' for i in range(1,16)}
    assert {i for row in outputs for i in ids(row)}==known
    assert all(m['indicator_name']==next(b['name'] for b in bank['indicators'] if b['id']==m['indicator_id'])
        for row in outputs for m in row['candidate_mappings'])
    assert all(m['evidence_quote']==row['quote'] and m['evidence_id']==row['evidence_id']
        for row in outputs for m in row['candidate_mappings'])


def test_wildlife_noise_and_shared_word_hard_negatives():
    wildlife=projection('I worry that nesting birds may be disturbed by repeated low flights.')
    residential_noise=projection('The repeated buzzing over homes could disturb sleep and make the soundscape unpleasant.')
    unrelated=projection('The aircraft has a noise-cancelling microphone for the operator.')
    assert wildlife['status']=='unmapped' and 'indicator-07' not in ids(wildlife)
    assert 'indicator-07' in ids(residential_noise)
    assert unrelated['status']=='unmapped'


def test_long_answer_noise_is_not_attributed_to_wildlife_only_topic():
    quote=('Nesting birds may be disturbed near the wetland, while separate residential noise could disturb sleep.')
    row=projection(quote,topic='nesting birds')
    assert 'indicator-07' not in ids(row)
    assert row['status']=='unmapped'


def test_s7_specific_privacy_fairness_and_transparency_phrasing_maps_conservatively():
    privacy=projection('A drone passing a bedroom window might see inside, though I do not know if it has a camera.',topic='privacy')
    fairness=projection('Benefits and impacts may not be shared fairly.',topic='distributional fairness')
    transparency=projection('I want transparency about route decisions and whether residents can influence them.',topic='transparency')
    assert ids(privacy)=={'indicator-09'}
    assert ids(fairness)=={'indicator-13'}
    assert ids(transparency)=={'indicator-14'}


def test_privacy_cyber_and_safety_are_kept_semantically_distinct_or_ambiguous():
    privacy=projection('I do not want cameras recording through my bedroom window.')
    cyber=projection('I am concerned about encryption, authentication and unauthorised access to stored images.')
    safety=projection('I feel unsafe when a drone flies close to pedestrians.')
    generic_privacy=projection('I have privacy concerns.')
    assert ids(privacy)=={'indicator-09'}
    assert ids(cyber)=={'indicator-10'}
    assert ids(safety)=={'indicator-09'}
    assert generic_privacy['status']=='ambiguous'
    assert set(generic_privacy['possible_indicator_ids'])=={'indicator-09','indicator-10'}


def test_one_answer_can_support_multiple_distinct_official_concepts():
    row=projection('The service could improve access for remote clinics, but I worry about energy use and unequal distribution of benefits.')
    assert {'indicator-03','indicator-05','indicator-13'}<=ids(row)


def test_negation_and_unmatched_concerns_do_not_become_positive_candidates():
    row=projection('Noise is not a concern for me, and I do not think drones should be used near nesting birds.')
    assert 'indicator-07' not in ids(row)
    assert 'indicator-02' not in ids(row)
    assert row['status']=='unmapped'


def test_superseded_or_nonrespondent_evidence_is_excluded_and_validator_rejects_forgery():
    bank=load_bank(); quote='I worry about noise from repeated flights.'
    for active,status in ((False,'respondent_provided'),(True,'model_supplied')):
        result=project_concerns([{'topic':'noise','evidence_ids':['x']}],[
            {'id':'x','role':'respondent','active':active,'evidence_status':status,'text':quote}],bank)
        assert result['results']==[]
    row=projection(quote)
    forged=json.loads(json.dumps(row));forged['candidate_mappings'][0]['evidence_quote']='different answer'
    with pytest.raises(ValueError,match='exact respondent answer'):
        validate_projection({'status':'available','results':[forged]},
            {'respondent-1':{'text':quote,'active':True,'role':'respondent','evidence_status':'respondent_provided'}},
            {item['id']:item for item in bank['indicators']})


def test_internal_projection_is_not_in_participant_view_or_download():
    bank=load_bank();session=ChatSession(bank,'short',synthetic=True)
    answer='The repeated buzzing at night would disturb my sleep.'
    message=session._user(answer)
    session.concerns=[{'topic':'night-time sound','evidence_ids':[message['id']],
        'spontaneously_raised':True,'suggested_by_interviewer':False,
        'selected_priority':True,'explored':True}]
    session._project_concerns()
    assert session.concern_projection['results'][0]['candidate_mappings']
    assert 'concern_projection' not in session.view()
    assert 'concern_projection' not in session.export()['indicator_projection']
    assert not any('indicator-' in row['text'] for row in session.view()['messages'])
