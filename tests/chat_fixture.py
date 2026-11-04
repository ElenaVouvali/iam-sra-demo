"""SYNTHETIC_TEST_DATA: deterministic navigation double, never live semantics."""
from copy import deepcopy


class ChatFixture:
    def turn(self, request):
        text = request['answer']; lower = text.lower(); current = request['current_objective']
        profile = ('organisational' if 'organisation' in lower else 'technical' if 'technology' in lower or 'subsystem' in lower else 'citizen') if current == 'perspective' else 'unknown'
        chosen = next((r for r in request['eligible'] if r['id'] != current), request['eligible'][0] if request['eligible'] else None)
        result = {'message': chosen['question'] if chosen else 'Would you like to finish?',
            'act': 'continue', 'profile': profile, 'profile_quote': text if profile!='unknown' else '',
            'context': [], 'covered': [{'objective_id': current, 'quote': text}] if text else [],
            'next_objective': chosen['id'] if chosen else None, 'indicator_ids': [], 'evidence_quote': '',
            'correction_target': None, 'variants': []}
        if current == 'area': result['context'] = [{'field':'city', 'quote':text}]
        if current == 'scope':
            fields = ['organisation_or_unit','responsibilities'] if request['profile']=='organisational' else ['technical_object','object_version','intended_environment']
            result['context'] = [{'field':f,'quote':text} for f in fields]
        if 'noise' in lower or 'rest' in lower: result.update(indicator_ids=['indicator-07'], evidence_quote=text)
        if 'privacy' in lower: result.update(indicator_ids=['indicator-09'], evidence_quote=text)
        if 'safety' in lower: result.update(indicator_ids=['indicator-10'], evidence_quote=text)
        if 'no idea what a drone' in lower: result['act']='explanation_offer'
        if 'correction' in lower or 'actually' in lower:
            target=next((m['id'] for m in request['original_context'] if m['objective_id']=='area'),None) if 'city' in lower or 'locality' in lower else next((i for i in request['prior_ids'] if i!=request['prior_ids'][-1]),None)
            result.update(act='correction', correction_target=target, covered=[])
        if 'change scope' in lower: result['act']='scope_change'
        if request['comparison']:
            result['variants']=[chosen['question'], 'In your own words, '+chosen['question'][0].lower()+chosen['question'][1:]]
        return result


class ScoreFixture:
    """Schema/citation double. Authored result is NOT a semantic assessor."""
    def match_profile(self,payload):
        return {'assessments':[{'anchor_id':a['id'],'status':'insufficient','citations':[]} for a in payload['anchors']],
                'selected_anchor_id':None, 'explanation':'Synthetic fixture abstains; human semantic review required.',
                'boundary':'This fixture tests the journey, not readiness accuracy.', 'alternative_anchor_id':None,
                'material_conflict':False,'evidence_incomplete':True}
