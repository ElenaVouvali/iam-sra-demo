"""SYNTHETIC_TEST_DATA: deterministic navigation double, never live semantics."""
from copy import deepcopy


class ChatFixture:
    def turn(self, request):
        text = request['answer']; lower = text.lower()
        result = {'message': 'What would you want people planning a possible service to understand about this?',
            'proposed_action':'ask_question', 'act':'continue', 'topic':'healthcare drone service',
            'respondent_intent':'expressing a view', 'question_goal':'understand the concern',
            'justification':'The respondent raised a point that can be explored further.',
            'considered_alternatives':['Ask about safeguards','Move to another concern'],
            'evidence_ids':[request['current_answer_id']] if request.get('current_answer_id') else [],
            'context_facts':[], 'source_ids':[], 'uncertainty':'', 'indicator_ids':[], 'variants':[]}
        if 'madrid' in lower:
            result['context_facts']=[{'field':'city','quote':'Madrid'}]
            result['topic']='local context'
            result['message']='Thanks. No local operation is assumed. What comes to mind about possible healthcare deliveries?'
        if 'our test unit' in lower:
            result['context_facts']=[{'field':'organisation_or_unit','quote':'test unit'},
                {'field':'responsibilities','quote':'our responsibility only'}]
        if 'safety subsystem' in lower:
            result['context_facts'] += [{'field':'technical_object','quote':'safety subsystem'},
                {'field':'object_version','quote':'v1'}, {'field':'intended_environment','quote':'laboratory'}]
        if any(term in lower for term in ('wildlife','bird','nest')):
            result.update(topic='wildlife impacts',message='That is a concern people may want to understand. What effects on wildlife would worry you most?')
        elif any(term in lower for term in ('noise','sleep','sound')):
            result.update(topic='noise and rest',message='When or where might noise matter most to people?')
        elif 'privacy' in lower:
            result.update(topic='privacy',message='What information would you want before judging the privacy implications?')
        elif 'no idea what a drone' in lower:
            result['act']='explanation_offer'
        elif request.get('comparison'):
            result['variants']=['Which part of this concern matters most to you?','What would you most want planners to understand about this concern?']
        if 'noise' in lower or 'rest' in lower: result.update(indicator_ids=['indicator-07'], evidence_quote=text)
        if 'privacy' in lower: result.update(indicator_ids=['indicator-09'], evidence_quote=text)
        if 'safety' in lower: result.update(indicator_ids=['indicator-10'], evidence_quote=text)
        return result


class ScoreFixture:
    """Schema/citation double. Authored result is NOT a semantic assessor."""
    def match_profile(self,payload):
        return {'citations':[], 'selected_anchor_id':None,
                'explanation':'Synthetic fixture abstains; human semantic review required.',
                'boundary':'This fixture tests the journey, not readiness accuracy.', 'alternative_anchor_id':None,
                'material_conflict':False,'evidence_incomplete':True}
