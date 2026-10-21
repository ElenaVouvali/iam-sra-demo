"""A thin operation/presentation adapter over the existing conversation engine."""
from copy import deepcopy
from pathlib import Path, PurePath
from hashlib import sha256
import json
import os
import re
import subprocess
import threading
from .errors import APIError
from .schemas import API_VERSION, SessionView
from ..assessment import AssessmentError
from ..conversation_session import ConversationSession
from ..privacy import NOTICE, PrivacyError, detector, require_clean, require_safe_data, screened_export
from ..settings import config, ROOT

CLAIM_FIELDS = ('evidence_id', 'event_id', 'dimension', 'kind', 'interpretation',
                'span_quote', 'subject', 'temporality', 'domain', 'information_context',
                'independent_prior_knowledge', 'external_verification', 'status',
                'confirmation_status', 'topic_ids', 'outcome_relation', 'evidence_basis')


def fields(value, names):
    return {key: deepcopy(value[key]) for key in names if key in value}


def source(value):
    value = value or {}
    result = fields(value, ('document', 'document_title', 'locator', 'location', 'sha256', 'source_status'))
    for name in ('document', 'document_title'):
        if name in result:
            result[name] = PurePath(result[name]).name
    return result


def question(value):
    if not value:
        return None
    return fields(value, ('id', 'question_text', 'format', 'dimension', 'stage',
                          'elicitation_context', 'information_context', 'topic_ids'))


def scenario(value):
    if not value:
        return None
    return {**fields(value, ('id', 'title', 'text', 'unknowns', 'version', 'city','scenario_bank_version',
                            'source_status','source_verification','source_refs','illustrative_assumptions')),
            'source': source(value.get('source')), 'illustrative': True}


def information(value):
    content = value.get('content') or {}
    passages = {row['id']: row for row in content.get('passages', []) if 'id' in row}
    result = fields(value, ('id', 'kind', 'acknowledged', 'text', 'version', 'sequence',
                            'source_ids', 'displayed_at', 'acknowledged_at'))
    result['content'] = {**fields(content, ('status', 'label', 'notice', 'corpus_version')),
                         'excerpts': [{**fields(row, ('quotation', 'passage_id')),
                                       'source': source(row.get('source') or passages.get(row.get('passage_id'), {}).get('source')
                                                        or passages.get(row.get('passage_id'), {}))}
                                      for row in content.get('excerpts', [])]}
    return result


def estimate(value):
    if not value:
        return None
    result = fields(value, ('crl', 'explanation', 'uncertainty', 'status', 'validation_status',
                            'evidence_ids', 'approved_by', 'numerical_srl', 'assessment_scope_version'))
    result['source'] = source(value.get('source'))
    result['criteria'] = [{**fields(row, ('level', 'status', 'reason', 'evidence_ids')),
                           'supporting_evidence': [fields(c, CLAIM_FIELDS) for c in row.get('supporting_evidence', [])]}
                          for row in value.get('criteria', [])]
    return result


class ControllerAdapter:
    def __init__(self, engine_factory=None, clients_factory=None, readiness=None):
        self.engine_factory = engine_factory or ConversationSession
        self.clients_factory = clients_factory
        self.readiness_override = readiness
        self.fixture = engine_factory is not None
        self._collection = None
        self._source_signature = None
        self._corpus_lock = threading.Lock()

    def _signature(self, collection):
        from ..conversation_corpus import corpus_path
        paths = [corpus_path(),ROOT/'src/iam_sra/scenario_expansion.py',ROOT/'references/source-register.json',
                 *sorted((ROOT/'configs').glob('*.json')),
                 ROOT/'src/iam_sra/conversation_sources.py',
                 *(ROOT/row['path'] for row in collection['sources'])]
        return tuple(sha256(path.read_bytes()).hexdigest() for path in paths)

    def readiness(self):
        if self.readiness_override:
            return self.readiness_override()
        try:
            detector()
        except PrivacyError:
            raise APIError('privacy_unavailable', 503) from None
        from ..conversation_corpus import load_corpus
        try:
            with self._corpus_lock:
                if self._collection is None or self._signature(self._collection) != self._source_signature:
                    self._collection = None
                    collection = load_corpus()
                    self._source_signature = self._signature(collection)
                    self._collection = collection
        except PrivacyError as exc:
            raise APIError(exc.code, 503) from None
        except (ValueError, OSError, KeyError, AssessmentError, subprocess.SubprocessError):
            raise APIError('source_unavailable', 503) from None
        return {'privacy': 'ready', 'corpus': 'ready'}

    def create(self):
        self.readiness()
        try:
            return self.engine_factory() if self.fixture else ConversationSession(collection=self._collection)
        except PrivacyError as exc:
            raise APIError(exc.code, 503) from None
        except (ValueError, OSError, KeyError):
            raise APIError('source_unavailable', 503) from None

    def onboarding(self):
        baseline = config('baseline')
        return {name: deepcopy(baseline[name]) for name in ('perspectives', 'stakeholders', 'cities', 'familiarity')}

    def allowed(self, engine):
        result = ['reset']
        state = engine.state
        if state in {'general_welcome', 'general_context'}:
            return result + ['set_context'] + (['start_assessment'] if engine.indicator_view().get('available') else [])
        result += ['back', 'edit_context'] if not getattr(engine,'assessment_route',False) else []
        if any(e['active'] and e['confirmed'] for p in (engine.general, engine.scenario) if p for e in p.events):
            result.append('edit_answer')
        if state.endswith('_interview'):
            result += ['answer', 'finish']
        if state in {'general_review', 'scenario_review'}:
            result += ['confirm_answer', 'correct_interpretation']
        if state == 'general_baseline_review':
            result.append('confirm_general')
        if state == 'offer':
            result += ['select_scenario', 'accept_scenario', 'decline_scenario']
        if state in {'scenario_baseline_review', 'final_review'}:
            result.append('confirm_final')
        if engine.stage == 'scenario' and not engine.pending:
            exposures = engine.information_exposures
            if sum(e['kind'] == 'explanation' for e in exposures) < engine.instrument['information_budget']:
                result.append('ask_information')
            if any(not e['acknowledged'] for e in exposures):
                result.append('acknowledge')
            active = [e for e in engine.scenario.events if e['active']]
            if (any(e['kind'] == 'explanation' for e in exposures)
                    and not any(e['question']['id'] == 'scenario_reflection' for e in active)
                    and len(active) < engine.scenario.maximum_questions
                    and any(q['question_id'] == 'scenario_reflection' and q['stage'] == 'scenario'
                            and q['variant_id'] == ('organisation' if engine.respondent['perspective'] == 'organisation' else 'personal')
                            for q in engine.collection['questions'])):
                result.append('start_reflection')
        if state == 'final' and engine.respondent['perspective'] == 'personal' and os.getenv('IAM_DEVELOPER') == '1' and not getattr(engine,'assessment_route',False) and not (engine.indicators and engine.indicators.current):
            result.append('provisional_estimate')
        if state == 'final':
            view = engine.indicator_view()
            if view.get('available'):
                row = view['current']
                if not row or row['state'] != 'interpretation':
                    result.append('select_indicators')
                if row:
                    result += ['indicator_next','complete_assessment','indicator_information']
                    if row['state'] != 'interpretation': result += ['indicator_scope','indicator_case']
                    if row['state'] != 'interpretation' and view.get('reusable_answers'): result.append('indicator_link')
                    if row['state'] == 'collecting': result += ['indicator_answer', 'indicator_finish']
                    if row['state'] == 'interpretation': result += ['indicator_confirm', 'indicator_correct', 'indicator_add_information']
                    if row['state'] == 'ready' and row['tool'] is None: result += ['indicator_suggest','indicator_finish']
                    if row['state'] in {'ready', 'review', 'complete'}: result.append('indicator_review')
                    if row['state'] != 'interpretation': result.append('indicator_edit')
        return result

    def prepare(self, action, data):
        """Screen BEFORE retention, retry hashing, controller mutation or queueing."""
        cleaned = deepcopy(data)
        changed = False
        for key in {'start_assessment': ('use_case','area','organisation_or_unit','responsibilities','technical_object','object_version','intended_environment','materials_or_service','use_case_purpose','origin_destination_types_or_unknown','significant_unknowns'),
                    'indicator_scope': ('organisation_or_unit','responsibilities','technical_object','object_version','intended_environment'),
                    'indicator_add_information': ('text',), 'set_context': ('place', 'function'), 'answer': ('text',),
                    'correct_interpretation': ('text',), 'ask_information': ('question',),
                    'select_indicators': ('use_case','area','organisation_or_unit','responsibilities','technical_object','object_version','intended_environment'), 'indicator_answer': ('text',),
                    'indicator_correct': ('text',), 'indicator_review': ('explanation',)}.get(action, ()):
            try:
                require_clean(data[key])
            except PrivacyError as exc:
                if exc.preview is None:
                    raise APIError(exc.code, 503 if exc.code == 'privacy_unavailable' else 422) from None
                cleaned[key] = exc.preview
                changed = True
        if action=='select_indicators':
            for key,text in data.get('use_case_fields',{}).items():
                try: require_clean(text)
                except PrivacyError as exc:
                    if exc.preview is None: raise APIError(exc.code,422) from None
                    cleaned['use_case_fields'][key]=exc.preview
                    changed=True
        if changed:
            try: require_safe_data(cleaned)
            except PrivacyError as exc: raise APIError(exc.code,422) from None
            text = cleaned.get('text', '')
            if '[private detail removed]' in text:
                words = re.findall(r'[\w]+', text.replace('[private detail removed]', '').casefold())
                if not words or set(words) <= set('my home address is at i live the'.split()):
                    raise APIError('privacy', 422)
        # Controlled-looking request strings must not smuggle credentials into
        # receipts or jobs before the controller validates their membership.
        try:
            require_safe_data(cleaned)
        except PrivacyError as exc:
            raise APIError(exc.code, 503 if exc.code == 'privacy_unavailable' else 422) from None
        return cleaned, changed

    def validate_action(self, engine, action, data):
        if action == 'start_assessment':
            baseline=engine.general.instrument
            if data['city'] not in baseline['cities'] or data['stakeholder_role'] not in baseline['stakeholders']:
                raise APIError('invalid_request')
            if data.get('scenario_id') and data['discussion_status']!='illustrative':
                raise APIError('invalid_request')
        elif action == 'set_context':
            options = engine.general.instrument
            if any(data[key] not in options[group] for key, group in
                   [('perspective', 'perspectives'), ('role', 'stakeholders'), ('city', 'cities')]):
                raise APIError('invalid_request')
        elif action == 'select_scenario':
            if data['scenario_id'] not in {row['id'] for row in engine.scenario_options()}:
                raise APIError('invalid_action', 409)
        elif action=='indicator_case':
            if data['scenario_id'] is not None and data['scenario_id'] not in {r['id'] for r in engine.indicator_view()['illustrative_options']}:
                raise APIError('invalid_action',409)
        elif action == 'acknowledge':
            if not any(row['id'] == data['exposure_id'] and not row['acknowledged'] for row in engine.information_exposures):
                raise APIError('invalid_action', 409)
        elif action == 'select_indicators':
            view = engine.indicator_view()
            known = {i['indicator_id'] for i in view.get('coverage', [])}
            if not view.get('available') or set(data['indicator_ids']) - known or len(set(data['indicator_ids'])) != len(data['indicator_ids']):
                raise APIError('invalid_action', 409)
        elif action == 'indicator_review':
            group = engine.indicators
            ids = {s['id'] for s in group.scale(group.current_id)} if group and group.current else set()
            if not group or data['revision'] != group.revision or (data.get('statement_id') is not None and data['statement_id'] not in ids):
                raise APIError('stale_action', 409)
        elif action == 'indicator_next':
            if data['indicator_id'] not in engine.indicators.selected:
                raise APIError('invalid_action', 409)
        elif action == 'edit_answer':
            phase = engine.general if data['stage'] == 'general' else engine.scenario
            if not phase or not any(row['id'] == data['event_id'] and row['active'] and row['confirmed'] for row in phase.events):
                raise APIError('invalid_action', 409)

    def clients(self, engine, deadline):
        if self.clients_factory:
            clients = self.clients_factory(engine)
        else:
            from ..baseline_client import BaselineClient
            from ..conversation_planner import PlannerClient
            from ..readiness_retrieval import ExplanationClient
            from ..readiness_score import WorkbookScoreClient
            from ..indicator_client import IndicatorClient
            clients = {'baseline': BaselineClient(), 'planner': PlannerClient(prompt=engine.planner_prompt),
                       'information': ExplanationClient(), 'score': WorkbookScoreClient(), 'indicator': IndicatorClient()}
        for client in clients.values():
            if client is not None:
                client.external_deadline = deadline
                if hasattr(client, 'bind_session'):
                    client.bind_session(engine.session_id, engine.edit_epoch)
        return clients

    def apply(self, engine, action, data, deadline):
        if not self.fixture:
            self.readiness()
            if engine.corpus_sha256 != sha256(json.dumps(self._collection, sort_keys=True, ensure_ascii=False).encode()).hexdigest():
                raise APIError('source_unavailable', 503)
        clients = self.clients(engine, deadline)
        returned = None
        try:
            if action == 'set_context':
                engine.set_context(**data)
            elif action == 'answer':
                engine.answer(data['text'], clients['baseline'], clients.get('planner'), data['control'])
            elif action == 'confirm_answer':
                engine.confirm_answer(clients.get('planner'))
            elif action == 'correct_interpretation':
                engine.correct_interpretation(data['text'], clients['baseline'])
            elif action == 'accept_scenario':
                engine.accept_scenario(clients.get('planner'))
            elif action == 'ask_information':
                engine.ask_information(data['question'], clients.get('information'))
            elif action == 'provisional_estimate':
                engine.provisional_estimate(clients['score'])
            elif action == 'indicator_answer':
                engine.indicator_answer(data['text'], clients['indicator'], data['control'])
            elif action == 'indicator_add_information':
                engine.indicator_add_information(data['text'], clients['indicator'])
            elif action == 'indicator_correct':
                engine.indicator_correct(data['text'], clients['indicator'])
            elif action == 'indicator_suggest':
                engine.indicator_suggest(clients['indicator'])
            elif action == 'indicator_edit':
                returned = engine.indicator_edit(**data)
            elif action == 'edit_answer':
                candidates = engine.general if data['stage'] == 'general' else engine.scenario
                if not candidates or not any(e['id'] == data['event_id'] and e['active'] and e['confirmed'] for e in candidates.events):
                    raise APIError('invalid_action', 409)
                returned = engine.edit_answer(**data)
            elif action == 'acknowledge':
                if not any(e['id'] == data['exposure_id'] and not e['acknowledged'] for e in engine.information_exposures):
                    raise APIError('invalid_action', 409)
                engine.acknowledge(**data)
            elif action == 'back':
                returned = engine.back()
            else:
                getattr(engine, action)(**data)
            return returned if isinstance(returned, str) else None
        finally:
            # No mutable client, raw response cache or request metrics survive a job.
            for client in clients.values():
                if client is not None:
                    for key in ('last_trace', '_request_cache', '_token_count_cache', 'last_settings', '_accepted_wire'):
                        if hasattr(client, key):
                            setattr(client, key, None if key == '_accepted_wire' else {} if 'cache' in key or key == 'last_settings' else [])

    def present(self, engine, session_id, version):
        pending = engine.pending
        q = question(engine.current_question)
        if q and q.get('format') == 'selection':
            q['options'] = deepcopy(engine.general.instrument['familiarity'])
        answers = []
        for stage, phase in [('general', engine.general), ('scenario', engine.scenario)]:
            if phase:
                answers.extend({'stage': stage, 'id': e['id'], 'question_text': e['question']['question_text'],
                                'text': e['text'], 'confirmed': e['confirmed']}
                               for e in phase.events if e['active'] and e['confirmed'])
        data = dict(id=session_id, version=version, state=engine.state, stage=engine.stage,
                    allowed_actions=self.allowed(engine), question=q,
                    pending=None if not pending else {
                        **fields(pending, ('id', 'text', 'interaction', 'interpretation_status')),
                        'question': question(pending.get('question')),
                        'interpretations': list(dict.fromkeys(c['interpretation'] for c in pending.get('claims', [])))},
                    respondent=deepcopy(engine.respondent), scenario=scenario(engine.card),
                    scenarios=[scenario(row) for row in engine.scenario_options()] if engine.stage == 'offer' else [],
                    information=[information(row) for row in engine.information_exposures], answers=answers,
                    summary=engine.respondent_summary(),
                    evidence=[fields(row, CLAIM_FIELDS) for row in engine.profile()['claims']],
                    qualitative_assessment=engine.qualitative_assessment(),
                    results={'crl': None, 'trl': None, 'orl': None, 'srl': None,
                             'provisional_citizen_estimate': estimate(engine._provisional)},
                    privacy_notice=NOTICE, indicator_assessment=engine.indicator_view())
        value = SessionView(**data).model_dump()
        return screened_export(value, engine)

    def export(self, engine):
        # Screen the engine's authoritative export first, then project its assessment
        # evidence. No operational diagnostics, paths or prompts enter the download.
        raw = engine.export()
        omitted = {'inference', 'selection_decisions', 'planning_actions', 'planner_metrics',
                   'model_provenance', 'prompt_hashes', 'prompts', 'prompt', 'last_settings',
                   'diagnostics', 'trace', 'settings', 'base_url', 'endpoint', 'local_path',
                   'path', 'file_sha256', 'instrument', 'handoff', 'anchor_review'}

        def project(value):
            if isinstance(value, dict):
                return {key: project(item) for key, item in value.items() if key not in omitted}
            if isinstance(value, list):
                return [project(item) for item in value]
            return deepcopy(value)

        keys = ('assessment_mode', 'privacy_contract', 'session_id', 'state', 'respondent_context',
                'scenario_decision', 'baseline', 'scenario', 'confirmed_baseline_history',
                'initial_confirmed_profile', 'final_profile', 'confirmed_final_snapshots',
                'changes', 'proposal_views', 'topic_memory_version', 'topic_memory',
                'qualitative_assessment', 'respondent_summary', 'objective_registry_version', 'indicator_assessment',
                'information_exposures', 'pre_information_snapshots', 'unresolved_attempt',
                'failure_history', 'superseded_scenarios', 'stop_reason', 'numerical_crl',
                'numerical_srl', 'numerical_orl', 'numerical_trl', 'numerical_reason')
        result = project(fields(raw, keys))
        result.update(schema_version='1.0.0', export_profile='browser_evidence', api_version=API_VERSION,
                      engine_schema_version=raw['schema_version'],
                      selected_scenario=scenario(raw.get('selected_scenario')),
                      suggested_scenario=scenario(raw.get('suggested_scenario')),
                      provisional_citizen_estimate=estimate(raw.get('provisional_citizen_estimate')),
                      corpus_provenance={'version': engine.collection['version'],
                                         'sources': [source(row) for row in engine.collection['sources']]},
                      provenance={**fields(engine.provenance, ('code_commit', 'working_tree_dirty', 'code_snapshot_sha256')),
                                  'file_sha256': {'api_snapshot': sha256(
                          b''.join(p.name.encode() + b'\0' + p.read_bytes()
                                   for p in sorted(Path(__file__).parent.glob('*.py')))).hexdigest()}})
        return screened_export(result, engine)
