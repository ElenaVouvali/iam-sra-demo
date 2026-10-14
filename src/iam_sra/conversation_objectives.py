"""Versioned view of the existing draft assessment objectives.

Eligibility remains in baseline_routing and ConversationSession; this registry
describes and audits those objectives without creating a second methodology.
"""
from copy import deepcopy
from .settings import config, CONCERNS

VERSION = 'conversation-objectives-1.2.0'
APPROVAL_STATUS = 'draft_pending_FN'


def registry():
    baseline = config('baseline')
    policy = config('conversation')
    result = {}
    for item in baseline['core_questions'] + baseline['probes']:
        key = 'general:' + item['id']
        result[key] = {
            'objective_id': key, 'criterion': item['dimension'],
            'topic_ids': list(item.get('topic_ids', [])),
            'stakeholder_applicability': deepcopy(item['applicable_roles']),
            'perspective_applicability': deepcopy(item['applicable_perspectives']),
            'stage': 'general', 'required_evidence_type': item['target_requirement'],
            'eligibility_prerequisites': deepcopy(item['prerequisites']),
            'sufficiency_conditions': item['completion_rule'],
            'source_references': [item['source_reference']],
            'approval_status': item['review_status'], 'approved_by': item.get('approved_by'),
            'neutral_question_examples': list(item['variants'].values()),
            'exclusions': ['Role is not evidence of individual experience.',
                           'Familiarity or acceptance does not establish readiness.'],
            'clarification_condition': item['probe_condition'],
            'optional': item['id'] in {q['id'] for q in baseline['probes']},
            'stopping_condition': item['completion_rule'],
            'eligibility_authority': 'existing baseline_routing policy',
        }
    for item in policy['scenario_questions']:
        key = 'scenario:' + item['id']
        result[key] = {
            'objective_id': key, 'criterion': item['criterion'],
            'topic_ids': list(item.get('topic_ids', [])),
            'stakeholder_applicability': list(baseline['stakeholders']),
            'perspective_applicability': list(baseline['perspectives']),
            'stage': 'scenario', 'required_evidence_type': item['criterion'],
            'eligibility_prerequisites': [item['prerequisite']] if item.get('prerequisite') else [],
            'sufficiency_conditions': 'existing scenario eligibility and claim sufficiency policy',
            'source_references': [item['source_locator']],
            'approval_status': policy['review_status'], 'approved_by': policy.get('approved_by'),
            'neutral_question_examples': [item['personal'], item['organisation']],
            'exclusions': ['Illustrative scenario text is not respondent evidence.',
                           'Hypothetical preference is not actual participation or influence.'],
            'clarification_condition': item.get('prerequisite', 'eligible unanswered objective'),
            'optional': not item['initial'],
            'stopping_condition': 'existing question budget, decline, or no eligible objective',
            'eligibility_authority': 'existing ConversationSession scenario policy',
        }
    for topic_id, item in CONCERNS.items():
        key = 'topic:' + topic_id
        result[key] = {
            'objective_id': key, 'criterion': item['label'], 'topic_ids': [topic_id],
            'stakeholder_applicability': list(baseline['stakeholders']),
            'perspective_applicability': list(baseline['perspectives']),
            'stage': 'scenario', 'required_evidence_type': 'respondent-grounded concern or relevant observation',
            'eligibility_prerequisites': ['topic is present in retrieved scenario/question context'],
            'sufficiency_conditions': 'topic context permits retrieval; claim support is separately verified',
            'source_references': deepcopy(item.get('source_references', [])),
            'approval_status': APPROVAL_STATUS, 'approved_by': None,
            'neutral_question_examples': [],
            'exclusions': ['Question or scenario topic alone is not respondent-expressed concern.',
                           'Topic coverage is not a CRL or SRL score.'],
            'clarification_condition': 'only when an eligible sourced question exists and evidence needs clarification',
            'optional': True, 'stopping_condition': 'existing scenario budget or respondent decline',
            'eligibility_authority': 'existing retrieved corpus and scenario eligibility',
        }
    return {'version': VERSION, 'review_status': APPROVAL_STATUS, 'approved_by': None,
            'topics': list(CONCERNS), 'objectives': result}
