"""Shared, bounded citizen indicator continuation; separate tool/participant judgments."""
from copy import deepcopy
from hashlib import sha256
import json
from .readiness_bank import load_bank, validate_bank
from .indicator_client import POLICY, validate_reading, validate_match
from .privacy import require_safe_data

SCHEMA = 'indicator-self-assessment-1.0.0'
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
              'third_party': 'another person’s reasoning or action', 'unclear': 'whose reasoning or action is unclear'}
    times = {'actual': 'reported as actual, not independently verified', 'hypothetical': 'hypothetical',
             'unspecified': 'actual experience not established'}
    domains = {'IAM': 'about IAM', 'other': 'about another domain', 'unclear': 'domain unclear'}
    return ' · '.join((kinds[observation['kind']], actors[observation['actor']],
                       times[observation['actuality']], domains[observation['domain']]))


def resolved_scale(bank, indicator_id):
    rows = {r['id']: r for r in bank['review_rows']}
    labels = {r['level']: r['description'].split('. ', 1)[0] for r in bank['generic_scales']['CRL']}
    return [{**deepcopy(s), 'label': labels[s['level']],
             'row_review_status': rows[s['review_row_id']]['status'],
             'row_review_comment': rows[s['review_row_id']]['comment'],
             'review_source': deepcopy(rows[s['review_row_id']]['source'])}
            for s in sorted(bank['statements'], key=lambda r: r['level'])
            if s['indicator_id'] == indicator_id and s['profile'] == 'citizen' and s['scale'] == 'CRL']


class IndicatorAssessment:
    def __init__(self, bank=None):
        self.bank = deepcopy(bank) if bank is not None else load_bank()
        validate_bank(self.bank)
        self.revision = 0
        self.scope = None
        self.selected = []
        self.current_id = None
        self.results = {}
        self.history = []

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
        return resolved_scale(self.bank, key)

    def invalidate(self, reason, all_results=False):
        targets = self.results.values() if all_results else [self.current] if self.current else []
        for row in targets:
            if row['tool'] is not None or row['participant'] is not None:
                self.history.append({'indicator_id': row['indicator_id'], 'scope': deepcopy(row['scope']),
                    'evidence_revision': row['evidence_revision'], 'tool': deepcopy(row['tool']),
                    'participant': deepcopy(row['participant']), 'reason': reason, 'status': 'superseded'})
            row.update(tool=None, participant=None, status='not_assessed')
        self.revision += 1

    def select(self, indicator_ids, scope, reuse):
        known = {i['id'] for i in self.bank['indicators']}
        if not 1 <= len(indicator_ids) <= 3 or len(set(indicator_ids)) != len(indicator_ids) or set(indicator_ids) - known:
            raise ValueError('Choose one to three distinct indicators from the source bank.')
        if set(reuse) - set(indicator_ids):
            raise ValueError('Reuse evidence only for an explicitly selected indicator.')
        if self.scope is not None and scope != self.scope:
            self.invalidate('Assessment scope changed', all_results=True)
            for row in self.results.values():
                row['state'] = 'superseded'
        self.scope = deepcopy(scope)
        self.selected = list(indicator_ids)
        for key in indicator_ids:
            previous = self.results.get(key)
            if previous is not None:
                self.current_id = key
                self.invalidate('Indicator restarted with selected scope/evidence')
                # Keep immutable answer revisions, not a copy of the whole session.
                old_events = previous['events']
                for e in old_events:
                    e['active'] = False
            else:
                old_events = []
            self.results[key] = {'indicator_id': key, 'scope': deepcopy(scope), 'state': 'collecting',
                'status': 'not_assessed', 'events': old_events, 'pending': None, 'tool': None, 'participant': None,
                'evidence_revision': 0, 'question_override': None}
            for event in reuse.get(key, []):
                self.results[key]['events'].append(deepcopy(event))
        self.current_id = indicator_ids[0]
        self.revision += 1
        self.advance_question()

    def evidence(self):
        return [{'evidence_id': e['id'], 'answer': e['text'], 'meaning': e['reading']['meaning'],
                 'observations': deepcopy(e['reading']['observations']),
                 'information_context': e['information_context'], 'origin': e['origin'],
                 'scope': deepcopy(e['scope'])}
                for e in self.current['events'] if e['active'] and e['confirmed'] and e['control'] == 'answer']

    def question(self):
        row = self.current
        if not row or row['state'] != 'collecting':
            return None
        if row['question_override']:
            return row['question_override']
        evidence = self.evidence()
        kinds = {o['kind'] for e in evidence for o in e['observations'] if o['actor'] == 'self' and o['domain'] == 'IAM'}
        asked = {e['question']['intent'] for e in row['events'] if e['active'] and e['origin'] == 'indicator_interview'}
        name = self.indicator(self.current_id)['name']
        intents = []
        if not kinds.intersection({'reasoning'}):
            intents.append(('understanding', f'Thinking about {name}, how could IAM affect people in your chosen context?'))
        if 'condition' not in kinds:
            intents.append(('conditions', 'What conditions or safeguards, if any, would you propose for this issue?'))
        if not kinds.intersection({'influence', 'agency'}):
            if kinds.intersection({'activity', 'contribution'}):
                text = 'What, if anything, changed as a result of your own input?'
            elif 'barrier' in kinds:
                text = 'What do you feel able to contribute if a suitable opportunity becomes available?'
            else:
                text = 'What involvement, if any, have you personally had in shaping decisions about this issue?'
            intents.append(('participation', text))
        for intent, text in intents:
            if intent not in asked:
                level = {'understanding': 3, 'conditions': 5, 'participation': 7}[intent]
                anchor = next(s for s in self.scale(self.current_id) if s['level'] == level)
                return {'id': f'{self.current_id}-{intent}', 'intent': intent, 'question_text': text,
                        'wording_status': 'authored_prototype_not_FN_question_or_KVI',
                        'statement_references': [anchor['id']], 'criterion_source':
                        deepcopy(self.indicator(self.current_id)['assessment_criteria']['citizen']['source'])}
        return None

    def advance_question(self):
        row = self.current
        count = sum(e['active'] and e['origin'] == 'indicator_interview' for e in row['events'])
        if row['state'] == 'collecting' and (count >= QUESTION_BUDGET or self.question() is None):
            row['state'] = 'ready'

    def answer(self, text, control, client):
        row = self.current
        if row is None or row['state'] != 'collecting' or control not in {'answer', 'skip', 'unsure', 'decline'}:
            raise ValueError('No indicator question is awaiting an answer.')
        if len(text) > 2000 or (control == 'answer' and not text.strip()):
            raise ValueError('Use a short answer (up to 2,000 characters), or Skip/Not sure.')
        question = deepcopy(self.question())
        if question is None:
            raise ValueError('The indicator question budget is complete.')
        reading = (validate_reading(client.interpret(self.indicator(self.current_id), row['scope'], question['question_text'], text), text)
                   if control == 'answer' else {'meaning': {'skip': 'Question skipped.', 'unsure': 'You are unsure.',
                                                           'decline': 'You prefer not to answer.'}[control], 'observations': []})
        self.invalidate('New indicator evidence')
        row['evidence_revision'] += 1
        event = {'id': f"indicator_answer_{self.revision}", 'text': text if control == 'answer' else '',
                 'question': question, 'control': control, 'reading': reading, 'confirmed': control != 'answer',
                 'active': True, 'origin': 'indicator_interview', 'scope': deepcopy(row['scope']),
                 'information_context': 'after_tool_definitions', 'independent_prior_knowledge': False, 'replaces': row.get('editing')}
        require_safe_data(event)
        row['question_override'] = None
        if control == 'answer':
            row.update(pending=event, state='interpretation')
        else:
            row['events'].append(event)
            row['state'] = 'ready'  # Do not repeatedly probe a declined/uncertain topic.

    def confirm(self):
        row = self.current
        if row is None or row['state'] != 'interpretation' or not row['pending']:
            raise ValueError('No indicator interpretation is awaiting confirmation.')
        row['pending']['confirmed'] = True
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
        reading = validate_reading(client.interpret(self.indicator(self.current_id), row['scope'],
            pending['question']['question_text'], pending['text'], text), pending['text'])
        correction = {'feedback': text, 'previous_reading': deepcopy(pending['reading']),
                      'original_answer_unchanged': True}
        require_safe_data(correction)
        pending.setdefault('interpretation_history', []).append(correction)
        pending['reading'] = reading
        self.invalidate('Interpretation corrected')
        row['evidence_revision'] += 1

    def finish(self):
        if not self.current or self.current['state'] != 'collecting':
            raise ValueError('Confirm the interpretation before finishing this indicator.')
        self.current['state'] = 'ready'
        self.revision += 1

    def suggest(self, client, session_revision):
        row = self.current
        if row is None or row['state'] != 'ready' or row['tool'] is not None:
            raise ValueError('Collect/confirm evidence before requesting a suggestion. Revise evidence before reassessing.')
        scale = self.scale(self.current_id)
        evidence = self.evidence()
        if not any(e['observations'] for e in evidence):
            result = {'assessments': [{'statement_id': s['id'], 'status': 'insufficient', 'evidence': [],
                                      'reason': 'No confirmed relevant observation is available.'} for s in scale],
                      'selected_statement_id': None, 'explanation': 'Insufficient evidence; no level is suggested.',
                      'material_conflict': False, 'selection_unclear': True,
                      'gap': 'Understanding and relevant experience were not established.'}
        else:
            result = validate_match(client.match(self.indicator(self.current_id), row['scope'], scale, evidence), scale, evidence)
        result['gaps'] = [result.pop('gap')] if result.get('gap') else []
        result.pop('gap', None)
        for assessment in result['assessments']:
            assessment['reason'] = {'supported': 'The model judged the full statement supported by the cited confirmed observations.',
                'insufficient': 'The available evidence does not establish the full statement; this is not evidence of inability.',
                'conflicting': 'Cited accounts conflict with this statement; see the selection explanation and evidence.'}[assessment['status']]
        selected = next((s for s in scale if s['id'] == result['selected_statement_id']), None)
        row['tool'] = {**result, 'status': 'suggested' if selected else 'abstained',
                       'statement': selected, 'policy_version': POLICY, 'evidence_revision': row['evidence_revision'],
                       'session_revision': session_revision, 'externally_verified': False}
        row.update(state='review', status='suggested' if selected else 'insufficient_evidence')
        self.revision += 1

    def review(self, choice, statement_id, explanation, revision):
        row = self.current
        if row is None or row['state'] not in {'ready', 'review', 'complete'} or revision != self.revision:
            raise ValueError('The assessment changed. Review the current suggestion and evidence first.')
        if choice not in {'endorse', 'select', 'unsure', 'decline'} or len(explanation) > 600:
            raise ValueError('Choose an assessment-review action; an explanation is optional (up to 600 characters).')
        scale = self.scale(self.current_id)
        tool_id = (row['tool'] or {}).get('selected_statement_id')
        if choice == 'endorse':
            if not tool_id or statement_id is not None:
                raise ValueError('There is no suggested statement to endorse.')
            selected = next(s for s in scale if s['id'] == tool_id)
        elif choice == 'select':
            selected = next((s for s in scale if s['id'] == statement_id), None)
            if selected is None:
                raise ValueError('Choose one of the nine citizen statements for this indicator.')
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
        row.update(state='complete', status='completed' if selected else 'participant_unsure' if choice == 'unsure' else 'declined')
        self.revision += 1

    def next(self, indicator_id):
        if indicator_id not in self.selected:
            raise ValueError('Choose a selected indicator.')
        self.current_id = indicator_id
        self.revision += 1
        self.advance_question()

    def edit(self, event_id, mode):
        row = self.current
        event = next((e for e in row['events'] if e['id'] == event_id and e['active'] and e['origin'] == 'indicator_interview'), None)
        if event is None or mode not in {'answer', 'interpretation'} or row['pending']:
            raise ValueError('Choose an active indicator answer to revise.')
        self.invalidate('Answer or interpretation reopened')
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
            row.update(name=item['name'], definition=item['definition'], criterion=deepcopy(item['assessment_criteria']['citizen']),
                       scale=self.scale(self.current_id), question=self.question(),
                       question_budget=QUESTION_BUDGET, confirmed_evidence=self.evidence(),
                       participation_barriers=[{'evidence_id': e['evidence_id'], 'quote': o['quote']}
                           for e in self.evidence() for o in e['observations'] if o['kind'] == 'barrier'])
        coverage = [{'indicator_id': i['id'], 'name': i['name'],
                     'status': self.results[i['id']]['status'] if i['id'] in self.results else 'not_assessed',
                     'selected': i['id'] in self.selected,
                     'participant': deepcopy(self.results[i['id']]['participant']) if i['id'] in self.results else None,
                     'tool': deepcopy(self.results[i['id']]['tool']) if i['id'] in self.results else None}
                    for i in self.bank['indicators']]
        return {'schema_version': SCHEMA, 'policy_version': POLICY, 'bank': self.identity(), 'profile': 'citizen',
                'notice': NOTICE, 'revision': self.revision, 'selected_indicator_ids': self.selected,
                'scope': deepcopy(self.scope), 'current': row, 'coverage': coverage}

    def export(self):
        value = self.view()
        value.pop('current')  # No nine-level bank copy for each unassessed indicator.
        value['results'] = deepcopy(list(self.results.values()))
        value['superseded_judgments'] = deepcopy(self.history)
        return value
