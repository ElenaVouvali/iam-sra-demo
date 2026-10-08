"""Direct-role mapper contracts, with synthetic annotations rather than live inference."""
import json
import pytest
from iam_sra.passage_mapping import combine, extract
from iam_sra.interpretation import EvidenceItem
from iam_sra.assessment import AssessmentError
from iam_sra.settings import CONCERNS


@pytest.mark.parametrize('roles,position,conditions',[
    ({'p1':'opposition_now','p2':'change_before_acceptance'},'opposed',['p2']),
    ({'p1':'refusal_even_after_changes','p2':'acceptance_now'},'opposed',[]),
    ({'p1':'balanced_evaluation'},'mixed',[]),
    ({'p1':'no_position_yet'},'uncertain',[]),
    ({'p1':'opposition_now'},'opposed',[]),
    ({'p1':'acceptance_now','p2':'opposition_now'},'uncertain',[]),
    ({'p1':'accepted_with_ongoing_requirement'},'supported',['p1']),
])
def test_semantic_roles_do_not_promote_refusal_or_future_acceptance_to_balance(roles,position,conditions):
    result=combine(roles)
    assert result.position==position and result.condition_ids==conditions


def test_unrelated_is_absent_and_excess_evidence_is_not_silently_truncated():
    assert combine({'p':'unrelated_or_factual'}) is None
    with pytest.raises(AssessmentError):combine({str(i):'acceptance_now' for i in range(4)})


class Client:
    def __init__(self,fail=None):self.last_settings={};self.calls=[];self.fail=fail
    def _request(self,http,stage,system,user,schema,validator):
        self.calls.append(user)
        if 'citizen_passages' in user:
            key=user['facet']
            if key==self.fail:raise AssessmentError('Bounded semantic failure',code='schema')
            raw={r:'unrelated_or_factual' for r in user['citizen_passages']}
            if key=='acoustic_impact':raw['O.p001']='acceptance_now'
            if key=='energy_demand':raw['O.p002']='no_position_yet'
        else:raw={'interpretation':'unassessed','excerpts':[],'rationale':'No route position.'}
        return validator(json.dumps(raw))


def test_every_facet_is_reviewed_and_uncertainty_cannot_be_lost_by_nomination():
    evidence={r:EvidenceItem(id=r,text=t,context='original',source='citizen_original') for r,t in [
        ('O.p001','The hum is acceptable.'),('O.p002','I cannot judge its electricity use.') ]}
    c=Client();meaning=extract(c,None,evidence)
    assert len(c.calls)==sum(len(d['facets']) for d in CONCERNS.values())+1
    assert {f.facet for f in c.last_original_facets}=={'acoustic_impact','energy_demand'}
    assert next(f for f in c.last_original_facets if f.facet=='energy_demand').position=='uncertain'
    assert all('quotation' not in json.dumps(call) for call in c.calls)


def test_one_semantic_failure_preserves_other_facets_and_is_explicitly_unresolved():
    evidence={r:EvidenceItem(id=r,text=t,context='original',source='citizen_original') for r,t in [
        ('O.p001','The hum is acceptable.'),('O.p002','I cannot judge its electricity use.') ]}
    c=Client(fail='energy_demand');extract(c,None,evidence)
    assert [f.facet for f in c.last_original_facets]==['acoustic_impact']
    assert 'energy_emissions:energy_demand' in c.last_settings['unresolved_facet_reviews']


def test_incomplete_mapping_cannot_silently_produce_an_overall_score():
    from iam_sra.session import Session
    from test_confirmation import Fake,meaning
    client=Fake(meaning(scores=('noise',)))
    s=Session();s.begin();s.submit('The hum is acceptable.',client)
    s.confirm(True,defer_discovery=True)
    s.mapping_review_errors={'energy_emissions:energy_demand':{'code':'schema','error':'Unresolved'}}
    with pytest.raises(AssessmentError,match='before scoring'):s.score_initial(client)
    assert s.initial is None and s.draft.concerns
