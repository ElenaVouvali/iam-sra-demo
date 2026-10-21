"""Shared, bounded profile assessment; separate tool/participant judgments."""
from copy import deepcopy
from hashlib import sha256
import json
from .readiness_bank import load_bank, validate_bank, PROFILES
from .questionnaire import load_questionnaire, validate_questionnaire, module_for
from .indicator_client import POLICY, validate_reading, validate_match
from .privacy import require_safe_data
from .assessment import AssessmentError

SCHEMA = 'indicator-self-assessment-2.0.0'
QUESTION_BUDGET = 3
NOTICE = 'Draft prototype for review. Confirmed self-report is not independently verified. Selected indicators are a partial individual assessment; there is no overall score.'


def observation_description(observation):
    """Expose distinctions used by matching so participants can correct them."""
    kinds = {'recognition': 'Recognition', 'reasoning': 'Reasoning', 'bare_claim': 'Claim without an explanation',
             'condition': 'Proposed condition or safeguard', 'stance': 'Personal position',
             'intention': 'Intention for a future activity', 'barrier': 'Participation barrier',
             'activity': 'Reported activity', 'contribution': 'Reported contribution',
             'influence': 'Reported influence on a decision', 'agency': 'Reported exercise of agency',
             'uncertainty': 'Uncertainty', 'absence': 'Reported absence of knowledge or activity'}
    actors = {'self': 'your own reasoning or action', 'organisation': 'an organisation’s reasoning or action',
              'technical_object': 'the named technical object', 'third_party': 'another person’s reasoning or action', 'unclear': 'whose reasoning or action is unclear'}
    times = {'actual': 'reported as actual, not independently verified', 'hypothetical': 'hypothetical',
             'unspecified': 'actual experience not established'}
    domains = {'IAM': 'about IAM', 'other': 'about another domain', 'unclear': 'domain unclear'}
    return ' · '.join((kinds[observation['kind']], actors[observation['actor']],
                       times[observation['actuality']], domains[observation['domain']]))


def resolved_scale(bank, indicator_id, profile='citizen'):
    rows = {r['id']: r for r in bank['review_rows']}
    labels = {r['level']: r['description'].split('. ', 1)[0] for r in bank['generic_scales'][PROFILES[profile]]}
    return [{**deepcopy(s), 'label': labels[s['level']],
             'row_review_status': rows[s['review_row_id']]['status'],
             'row_review_comment': rows[s['review_row_id']]['comment'],
             'review_source': deepcopy(rows[s['review_row_id']]['source'])}
            for s in sorted(bank['statements'], key=lambda r: r['level'])
            if s['indicator_id'] == indicator_id and s['profile'] == profile and s['scale'] == PROFILES[profile]]


class IndicatorAssessment:
    def __init__(self, bank=None, questionnaire=None):
        self.bank = deepcopy(bank) if bank is not None else load_bank()
        validate_bank(self.bank)
        self.questionnaire = deepcopy(questionnaire) if questionnaire is not None else load_questionnaire()
        validate_questionnaire(self.questionnaire, self.bank)
        self.profile = 'citizen'
        self.report_finished = False
        self.revision = 0
        self.scope = None
        self.selected = []
        self.current_id = None
        self.results = {}
        self.history = []
        self.presented_cases = []

    def identity(self):
        return {'source': deepcopy(self.bank['source']), 'bank_version': self.bank['bank_version'],
                'schema_version': self.bank['schema_version'], 'status': self.bank['status'],
                'bank_sha256': self.bank.get('bank_sha256') or sha256(json.dumps(self.bank, sort_keys=True).encode()).hexdigest()}

    @property
    def current(self):
        return self.results.get(self.current_id)

    def indicator(self, key):
        return next(i for i in self.bank['indicators'] if i['id'] == key)

    def scale(self, key):
        return resolved_scale(self.bank, key, self.profile)

    def invalidate(self, reason, all_results=False, targets=None):
        targets = targets if targets is not None else self.results.values() if all_results else [self.current] if self.current else []
        for row in targets:
            if row['tool'] is not None or row['participant'] is not None:
                self.history.append({'indicator_id': row['indicator_id'], 'scope': deepcopy(row['scope']),
                    'evidence_revision': row['evidence_revision'], 'tool': deepcopy(row['tool']),
                    'participant': deepcopy(row['participant']), 'reason': reason, 'status': 'superseded'})
            row.update(tool=None, participant=None, suggestion_error=None, status='not_assessed')
        self.revision += 1

    def invalidate_links(self, event_ids):
        """A linked snapshot must not outlive correction of its source answer/scope."""
        for row in self.results.values():
            if row is self.current: continue
            linked=[e for e in row['events'] if e['active'] and e['origin']=='confirmed_indicator_reuse' and e['id'] in event_ids]
            if linked:
                self.invalidate('Linked source answer or scope revised', targets=[row])
                for event in linked: event['active']=False
                row.update(state='collecting', opening_reused=False, next_question_id=None)
                row['evidence_revision']+=1

    def module(self):
        return module_for(self.questionnaire, self.current_id, self.profile)

    def questionnaire_identity(self):
        return deepcopy(self.questionnaire.get('_identity', {
            'questionnaire_version': self.questionnaire['questionnaire_version'],
            'schema_version': self.questionnaire['schema_version'], 'status': self.questionnaire['status']}))

    def _ensure_row(self, key):
        row = self.results.get(key)
        if row and row.get('base_scope', row['scope']) == self.scope and row['state'] != 'superseded':
            return row
        old_events = row['events'] if row else []
        for event in old_events:
            event['active'] = False
        row = {'indicator_id': key, 'profile': self.profile, 'base_scope': deepcopy(self.scope),
               'scope': deepcopy(self.scope), 'state': 'collecting' if self.profile == 'citizen' else 'scope',
               'status': 'not_assessed', 'events': old_events, 'pending': None, 'tool': None, 'participant': None, 'suggestion_error': None,
               'evidence_revision': 0, 'question_override': None, 'next_question_id': None,
               'information': [], 'likert': None, 'opening_reused': False, 'disposition': None}
        self.results[key] = row
        return row

    def select(self, indicator_ids, scope, reuse):
        known = {i['id'] for i in self.bank['indicators']}
        profile = scope.get('response_profile', 'citizen')
        if profile not in PROFILES or not 1 <= len(indicator_ids) <= 15 or len(set(indicator_ids)) != len(indicator_ids) or set(indicator_ids)-known:
            raise ValueError('Choose a response profile and distinct indicators from the source bank.')
        if set(reuse)-set(indicator_ids):
            raise ValueError('Link answers only to the indicators selected for this round.')
        if self.current and self.current['pending']:
            raise ValueError('Check or revise the pending interpretation before changing scope.')
        changed = self.scope is not None and scope != self.scope
        if changed:
            self.invalidate('Assessment profile or context changed', all_results=True)
            for row in self.results.values():
                row.update(state='superseded', pending=None)
                for event in row['events']: event['active'] = False
            self.selected = []
        self.profile = profile
        self.scope = deepcopy(scope)
        self.selected = list(dict.fromkeys(self.selected + list(indicator_ids)))
        for key in indicator_ids:
            row = self._ensure_row(key)
            for event in reuse.get(key, []):
                if event['id'] not in {e['id'] for e in row['events'] if e['active']}:
                    self.current_id = key
                    self.invalidate('Confirmed evidence explicitly linked')
                    linked = deepcopy(event)
                    linked['linked_source_scope'] = deepcopy(event.get('scope'))
                    linked['scope'] = deepcopy(row['scope'])
                    row['events'].append(linked)
                    row['opening_reused'] = True
        self.current_id = indicator_ids[0]
        self.report_finished = False
        self.revision += 1
        self.advance_question()

    def set_scope(self, availability='ready_to_discuss', organisation_or_unit='', responsibilities='',
                  technical_object='', object_version='', intended_environment='', component_scope='unsure'):
        row = self.current
        if not row or row['pending']:
            raise ValueError('Resolve the pending answer before changing indicator scope.')
        if availability not in {'ready_to_discuss','outside_role','no_technical_object_identified','not_applicable_explained'}:
            raise ValueError('Choose a listed scope disposition.')
        fields = dict(organisation_or_unit=organisation_or_unit, responsibilities=responsibilities,
                      technical_object=technical_object, object_version=object_version,
                      intended_environment=intended_environment, component_scope=component_scope)
        if any(not isinstance(v,str) or len(v)>500 for v in fields.values()):
            raise ValueError('Use short general scope descriptions.')
        require_safe_data(fields)
        if availability == 'outside_role' and self.profile != 'organisational':
            raise ValueError('Outside-role disposition applies to organisational responsibilities.')
        if availability == 'no_technical_object_identified' and self.profile != 'technical':
            raise ValueError('No-object disposition applies to technical assessment.')
        if availability == 'ready_to_discuss':
            if self.profile == 'organisational' and (not organisation_or_unit.strip() or not responsibilities.strip()):
                raise ValueError('Confirm the broad unit and responsibilities for this indicator.')
            if self.profile == 'technical' and not technical_object.strip():
                raise ValueError('Name the relevant object/concept, or record no relevant object.')
        scope = {**deepcopy(self.scope), **fields, 'availability': availability}
        if row['scope'].get('illustrative_case'):scope['illustrative_case']=deepcopy(row['scope']['illustrative_case'])
        if row['scope']==scope:return
        if row['scope'] != scope:
            self.invalidate('Indicator responsibility or technical object changed')
            initial_confirmation = row['state']=='scope' and availability=='ready_to_discuss' and all(
                row['scope'].get(k)==v for k,v in fields.items())
            if not initial_confirmation:
                self.invalidate_links({e['id'] for e in row['events'] if e['active'] and e['origin']=='indicator_interview'})
            for event in row['events']:
                if initial_confirmation and event['active']:
                    event['scope'] = deepcopy(scope)
                else:
                    event['active'] = False
            row.update(scope=scope, question_override=None, next_question_id=None,
                       opening_reused=row['opening_reused'] if initial_confirmation else False, likert=None)
            row['evidence_revision'] += 1
        row.update(state='collecting', status='not_assessed', disposition=None)
        self.revision += 1
        if availability != 'ready_to_discuss':
            row.update(state='ready', status=availability, disposition=availability)
            self.suggest(None, self.revision)
        else:
            self.advance_question()

    def evidence(self):
        row = self.current
        if any(e['active'] and e['confirmed'] and e['control']=='answer' and e['scope']!=row['scope'] for e in row['events']):
            raise ValueError('Active evidence has an incompatible assessment scope; revise the explicit link.')
        return [{'evidence_id': e['id'], 'answer': e['text'], 'question': deepcopy(e['question']),
                 'meaning': e['reading']['meaning'], 'observations': deepcopy(e['reading']['observations']),
                 'interpretation_history': deepcopy(e.get('interpretation_history', [])),
                 'information_context': e['information_context'], 'origin': e['origin'],
                 'scope': deepcopy(e['scope']), 'confirmed': True, 'active': True}
                for e in row['events'] if e['active'] and e['confirmed'] and e['control']=='answer'
                and e['question'].get('format') != 'likert' and e['scope'] == row['scope']]

    def candidates(self, exclude=()):
        module = self.module()
        asked = {e['question'].get('id') for e in self.current['events'] if e['active']} | set(exclude)
        questions = {q['id']: q for q in module['questions']}
        ordered = [questions[key] for key in module['question_order']]
        probes = {q['id']:q for q in self.questionnaire['shared_probes']}
        case=self.current['scope'].get('illustrative_case')
        reflections=[]
        if case and self.profile=='citizen' and self.current_id in case.get('indicator_ids',[]) and case.get('opening_question'):
            opening=case['id']+'-opening';probe=case['id']+'-probe'
            reflection_id=probe if opening in asked else opening
            reflections=[{'id':reflection_id,'indicator_id':self.current_id,'profile':'citizen','kind':'case_reflection',
                'text':case['conditional_followup']['text'] if reflection_id==probe else case['opening_question'],
                'purpose':'reflection_or_conditions','ask_when':'Only if relevant to the active criterion, unresolved and not already answered. '+case['conditional_followup']['ask_when'],
                'origin':'newly_drafted','source_refs':[deepcopy(case['source'])],
                'scenario_id':case['id'],'scenario_version':case['version']}]
        return [deepcopy(q) for q in ordered + reflections + [probes[key] for key in module['shared_probe_ids']] if q['id'] not in asked]

    def set_case(self, card):
        row=self.current
        if not row or row['pending']:raise ValueError('Resolve the pending interpretation before changing the case.')
        from .scenario_expansion import presented_card
        case=presented_card(card) if card else None
        if row['scope'].get('illustrative_case')==case:return
        self.invalidate('Optional illustrative case changed')
        self.invalidate_links({e['id'] for e in row['events'] if e['active'] and e['origin']=='indicator_interview'})
        for e in row['events']:e['active']=False
        row['scope'].pop('illustrative_case',None)
        if row['scope'].get('use_case_card',{}).get('origin')=='source_backed_illustrative':
            row['scope']['scenario_id']=case['id'] if case else None
            row['scope']['use_case_card'].update(illustrative_text=case['text'] if case else None,
                source=deepcopy(case['source']) if case else None,source_refs=deepcopy(case.get('source_refs',[])) if case else [],
                unknowns=deepcopy(case['unknowns']) if case else [],source_status=case.get('source_status') if case else None)
        if case:
            row['scope']['illustrative_case']=case
            already=any(c['id']==case['id'] and c['version']==case['version'] for c in self.presented_cases)
            if not already:self.presented_cases.append(deepcopy(case))
            row['information'].append({'kind':'case','case_id':case['id'],'version':case['version'],
                'sequence':len(row['information'])+1,'already_presented':already,'source':deepcopy(case['source']),
                'text':case['text'],'meaning':'Illustrative source information; not actual experience, a VR evaluation or technical validation.'})
        disposition=row['scope'].get('availability')
        if disposition not in {'outside_role','no_technical_object_identified','not_applicable_explained'}:disposition=None
        row.update(state='ready' if disposition else 'scope' if self.profile!='citizen' and not row['scope'].get('availability') else 'collecting',
            next_question_id=None,question_override=None,opening_reused=False,disposition=disposition)
        row['evidence_revision']+=1
        self.report_finished=False
        if disposition:self.suggest(None,self.revision)
        else:self.advance_question()

    def question_record(self, question):
        value = deepcopy(question)
        value.update(question_text=question['text'].replace('{topic}', self.module()['plain_topic']),
                     format='likert' if 'likert' in question.get('response_type','') else 'open_text',
                     intent=question['purpose'], questionnaire_version=self.questionnaire['questionnaire_version'],
                     wording_status=question['origin'], criterion_source=deepcopy(self.module()['criterion_source']))
        if value['format']=='likert':
            value['options'] = dict(zip(question['response_codes'], question['options']))
        return value

    def question(self):
        row = self.current
        if not row or row['state'] != 'collecting': return None
        if row['question_override']: return row['question_override']
        module = self.module()
        if self.profile=='citizen' and self.scope.get('likert_enabled') and row['likert'] is None:
            return self.question_record(module['optional_likert_items'][0])
        asked = [e for e in row['events'] if e['active'] and e['origin']=='indicator_interview']
        if not asked and not row['opening_reused']:
            first = module['question_order'][0]
            return self.question_record(next(q for q in module['questions'] if q['id']==first))
        candidate = next((q for q in self.candidates() if q['id']==row['next_question_id']), None)
        return self.question_record(candidate) if candidate else None

    def runtime_indicator(self, exclude=()):
        item = deepcopy(self.indicator(self.current_id))
        item['questionnaire_candidates'] = self.candidates(exclude)
        return item

    def advance_question(self):
        row = self.current
        count = sum(e['active'] and e['origin']=='indicator_interview' for e in row['events'])
        if row['state']=='collecting' and (count>=QUESTION_BUDGET or self.question() is None):
            row['state']='ready'

    def answer(self, text, control, client):
        row = self.current
        if row is None or row['state'] != 'collecting' or control not in {'answer', 'skip', 'unsure', 'decline'}:
            raise ValueError('No indicator question is awaiting an answer.')
        if len(text) > 2000 or (control == 'answer' and not text.strip()):
            raise ValueError('Use a short answer (up to 2,000 characters), or Skip/Not sure.')
        question = deepcopy(self.question())
        if question is None:
            raise ValueError('The indicator question budget is complete.')
        if question['format']=='likert':
            if control=='skip':
                row['likert']={'question_id':question['id'],'category':None,'label':'Skipped','agreement_category':None,
                    'response_state':'skipped','questionnaire_version':self.questionnaire['questionnaire_version']}
                self.revision += 1
                return
            key = text if control=='answer' else {'skip':'declined','unsure':'unsure','decline':'declined'}[control]
            if key not in question['options']: raise ValueError('Choose an exact Likert category.')
            row['likert'] = {'question_id': question['id'], 'category': key, 'label': question['options'][key],
                'agreement_category': question['response_codes'][key], 'questionnaire_version': self.questionnaire['questionnaire_version'],
                'information_context': 'after_information' if row['information'] else 'before_tool_information',
                'response_state':key if key in {'unsure','not_applicable','declined'} else 'selected',
                'meaning': 'Agreement category, never a readiness level.'}
            self.revision += 1
            return
        reading = (validate_reading(client.interpret(self.runtime_indicator([question['id']]), row['scope'], question['question_text'], text), text, self.candidates([question['id']]))
                   if control == 'answer' else {'meaning': {'skip': 'Question skipped.', 'unsure': 'You are unsure.',
                                                           'decline': 'You prefer not to answer.'}[control], 'observations': []})
        self.invalidate('New indicator evidence')
        row['evidence_revision'] += 1
        event = {'id': f"indicator_answer_{self.revision}", 'text': text if control == 'answer' else '',
                 'question': question, 'control': control, 'reading': reading, 'confirmed': control != 'answer',
                 'active': True, 'origin': 'indicator_interview', 'scope': deepcopy(row['scope']),
                 'information_context': 'after_information' if row['information'] else 'before_tool_information',
                 'interpretation_status': 'observations_extracted' if reading['observations'] else 'no_observations_extracted',
                 'independent_prior_knowledge': False if row['information'] else None, 'replaces': row.get('editing')}
        require_safe_data(event)
        row['question_override'] = None
        if control == 'answer':
            row.update(pending=event, state='interpretation')
        else:
            row['events'].append(event)
            row.update(state='ready', disposition={'skip':'skipped','unsure':'respondent_unsure','decline':'declined'}[control])

    def confirm(self):
        row = self.current
        if row is None or row['state'] != 'interpretation' or not row['pending']:
            raise ValueError('No indicator interpretation is awaiting confirmation.')
        row['pending']['confirmed'] = True
        row['next_question_id'] = row['pending']['reading'].get('next_question_id')
        row['events'].append(row['pending'])
        row.update(pending=None, state='collecting')
        row['evidence_revision'] += 1
        self.revision += 1
        self.advance_question()

    def correct(self, text, client):
        row = self.current
        if not row or not row['pending'] or not text.strip() or len(text) > 1500:
            raise ValueError('Describe the correction to this interpretation (up to 1,500 characters).')
        pending = row['pending']
        reading = validate_reading(client.interpret(self.runtime_indicator([pending['question']['id']]), row['scope'],
            pending['question']['question_text'], pending['text'], text), pending['text'], self.candidates([pending['question']['id']]))
        if reading.get('needs_answer_edit'):
            pending['correction_offer'] = {'text': text, 'notice': reading.get('correction_notice') or 'Add new facts through an answer addition, then check the interpretation.'}
            self.revision += 1
            return
        correction = {'feedback': text, 'previous_reading': deepcopy(pending['reading']),
                      'original_answer_unchanged': True}
        require_safe_data(correction)
        pending.setdefault('interpretation_history', []).append(correction)
        pending['reading'] = reading
        self.invalidate('Interpretation corrected')
        row['evidence_revision'] += 1

    def finish(self):
        if not self.current or self.current['state'] not in {'collecting','ready'}:
            raise ValueError('Confirm the interpretation before finishing this indicator.')
        self.current['state'] = 'ready'
        self.revision += 1

    def suggest(self, client, session_revision):
        row = self.current
        if row is None or row['state'] != 'ready' or row['tool'] is not None:
            raise ValueError('Collect/confirm evidence before requesting a suggestion. Revise evidence before reassessing.')
        scale = self.scale(self.current_id)
        evidence = self.evidence()
        if not evidence or row['disposition'] in {'outside_role','no_technical_object_identified','not_applicable_explained'}:
            result = {'assessments': [{'statement_id': s['id'], 'status': 'insufficient', 'evidence': [],
                                      'reason': 'No confirmed answer in the selected scope is available.'} for s in scale],
                      'selected_statement_id': None, 'explanation': 'No level is suggested: ' + (row['disposition'] or 'no confirmed answer') + '.',
                      'material_conflict': False, 'selection_unclear': True,
                      'gap': 'Understanding and relevant experience were not established.'}
        else:
            try:
                result = validate_match(client.match(self.indicator(self.current_id), row['scope'], scale, evidence), scale, evidence, row['scope'])
            except AssessmentError as exc:
                self.note_suggestion_failure(exc.code)
                raise
        row['suggestion_error']=None
        result['gaps'] = [result.pop('gap')] if result.get('gap') else []
        result.pop('gap', None)
        for assessment in result['assessments']:
            assessment['reason'] = {'supported': 'The model judged the full statement supported by the cited confirmed answer passages.',
                'insufficient': 'The available evidence does not establish the full statement; this is not evidence of inability.',
                'conflicting': 'Cited accounts conflict with this statement; see the selection explanation and evidence.'}[assessment['status']]
        selected = next((s for s in scale if s['id'] == result['selected_statement_id']), None)
        row['tool'] = {**result, 'status': 'suggested' if selected else 'abstained',
                       'statement': selected, 'policy_version': POLICY, 'evidence_revision': row['evidence_revision'],
                       'session_revision': session_revision, 'externally_verified': False}
        row.update(state='review', status=row['disposition'] or ('suggested' if selected else 'insufficient_evidence'))
        self.revision += 1

    def note_suggestion_failure(self, code):
        # No rejected model text or operational diagnostics become report data.
        if self.current and self.current['state']=='ready' and self.current['tool'] is None:
            self.current['suggestion_error']={'status':'unavailable',
                'code':code if code in {'schema','evidence','transport','timeout','budget','privacy','privacy_unavailable'} else 'model_failure',
                'notice':'No valid tool suggestion is available. You may choose your own source statement, remain unsure or decline.'}

    def review(self, choice, statement_id, explanation, revision):
        row = self.current
        if row is None or row['state'] not in {'ready', 'review', 'complete'} or revision != self.revision:
            raise ValueError('The assessment changed. Review the current suggestion and evidence first.')
        if choice not in {'endorse', 'select', 'unsure', 'decline'} or len(explanation) > 600:
            raise ValueError('Choose an assessment-review action; an explanation is optional (up to 600 characters).')
        if row['disposition'] in {'outside_role','no_technical_object_identified','not_applicable_explained'} and choice in {'endorse','select'}:
            raise ValueError('Establish an applicable responsibility or technical object before selecting a level.')
        scale = self.scale(self.current_id)
        tool_id = (row['tool'] or {}).get('selected_statement_id')
        if choice == 'endorse':
            if not tool_id or statement_id is not None:
                raise ValueError('There is no suggested statement to endorse.')
            selected = next(s for s in scale if s['id'] == tool_id)
        elif choice == 'select':
            selected = next((s for s in scale if s['id'] == statement_id), None)
            if selected is None:
                raise ValueError('Choose one of the nine profile-specific statements for this indicator.')
        else:
            if statement_id is not None:
                raise ValueError('Unsure/refusal carries no selected level.')
            selected = None
        if row['participant']:
            self.history.append({'indicator_id': self.current_id, 'participant': deepcopy(row['participant']),
                                 'reason': 'Participant revised their assessment review', 'status': 'superseded'})
        row['participant'] = {'status': {'endorse': 'endorsed', 'select': 'selected', 'unsure': 'unsure',
                                         'decline': 'declined'}[choice], 'statement': deepcopy(selected),
                              'explanation': explanation, 'disagrees_with_tool': bool(selected and tool_id and selected['id'] != tool_id),
                              'evidence_revision': row['evidence_revision'], 'review_revision': self.revision,
                              'evidence_ids': [e['evidence_id'] for e in self.evidence()],
                              'meaning': 'Explicit participant self-assessment; not independent verification.'}
        row.update(state='complete', status='completed' if selected else row['disposition'] or ('participant_unsure' if choice == 'unsure' else 'declined'))
        self.revision += 1

    def next(self, indicator_id):
        if indicator_id not in self.selected:
            raise ValueError('Choose a selected indicator.')
        if self.current and self.current['pending'] and indicator_id != self.current_id:
            raise ValueError('Resolve the pending interpretation before moving to another indicator.')
        self._ensure_row(indicator_id)
        self.current_id = indicator_id
        self.report_finished = False
        self.revision += 1
        self.advance_question()

    def edit(self, event_id, mode):
        row = self.current
        event = next((e for e in row['events'] if e['id'] == event_id and e['active'] and e['origin'] == 'indicator_interview'), None)
        if event is None or mode not in {'answer', 'interpretation'} or row['pending']:
            raise ValueError('Choose an active indicator answer to revise.')
        self.invalidate('Answer or interpretation reopened')
        self.invalidate_links({event_id})
        event['active'] = False
        row['evidence_revision'] += 1
        row['editing'] = event_id
        if mode == 'answer':
            row.update(state='collecting', question_override=deepcopy(event['question']))
        else:
            pending = deepcopy(event)
            pending.update(id=f'indicator_answer_{self.revision}', active=True, confirmed=False, replaces=event_id)
            row.update(state='interpretation', pending=pending)
        return event['text']

    def add_information(self, text, client):
        row = self.current
        if not row or not row['pending'] or not text.strip():
            raise ValueError('Add information to a pending answer, or reopen a confirmed answer first.')
        original = row['pending']
        combined = original['text'] + '\nAdditional information: ' + text
        if len(combined)>2000: raise ValueError('Edit the answer to keep it within 2,000 characters.')
        require_safe_data({'text':combined})
        previous_override, previous_editing = row['question_override'], row.get('editing')
        row.update(pending=None, state='collecting', question_override=deepcopy(original['question']), editing=original['id'])
        try:
            self.answer(combined, 'answer', client)
        except Exception:
            row.update(pending=original, state='interpretation', question_override=previous_override, editing=previous_editing)
            raise
        original.update(active=False, confirmed=False)
        row['events'].append(original)

    def read_more(self, kind='definition'):
        if kind not in {'definition','scale'} or not self.current:
            raise ValueError('Choose definition or source scale information.')
        row = self.current
        if not any(e['kind']==kind for e in row['information']):
            row['information'].append({'kind':kind, 'sequence':len(row['information'])+1,
                'text':self.indicator(self.current_id)['definition'] if kind=='definition' else 'Nine profile-specific source statements displayed.',
                'source':deepcopy(self.module()['definition_source']) if kind=='definition' else {'statement_ids':[s['id'] for s in self.scale(self.current_id)]},
                'meaning':'Supplied information, not prior competence or demonstrated development.'})
            self.revision += 1

    def finish_assessment(self):
        self.report_finished = True
        self.revision += 1

    def reusable_answers(self):
        if not self.current: return []
        return [deepcopy(e) for key,r in self.results.items() if key != self.current_id
                for e in r['events'] if e['active'] and e['confirmed'] and e['control']=='answer'
                and e['scope']==self.current['scope']]

    def link_answers(self, answer_ids):
        row = self.current
        if not row or row['pending'] or not 1<=len(answer_ids)<=3 or len(set(answer_ids))!=len(answer_ids):
            raise ValueError('Link one to three distinct compatible confirmed answers before proceeding.')
        candidates = {e['id']:e for e in self.reusable_answers()}
        if set(answer_ids)-set(candidates):
            raise ValueError('Linked answers must have the same response profile, object and context.')
        self.invalidate('Equivalent confirmed answers explicitly linked')
        for key in answer_ids:
            if key not in {e['id'] for e in row['events'] if e['active']}:
                event = candidates[key]
                event.update(origin='confirmed_indicator_reuse', relevance_basis='Participant explicitly linked equivalent opening evidence; the full words still need to establish this criterion.')
                row['events'].append(event)
        row.update(opening_reused=True, state='collecting')
        row['evidence_revision'] += 1
        self.advance_question()

    def view(self):
        row = deepcopy(self.current)
        if row:
            readings = [e['reading'] for e in row['events']]
            if row['pending']:
                readings.append(row['pending']['reading'])
            for reading in readings:
                for observation in reading['observations']:
                    observation['review_description'] = observation_description(observation)
            item = self.indicator(self.current_id)
            row.update(name=item['name'], definition=item['definition'], criterion=deepcopy(item['assessment_criteria'][self.profile]),
                       scale=self.scale(self.current_id), question=self.question(),
                       question_budget=QUESTION_BUDGET, scale_name=PROFILES[self.profile], module_id=self.module()['id'],
                       scope_note=self.module()['scope_note'], confirmed_evidence=self.evidence(),
                       participation_barriers=[{'evidence_id': e['evidence_id'], 'quote': o['quote']}
                           for e in self.evidence() for o in e['observations'] if o['kind'] == 'barrier'])
        coverage = [{'indicator_id': i['id'], 'name': i['name'],
                     'status': self.results[i['id']]['status'] if i['id'] in self.results else 'not_assessed',
                     'selected': i['id'] in self.selected,
                     'answered': any(e['active'] and e['confirmed'] and e['control']=='answer' for e in self.results.get(i['id'], {}).get('events', [])),
                     'scope': deepcopy(self.results.get(i['id'], {}).get('scope')),
                     'unconfirmed': bool(self.results.get(i['id'], {}).get('pending')),
                     'disposition': self.results.get(i['id'], {}).get('disposition'),
                     'suggestion_error': deepcopy(self.results.get(i['id'], {}).get('suggestion_error')),
                     'participant': deepcopy(self.results[i['id']]['participant']) if i['id'] in self.results else None,
                     'tool': deepcopy(self.results[i['id']]['tool']) if i['id'] in self.results else None}
                    for i in self.bank['indicators']]
        return {'schema_version': SCHEMA, 'policy_version': POLICY, 'bank': self.identity(), 'questionnaire': self.questionnaire_identity(), 'profile': self.profile,
                'scale_name': PROFILES[self.profile], 'report_finished': self.report_finished,
                'sections': deepcopy(self.questionnaire['protocol']['sections']),
                'reusable_answers': [{'id':e['id'],'text':e['text']} for e in self.reusable_answers()],
                'notice': NOTICE, 'revision': self.revision, 'selected_indicator_ids': self.selected,
                'scope': deepcopy(self.scope), 'current': row, 'coverage': coverage,'presented_cases':deepcopy(self.presented_cases)}

    def export(self):
        value = self.view()
        value.pop('current')  # No nine-level bank copy for each unassessed indicator.
        value['results'] = deepcopy(list(self.results.values()))
        value['superseded_judgments'] = deepcopy(self.history)
        return value
