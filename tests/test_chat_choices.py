"""Controller-owned option metadata; original letters use the existing screened API."""
from copy import deepcopy
import pytest
from iam_sra.chat_session import ChatSession
from iam_sra.chat_policy import letter_options,PERSPECTIVE,CITIZEN_DURATION,EDUCATIONAL_OPTIONS
from iam_sra.fn_interview import specification,flow_key
from indicator_fixtures import bank
from fn_fixture import SyntheticInterpreter
from test_fn_interview import replay


@pytest.mark.parametrize('letter,profile',[('A','citizen'),('B','organisational'),('C','technical')])
def test_role_options_do_not_turn_subsequent_open_questions_into_choices(letter,profile):
    s=ChatSession(bank(),synthetic=True);c=SyntheticInterpreter()
    assert s.view()['response_options']==letter_options(PERSPECTIVE)
    s.send(letter,c)
    assert s.profile==profile and s.objective=='area' and not s.view()['response_options']
    s.send('Madrid',c)
    assert s.view()['response_options']==(letter_options(CITIZEN_DURATION) if profile=='citizen' else [])
    assert s.calls==0


@pytest.mark.parametrize('depth_letter,depth',[('A','short'),('B','extended')])
def test_depth_and_educational_choices_accept_the_selected_value_without_a_model(depth_letter,depth):
    s=ChatSession(bank(),synthetic=True);c=SyntheticInterpreter()
    for text in ('A','Madrid',depth_letter):s.send(text,c)
    assert s.depth==depth and not s.view()['response_options']
    s.send('no',c)
    assert s.view()['response_options']==letter_options(EDUCATIONAL_OPTIONS)
    s.send('B',c)
    assert s.stage=='ended' and not s.view()['response_options'] and s.suggestion is None
    assert s.calls==0


@pytest.mark.parametrize('key',['citizen_short','citizen_extended','organisational','technical'])
def test_profile_specific_review_options_then_open_explanation_preserve_initial_score(key):
    s,c,score,questions=replay(key)
    config=specification()['review'][flow_key(s.profile,s.depth)]
    assert s.view()['response_options']==[{'value':k,'label':label} for k,label in zip('ABCDE',config['choices'])]
    original=deepcopy(s.suggestion);calls=s.calls
    s.send('C',c)
    assert s.stage=='review_addition' and not s.view()['response_options']
    assert s.suggestion==original and s.calls==calls


def test_options_are_hidden_for_recovery_correction_and_pause():
    s=ChatSession(bank(),synthetic=True)
    for attr,value in [('pending_correction','clarify'),('pending_comparison',{'variants':[]}),('pending_explanation',True),('failed_turn_id','m999')]:
        old=getattr(s,attr);setattr(s,attr,value)
        assert not s.response_options()
        setattr(s,attr,old)
    s.stage='paused';assert not s.response_options()


def test_no_valid_score_means_no_numeric_review_validation_buttons():
    s,c,score,questions=replay('citizen_short')
    s.suggestion={'level':None,'status':'abstained','gaps':['Synthetic insufficient evidence']}
    assert not s.response_options()


@pytest.mark.presidio_live
def test_real_privacy_accepts_option_metadata_and_unchanged_original_introduction():
    from iam_sra.privacy import require_safe_data
    from iam_sra.chat_policy import INTRODUCTION
    s=ChatSession(bank(),synthetic=True);c=SyntheticInterpreter()
    assert s.messages[0]['text']==INTRODUCTION
    require_safe_data(s.export())
    for text in ('A','Madrid','B','no'):
        s.send(text,c);require_safe_data(s.export())


def test_back_at_beginning_does_not_repeat_the_introduction_inside_chat():
    from iam_sra.chat_policy import INTRODUCTION
    s=ChatSession(bank(),synthetic=True)
    s.send('go back',SyntheticInterpreter())
    assert INTRODUCTION not in s.messages[-1]['text']
    assert s.messages[-1]['text'].endswith(PERSPECTIVE)
    assert s.view()['response_options']==letter_options(PERSPECTIVE)
    assert sum(m.get('act')=='introduction' for m in s.messages)==1
