"""Confirmation-gated descriptive interviews, isolated from historical arithmetic."""
import json
from copy import deepcopy
from uuid import uuid4
from .privacy import VERSION as PRIVACY_VERSION, guarded, export_guard, require_safe_data
from .assessment import check_input
from .evidence import passages
from .interpretation import EvidenceItem, digest
from .settings import SCENARIO, config
from .readiness import DEFAULT_MODE, build_profile, next_question, profile_changes, citizen_result, mode_policy, validate_extraction


class ReadinessSession:
    def __init__(self, *, question_budget=None):
        self.privacy_contract = PRIVACY_VERSION
        self.session_id = str(uuid4())
        self.instrument = deepcopy(config('readiness'))
        self.numerical_policy = mode_policy()
        self._mode_version = config('assessment_modes')['version']
        self.scenario = deepcopy(SCENARIO)
        self._source_prompt_hash = self._prompt_hash()
        from hashlib import sha256
        from .settings import ROOT
        self._grounding_prompt_hash = sha256((ROOT/'prompts/readiness-grounding.txt').read_bytes()).hexdigest()
        self.state = 'answer'
        self.version = 0
        self.evidence = {}
        self.events = []
        self.pending = None
        self.draft_text = ''
        self.confirmations = []
        self.corrections = []
        self.inference = []
        self.information_exposures = []
        self.information_module = deepcopy(config('readiness_information'))
        from .readiness_retrieval import corpus
        self.retrieval_corpus = corpus()
        self.retrieval_corpus['passages'] = [p for p in self.retrieval_corpus['passages']
                                             if 'citizen_explanation' in p['permitted_use']]
        self.pre_information_snapshot = None
        self.information_acknowledgements = []
        self.learning_pending = False
        self._initial_readiness = None
        self._final_readiness = None
        self._initial_snapshots = []
        self._current_initial_confirmed = False
        self.stop_reason = None
        self.question_budget = self.instrument['maximum_questions'] if question_budget is None else question_budget
        if type(self.question_budget) is not int or not 0 <= self.question_budget <= self.instrument['maximum_questions']:
            raise ValueError('Question budget must be between zero and the configured maximum.')
        self.assessment_participation = {'activity': 'this chat', 'type': 'assessment_participation',
            'engagement_or_codesign_awarded': False, 'influence_established': False,
            'note': 'Completing this assessment does not establish engagement, co-design, influence or a CRL level.'}

    @property
    def assessment_mode(self): return DEFAULT_MODE

    @guarded()
    def record_information_exposure(self):
        # Preserve the old public method, with explicit display/ack events for
        # new calls. Previously saved exposure dictionaries are never rewritten.
        displays = [e for e in self.information_exposures
                    if e['source'] == 'controlled_demo_explanation_display']
        exposure = displays[-1] if displays else self.display_information()
        self.acknowledge_information(exposure['exposure_id'])

    @guarded('content')
    def _log_display(self, content, source):
        from datetime import datetime, timezone
        require_safe_data(content)
        if not self._current_initial_confirmed or self.pending is not None:
            raise ValueError('Confirm your interpretation before displaying information.')
        if not hasattr(self, 'pre_information_snapshot') or self.pre_information_snapshot is None:
            self.pre_information_snapshot = deepcopy(self.current_profile)
        exposure = {'exposure_id': 'display_' + str(len(self.information_exposures) + 1),
            'sequence': len(self.information_exposures) + 1,
            'displayed_at': datetime.now(timezone.utc).isoformat(),
            'version_at_exposure': self.version, 'source': source,
            'display': True, 'acknowledgement': False,
            'understanding_verified': False, 'content': deepcopy(content)}
        self.information_exposures.append(exposure)
        return deepcopy(exposure)

    @guarded()
    def display_faq(self, faq_id):
        module = config('readiness_information')
        entry = next((f for f in module.get('faqs', []) if f['id'] == faq_id), None)
        if entry is None: raise ValueError('Select an available frequently asked question.')
        passages = {p['id']:p for p in self.retrieval_corpus['passages']}
        if any(pid not in passages for pid in entry['passage_ids']):
            raise ValueError('FAQ sources are unavailable; no answer was displayed.')
        return self._log_display({'id':entry['id'],'question':entry['question'],
            'answer':entry['answer'],'module_version':module['version'],
            'review_status':module['review_status'],'approved_by':module['approved_by'],
            'sources':[deepcopy(passages[pid]) for pid in entry['passage_ids']]}, 'controlled_faq_display')

    @guarded()
    def display_information(self):
        return self._log_display(getattr(self, 'information_module', config('readiness_information')),
                                 'controlled_demo_explanation_display')

    @guarded('question')
    def ask_information(self, question, client=None):
        from .readiness_retrieval import corpus, explain
        if not self._current_initial_confirmed or self.pending is not None:
            raise ValueError('Confirm your interpretation before displaying information.')
        collection = getattr(self, 'retrieval_corpus', corpus())
        count = sum(e['source'] == 'local_retrieval_display' for e in self.information_exposures)
        if count >= collection['maximum_requests_per_session']:
            raise ValueError('The optional information budget has been reached.')
        answer = explain(question, client, collection=collection)
        return self._log_display(answer, 'local_retrieval_display')

    @guarded()
    def acknowledge_information(self, exposure_id):
        from datetime import datetime, timezone
        if not any(e.get('exposure_id') == exposure_id for e in self.information_exposures):
            raise ValueError('Select displayed information to acknowledge.')
        if not hasattr(self, 'information_acknowledgements'): self.information_acknowledgements = []
        if not any(a['exposure_id'] == exposure_id for a in self.information_acknowledgements):
            self.information_acknowledgements.append({'exposure_id': exposure_id,
                'acknowledged_at': datetime.now(timezone.utc).isoformat(), 'meaning': 'citizen_clicked_read',
                'understanding_verified': False})

    @guarded()
    def start_learning(self, exposure_id=None):
        if not self._current_initial_confirmed or self.pending is not None:
            raise ValueError('Confirm your first interpretation before the optional explanation.')
        if exposure_id is None:
            self.record_information_exposure()
        else:
            self.acknowledge_information(exposure_id)
        # Information alone adds no semantic evidence and never rewrites a score.
        check_id = getattr(self, 'information_module', config('readiness_information'))['understanding_check']['id']
        if len(self.answers) < self.question_budget and not any(a['question']['id'] == check_id for a in self.answers):
            self.learning_pending = True
            self._final_readiness = None
            self.state = 'interview'

    @property
    def mode_version(self): return self._mode_version

    @property
    def initial_readiness(self): return deepcopy(self._initial_readiness)

    @property
    def final_readiness(self): return deepcopy(self._final_readiness)

    def _verify_confirmed(self):
        for event in self.events:
            if not event['active'] or event['control'] in {'skip', 'unsure'}: continue
            confirmation = next((c for c in self.confirmations if c['event_id'] == event['id'] and c.get('active', True)), None)
            if confirmation is None or confirmation.get('sha256') != digest(event):
                raise ValueError('Confirmed interpretation changed; correct and confirm it again.')

    @property
    def answers(self):
        return [deepcopy(e) for e in self.events if e['active'] and e['kind'] == 'readiness_followup']

    @property
    def current_profile(self):
        self._verify_confirmed()
        records = [r for e in self.events if e['active'] for r in e['records']]
        profile = build_profile(records, [a['criterion_id'] for a in self.answers], self.instrument)
        profile['unavailable_reason'] = self.numerical_policy['unavailable_reason']
        for answer in self.answers:
            coverage = profile['criterion_coverage'][answer['criterion_id']]
            if not coverage['evidence_ids'] and answer['control'] in {'skip', 'unsure'}:
                coverage['status'] = 'unclear' if answer['control'] == 'unsure' else 'skipped'
        return profile

    @property
    def acceptance(self):
        self._verify_confirmed()
        # Context-specific findings never overwrite the unchanged proposal.
        views = [e['acceptance'] for e in self.events if e['active'] and e['context'] == 'original' and e.get('acceptance')]
        original = {'stance': 'not_stated', 'evidence_ids': [], 'concerns': [], 'conditions': [], 'topic_ids': [], 'concern_facets': [], 'policy_preferences': []}
        original['medical_public_benefit_support'] = 'not_stated'
        stance_claims = set()
        for view in views:
            medical = view.get('medical_public_benefit_support', 'not_stated')
            if medical != 'not_stated': original['medical_public_benefit_support'] = medical
            if view['stance'] != 'not_stated':
                original['stance'] = view['stance']; stance_claims.add(view['stance'])
            for field in ['evidence_ids', 'concerns', 'conditions', 'topic_ids', 'concern_facets', 'policy_preferences']:
                original[field] = list(dict.fromkeys(original[field] + view.get(field, [])))
        original['unresolved_stance_conflict'] = 'supported' in stance_claims and 'opposed' in stance_claims
        return {'original_proposal': original,
                'optional_hypothetical_findings': [deepcopy(e) for e in self.events if e['active'] and e['context'] == 'hypothetical_modification']}

    @property
    def current_question(self):
        if self.state != 'interview': return None
        if getattr(self, 'learning_pending', False) and len(self.answers) < self.question_budget:
            return deepcopy(getattr(self, 'information_module', config('readiness_information'))['understanding_check'])
        return next_question(self.current_profile, self.answers, self.question_budget, self.instrument)

    @guarded('text')
    def _extract(self, text, client, *, kind, criterion=None, question=None, context='original', control='answer'):
        check_input(text)
        self.draft_text = text  # Retained even if model or validation fails.
        event_id = 'R' + str(self.version + 1) + '_' + str(len(self.events) + 1)
        evidence = {event_id + '.' + k: EvidenceItem(id=event_id + '.' + k, text=v, context=context,
                    source='citizen_original' if kind == 'initial' else 'citizen_correction' if kind == 'correction' else 'citizen_readiness',
                    question_id=question['id'] if question else None) for k, v in passages(text).items()}
        if hasattr(client, 'bind_session'): client.bind_session(self.session_id, self.version)
        elicitation = 'initial_answer' if kind == 'initial' else 'follow_up'
        if getattr(self, 'information_exposures', []): elicitation = 'after_information_exposure'
        try:
            result = client.extract_readiness(evidence, elicitation=elicitation, context=context, version=self.version + 1,
                question=question['question_text'] if question else None, existing=self.current_profile['records'])
            require_safe_data(result)
            # Doubles and alternative clients pass through the same checks.
            result = validate_extraction(result.model_dump(), evidence, elicitation, context, self.version + 1)
        finally:
            require_safe_data({'diagnostics':getattr(client, 'last_diagnostics', []), 'settings':getattr(client, 'last_settings', {}), 'trace':getattr(client, 'last_trace', [])})
            self.inference.append({'stage': 'readiness_evidence', 'version': self.version + 1,
                'diagnostics': deepcopy(getattr(client, 'last_diagnostics', [])),
                'settings': deepcopy(getattr(client, 'last_settings', {})),
                'raw_model_trace': deepcopy(getattr(client, 'last_trace', []))})
        self.pending = {'id': event_id, 'kind': kind, 'criterion_id': criterion, 'question': deepcopy(question),
            'text': text, 'control': control, 'context': context, 'acceptance': result.acceptance.model_dump(),
            'records': [r.model_dump() for r in result.records], 'evidence_ids': list(evidence), 'active': True,
            'version': self.version + 1, 'evidence': {k: v.model_dump() for k, v in evidence.items()}}
        review = getattr(client, 'last_settings', {}).get('readiness_grounding', {})
        self.pending['interaction'] = review.get('interaction', 'substantive')
        if self.pending['interaction'] in {'declined', 'already_answered'}:
            self.pending['control'] = 'decline'
        self.state = 'review'

    @guarded()
    def retry_interpretation(self, client):
        if self.state != 'review' or not self.pending:
            raise ValueError('Re-read an answer only while reviewing its interpretation.')
        pending = deepcopy(self.pending)
        self._extract(pending['text'], client, kind=pending['kind'],
            criterion=pending['criterion_id'], question=pending['question'],
            context=pending['context'], control=pending['control'])

    @guarded('text')
    def submit(self, text, client):
        if self.state != 'answer': raise ValueError('Submit a first answer only on the answer page.')
        self._extract(text, client, kind='initial')

    @guarded('text')
    def respond(self, text, client):
        q = self.current_question
        if q is None: raise ValueError('No readiness question is pending.')
        self._extract(text, client, kind='readiness_followup', criterion=q['criterion_id'], question=q)

    @guarded()
    def confirm(self, agreed):
        if not agreed or self.pending is None: raise ValueError('Confirm the interpretation before continuing.')
        event = deepcopy(self.pending)
        if (event.get('question') or {}).get('id') == getattr(self, 'information_module', config('readiness_information'))['understanding_check']['id']:
            self.learning_pending = False
        for record in event['records']: record['confirmation_status'] = 'confirmed'
        self.version = event['version']
        self.evidence.update({k: EvidenceItem.model_validate(v) for k, v in event.pop('evidence').items()})
        self.events.append(event)
        self.confirmations.append({'version': self.version, 'event_id': event['id'], 'sha256': digest(event),
            'scope': 'interpretation_only', 'active': True, 'external_truth_verified': False, 'criterion_validity_verified': False})
        self.pending = None; self.draft_text = ''; self._final_readiness = None
        if event['kind'] == 'initial':
            snapshot = self.current_profile
            self._initial_snapshots.append(deepcopy(snapshot))
            if self._initial_readiness is None: self._initial_readiness = deepcopy(snapshot)
            self._current_initial_confirmed = True
        if event['kind'] == 'optional_acceptance':
            self.finish(self.stop_reason or 'user_finish'); return
        self.state = 'interview'
        if self.current_question is None:
            self.finish('question_budget' if len(self.answers) >= self.question_budget else 'sufficient_evidence_or_no_eligible_questions')

    @guarded()
    def skip(self, unsure=False):
        q = self.current_question
        if q is None: raise ValueError('No readiness question is pending.')
        self.learning_pending = False
        self.version += 1
        key = 'control_' + str(self.version)
        self.evidence[key] = EvidenceItem(id=key, text='Unsure' if unsure else 'Skipped', context='original', source='citizen_control', question_id=q['id'])
        self.events.append({'id': key, 'kind': 'readiness_followup', 'criterion_id': q['criterion_id'], 'question': q,
            'control': 'unsure' if unsure else 'skip', 'text': '', 'context': 'original', 'records': [],
            'acceptance': None, 'evidence_ids': [key], 'active': True, 'version': self.version})
        self._final_readiness = None
        if self.current_question is None: self.finish('question_budget' if len(self.answers) >= self.question_budget else 'sufficient_evidence_or_no_eligible_questions')

    @guarded()
    def finish(self, reason='user_finish'):
        if not self._current_initial_confirmed or self.pending is not None:
            raise ValueError('Confirm the current first answer and pending interpretation before finishing.')
        if reason not in {'user_finish', 'question_budget', 'sufficient_evidence_or_no_eligible_questions'}:
            raise ValueError('Unknown interview stop reason.')
        self.stop_reason = reason
        self.learning_pending = False
        self._final_readiness = deepcopy(self.current_profile)
        self.state = 'final'

    @guarded()
    def edit_answer(self, event_id):
        event = next((e for e in self.events if e['id'] == event_id and e['active']), None)
        if event is None: raise ValueError('Choose an active answer to correct.')
        self.corrections.append({'event_id': event_id, 'version': self.version,
            'previous_final_profile': self.final_readiness, 'reason': 'citizen_edit',
            'superseded_confirmations': [c for c in self.confirmations if c['version'] >= event['version']]})
        for confirmation in self.confirmations:
            if confirmation['version'] >= event['version']: confirmation['active'] = False
        for other in self.events:
            if other['version'] >= event['version']: other['active'] = False
        self.version += 1; self.pending = None; self._final_readiness = None; self.stop_reason = None
        self.learning_pending = False
        self.draft_text = event['text']
        self._editing = deepcopy(event)
        if event['kind'] == 'initial':
            self._current_initial_confirmed = False; self.state = 'answer'
        else: self.state = 'correction'

    @guarded('text')
    def correct(self, text, client):
        if self.state == 'answer': return self.submit(text, client)
        if self.state not in {'correction', 'review'}: raise ValueError('Select an answer to correct first.')
        event = self.pending if self.state == 'review' else self._editing
        self._extract(text, client, kind=event['kind'], criterion=event['criterion_id'],
            question=event['question'], context=event['context'])

    @guarded('text')
    def explore_acceptance(self, facet, choice, text, client):
        if self.state != 'final': raise ValueError('Complete the readiness interview first.')
        if sum(e['active'] and e['kind'] == 'optional_acceptance' for e in self.events) >= 2:
            raise ValueError('The optional exploration budget is two questions.')
        mitigations = config('updates')['mitigations']
        choices = ['Would address my concern', 'Would partly address my concern', 'Would not address my concern', 'Unsure']
        if facet not in mitigations or choice not in choices: raise ValueError('Choose an offered aspect and answer.')
        if facet not in self.acceptance['original_proposal']['concern_facets']:
            raise ValueError('Only explicitly evidenced concern aspects can be explored.')
        question = {'id': 'optional_' + facet, 'question_text': mitigations[facet], 'feasibility': 'hypothetical_unverified'}
        # Choice alone never enters readiness extraction, and never changes a number.
        self.version += 1; key = 'optional_' + str(self.version)
        self.evidence[key] = EvidenceItem(id=key, text=choice, context='hypothetical_modification', source='citizen_choice', question_id=question['id'])
        base = {'id': key, 'kind': 'optional_acceptance', 'criterion_id': None, 'question': question,
            'text': text, 'choice': choice, 'control': 'answer', 'context': 'hypothetical_modification', 'acceptance': None,
            'records': [], 'evidence_ids': [key], 'active': True, 'version': self.version}
        if text.strip():
            self._extract(text, client, kind='optional_acceptance', question=question, context='hypothetical_modification')
            self.pending['choice'] = choice
            self.pending['evidence_ids'].append(key)
        else:
            self.events.append(base)
            self.confirmations.append({'event_id': key, 'version': self.version, 'scope': 'explicit_choice_only', 'active': True, 'sha256': digest(base)})
            self._final_readiness = deepcopy(self.current_profile)

    @export_guard
    def export(self):
        from .readiness_score import current_score
        final = self.final_readiness
        return {**({'baseline_provenance':deepcopy(self.baseline_provenance), 'baseline_handoff':deepcopy(self.baseline_handoff)} if hasattr(self,'baseline_provenance') else {}),
            'schema_version': '6.5.0' if hasattr(self,'baseline_provenance') else '6.4.0', 'privacy_contract': self.privacy_contract, 'assessment_mode': self.assessment_mode, 'mode_version': self.mode_version,
            'instrument': deepcopy(self.instrument), 'session_id': self.session_id, 'state': self.state,
            'scenario': deepcopy(self.scenario), 'acceptance_profile': self.acceptance,
            'initial_readiness_profile': self.initial_readiness, 'initial_readiness_snapshots': deepcopy(self._initial_snapshots),
            'final_readiness_profile': final,
            'readiness_changes': profile_changes(self.initial_readiness, final) if final else None,
            'readiness_score_status': {'status': 'unavailable_pending_methodological_approval', 'numerical_crl': None,
                'numerical_srl': None, 'reason': self.numerical_policy['unavailable_reason']},
            'numerical_crl': None, 'numerical_srl': None,
            'provisional_workbook_score': current_score(self),
            'question_budget': self.question_budget, 'stop_reason': self.stop_reason,
            'questions_and_answers': deepcopy(self.events), 'pending_interpretation': deepcopy(self.pending),
            'information_exposures': deepcopy(getattr(self, 'information_exposures', [])),
            'information_module': deepcopy(getattr(self, 'information_module', config('readiness_information'))),
            'pre_information_snapshot': deepcopy(getattr(self, 'pre_information_snapshot', None)),
            'information_acknowledgements': deepcopy(getattr(self, 'information_acknowledgements', [])),
            'retrieval_corpus': deepcopy(getattr(self, 'retrieval_corpus', None)),
            'evidence': {k: v.model_dump() for k, v in self.evidence.items()},
            'confirmations': deepcopy(self.confirmations), 'corrections': deepcopy(self.corrections),
            'assessment_participation': deepcopy(self.assessment_participation),
            'citizen_result': citizen_result(self),
            'provenance': {'model': config('model'), 'prompts': config('prompts'), 'registry_version': config('concerns')['version'],
                           'readiness_prompt': 'prompts/readiness-evidence.txt', 'readiness_prompt_sha256': self._source_prompt_hash,
                           'grounding_prompt': 'prompts/readiness-grounding.txt',
                           'grounding_prompt_sha256': getattr(self, '_grounding_prompt_hash', None),
                           'mode_policy': config('assessment_modes'), 'inference': deepcopy(self.inference)}}

    @staticmethod
    def _prompt_hash():
        from hashlib import sha256
        from .settings import ROOT
        return sha256((ROOT/'prompts/readiness-evidence.txt').read_bytes()).hexdigest()

    def json(self): return json.dumps(self.export(), ensure_ascii=False, indent=2)
    def jsonl(self): return json.dumps(self.export(), ensure_ascii=False, separators=(',', ':')) + '\n'
