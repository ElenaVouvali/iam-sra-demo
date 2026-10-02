import importlib.util
from pathlib import Path
from test_core import assessment
spec=importlib.util.spec_from_file_location('evaluation_runner',Path(__file__).parents[1]/'eval/run.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def test_failures_remain_in_agreement_denominator():
    rows=[{'accepted':True,'qualitative_agreement':True,'latency_seconds':1},{'accepted':False,'failure_category':'schema','latency_seconds':2}]
    s=module.summary(rows)
    assert s['attempted']==2 and s['failures']==1 and s['qualitative_agreement_all_attempts']==.5

def test_fn_source_labels_are_separate_from_alternative_mapping():
    a=assessment({'welfare_equity':8,'noise':3,'perceived_safety_privacy':2})
    case={'id':'fn_reference','required_concerns':['welfare_equity','noise','perceived_safety_privacy'],'optional_concerns':['visual_pollution']}
    ref={'scores':{'welfare_equity':8,'noise':3,'perceived_safety_privacy':2,'visual_pollution':4},'mean':4.25,'illustrative_final':4}
    r=module.evaluate_result(a,case,ref)
    assert r['qualitative_agreement'] and r['fn_missing_source_dimensions']==['visual_pollution']
    assert r['fn_source_score_deltas']['visual_pollution'] is None

def test_correct_topic_does_not_hide_unsupported_medical_support():
    from iam_sra.schemas import Dimension
    a=assessment({'noise':3})
    a.medical_public_benefit_support=Dimension(interpretation='supported',excerpts=['noise privacy visual welfare'],rationale='Unsupported public-benefit interpretation.')
    case={'id':'noise_only','required_concerns':['noise'],'expected_medical_support':'unassessed'}
    result=module.evaluate_result(a,case,{})
    assert result['checks']['required_concerns']
    assert not result['checks']['expected_medical_support']
    assert not result['qualitative_agreement']
