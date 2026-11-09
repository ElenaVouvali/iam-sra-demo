"""Conversational evidence admission composed into the existing session/controller.

Original screened messages, not unreviewed model interpretations, are evidence.
Navigation uses bounded context; reporting never claims to have read omitted text.
"""
from copy import deepcopy
from datetime import datetime, timezone
import os
import random
import re
import time
import httpx
from .assessment import AssessmentError
from .privacy import require_safe_data
from .chat_policy import POLICY, SCHEMA, WELCOME, objectives, rubric, load_rubrics


def direct_intent(text):
    value = text.strip().lower().rstrip('.!')
    # Anchored commands prevent false withdrawal from quotations and negation.
    if re.fullmatch(r"(?:please )?(?:withdraw|withdraw my data|delete my conversation|delete this conversation)", value): return 'withdraw'
    if re.fullmatch(r"(?:i(?:'d| would) like to (?:stop|finish)|can we stop|i (?:do not|don't) want to continue)(?: now)?", value): return 'stop'
    if re.fullmatch(r"(?:please )?(?:pause|take a break|i need a break|i would like a break)", value): return 'pause'
    if re.fullmatch(r"(?:please )?(?:stop|finish|end|withdraw|finish for now|stop the interview|end the conversation|i want to stop|i would like to stop|i'd like to stop)(?: now| please)?", value): return 'stop'
    if re.fullmatch(r"(?:please )?(?:skip|skip this|skip this question|next question|prefer not to answer)", value): return 'skip'
    if re.fullmatch(r"(?:please )?(?:simplify|say that more simply|use simpler words|explain the question|i don.t understand the question)", value): return 'simplify'
    if re.fullmatch(r"(?:please )?(?:change topic|change subject|talk about something else)", value): return 'topic'
    if re.fullmatch(r"(?:please )?(?:go back|back|previous question)", value): return 'back'
    if re.fullmatch(r"(?:please )?(?:show (?:me )?(?:the )?(?:readiness )?scale|explain (?:the )?methodology|can i see (?:the )?(?:readiness )?scale|can you show (?:me )?(?:the )?scale|what does (?:crl|orl|trl|srl) mean)\??", value): return 'scale'
    if re.fullmatch(r"(?:(?:please|could you|can you) )?(?:retry|try again)(?: (?:the (?:last )?answer|to (?:process|continue|complete) (?:the next step|this step)))?(?: because .*)?", value): return 'retry'
    if re.fullmatch(r"(?:please )?(?:show (?:me )?an example|give (?:me )?an example|show an illustrative example)", value): return 'example'
    if re.fullmatch(r"(?:please )?(?:show two ways of asking that|show two wordings)", value): return 'comparison'
    if re.fullmatch(r"(?:please )?(?:shorter conversation|keep it short)", value): return 'short'
    if re.fullmatch(r"(?:please )?(?:more detail|extended conversation)", value): return 'extended'
    return None


def explicit_profile(text):
    """Recognise a plainly selected perspective; never infer it from occupation."""
    value = text.strip().casefold()
    choices = {
        'citizen': r'\b(?:personal (?:view|views|perspective)|my own view|my own views|answer(?:ing)? as a citizen|as a resident|citizen perspective)\b',
        'organisational': r'\b(?:our organisation responsibilities|our organization responsibilities|on behalf of (?:an )?organisation|on behalf of (?:an )?organization|representing (?:an )?organisation|representing (?:an )?organization|organisation(?:al)? perspective|organization perspective|our team responsibilities|team responsibilities)\b',
        'technical': r'\b(?:technology subsystem|technical system|technical perspective|technology perspective|technology expert|technical object|technology component)\b',
    }
    matches = [profile for profile, pattern in choices.items() if re.search(pattern, value)]
    if len(matches) == 1:
        return matches[0]
    # A bare response to the explicit opening choice is an unambiguous selection.
    bare = {'citizen':'citizen', 'personal':'citizen', 'organisation':'organisational',
            'organization':'organisational', 'organisational':'organisational',
            'organizational':'organisational', 'technology':'technical',
            'technical':'technical', 'technology expert':'technical'}
    if value.rstrip('.!?') in bare:
        return bare[value.rstrip('.!?')]
    return None


def withheld_area(text):
    return bool(re.search(r'\b(?:prefer not|withhold|keep (?:it|this) general|do not know|don.t know|unknown|not sure|not known)\b', text, re.I))


def explicit_capacity_choice(profile, quote):
    """Reject ambiguous role descriptions; this never infers capacity from a job."""
    patterns = {'citizen':r'personal|citizen|resident|myself|own views?|my views?',
                'organisational':r'organi[sz]ation|on behalf|representing|team|institution|unit.*responsibil',
                'technical':r'technical|technology|system|component|subsystem'}
    matches = [key for key,pattern in patterns.items() if re.search(pattern,quote,re.I)]
    if profile not in matches:return False
    return len(matches)==1 or bool(re.search(r'prefer|choos|today|personal views|own views|on behalf|answer.*as',quote,re.I))


class ChatSession:
    def __init__(self, bank, depth='short', synthetic=False, assisted=False, corpus=None):
        self.source_scales, self.source_register = load_rubrics()
        self.bank = deepcopy(bank)
        self.depth = depth
        self.synthetic = synthetic
        self.assisted = assisted
        self.corpus = deepcopy(corpus)
        self.withdrawn = False
        self.profile = None
        self.context = {'city': None, 'city_status': 'not_established', 'organisation_or_unit': '', 'responsibilities': '',
                        'technical_object': '', 'object_version': '', 'intended_environment': '',
                        'scope_status': 'not_established', 'language': 'en'}
        self.stage = 'conversation'
        self.objective = 'perspective'
        self.covered = {}
        self.messages = []
        self.annotations = []
        self.priorities = []
        self.exposures = []
        self.preferences = []
        self.pending_comparison = None
        self.pending_explanation = False
        self.pending_correction = None
        self.visits = {}
        self.revision = 0
        self.calls = 0
        self.metrics = []
        self.failures = []
        self.routing_events = []
        self.decision_traces = []
        self.concerns = []
        self._last_decision = {}
        self.failed_turn_id = None
        self.suggestion = None
        self.initial_results = []
        self.participant_review = None
        self.indicator_results = []
        self.stop_reason = None
        self.started = time.monotonic()
        self._assistant(WELCOME, 'perspective')

    def _rubric(self):
        value = rubric(self.bank, self.profile, self.depth)
        key = 'citizen_'+self.depth if self.profile=='citizen' else self.profile
        if value['source'] != self.source_register['sources'][key] or value['rubric_version'] != self.source_register['version']:
            raise ValueError('Interview sources changed during this conversation; start a new scoped session.')
        return value

    @property
    def limits(self):
        return {'turns': 30 if self.depth == 'short' else 50,
                'calls': int(os.getenv('IAM_CHAT_MAX_CALLS', '64')),
                'processing_seconds': int(os.getenv('IAM_CHAT_PROCESSING_SECONDS', '600'))}

    def _assistant(self, text, objective=None, act='question'):
        require_safe_data({'text': text})
        self.messages.append({'id': f'm{len(self.messages)+1}', 'role': 'assistant', 'text': text,
                              'objective_id': objective, 'act': act, 'revision': self.revision})

    def _user(self, text, evidence=True, act='answer'):
        require_safe_data({'text': text})
        row = {'id': f'm{len(self.messages)+1}', 'role': 'respondent', 'text': text,
               'objective_id': self.objective, 'act': act, 'active': True,
               'profile': self.profile, 'scope_revision': 1, 'revision': self.revision,
               'evidence_status': 'respondent_provided' if evidence else 'interaction_only',
               'interpretation_status': 'interpretation_unreviewed',
               'provenance': 'facilitator_entered_respondent_words' if self.assisted else 'respondent_entered',
               'information_exposure_ids': [e['id'] for e in self.exposures]}
        self.messages.append(row)
        return row

    def active_evidence(self):
        return [m for m in self.messages if m['role'] == 'respondent' and m['active']
                and m['evidence_status'] == 'respondent_provided']

    def _invalidate(self, reason):
        if self.suggestion or self.indicator_results:
            self.initial_results.append({'suggestion': deepcopy(self.suggestion),
                'indicator_results': deepcopy(self.indicator_results), 'reason': reason, 'revision': self.revision})
        self.suggestion = None
        self.indicator_results = []
        if self.participant_review: self.participant_review['status'] = 'pending_after_new_evidence'

    def _all_objectives(self):
        return objectives(self.profile, self.depth)

    def _fallback_question(self, answer=''):
        """A concise authored recovery probe; never the normal routing path."""
        if re.search(r'\b(?:bird|wildlife|nest|animal|habitat)\w*\b', answer, re.I):
            return 'What effects on wildlife would you most want decision-makers to understand?'
        if re.search(r'\b(?:noise|loud|sound|sleep)\w*\b', answer, re.I):
            return 'When or where might noise matter most to people, and what would you want considered?'
        if re.search(r'\b(?:privacy|camera|record)\w*\b', answer, re.I):
            return 'What would you want to know about information collection and privacy safeguards?'
        if self.profile == 'organisational':
            return 'What is already established within your unit, and what is still only proposed?'
        if self.profile == 'technical':
            return 'What has been tested on this specific component or system, and what remains untested?'
        return 'What would you most want people planning a possible service to understand about this concern?'

    def _fallback_source(self, answer=''):
        objective_id = ('understanding' if re.search(r'\b(?:bird|wildlife|nest|animal|habitat|noise|loud|sound|sleep|privacy|camera)\w*\b',answer,re.I)
                        else 'open_priorities')
        row = next((item for item in self._all_objectives() if item['id']==objective_id), None)
        return deepcopy((row or {}).get('source'))

    def _request(self, answer, comparison=False):
        # Preserve every original outside the prompt. Include bounded ORIGINALS;
        # omitted IDs are explicit and never claimed as considered at judgment.
        originals = self.active_evidence()
        current_id = originals[-1]['id'] if originals and originals[-1]['text']==answer else None
        active_ids = {m['id'] for m in originals}
        priority = next((p for p in reversed(self.priorities) if p['evidence_id'] in active_ids and p['evidence_id']!=current_id), None)
        priority_ids = {priority['evidence_id']} if priority else set()
        remaining_chars = max(0,4500-len(answer)-(len(priority['text']) if priority else 0))
        selected, size = [], 0
        for message in reversed(originals):
            if message['id']==current_id or message['id'] in priority_ids: continue
            if size + len(message['text']) > remaining_chars: continue
            selected.append({k: message[k] for k in ('id', 'text', 'objective_id')})
            size += len(message['text'])
        ids = {m['id'] for m in selected} | priority_ids
        if current_id: ids.add(current_id)
        previous_questions = [m['text'] for m in self.messages if m['role']=='assistant' and m.get('act') in {'question','authored_fallback'}]
        from .chat_retrieval import retrieve_chat_context
        query = (' '.join([answer[:900]] + [m['text'][:300] for m in originals[-3:]]))[:1800]
        retrieval = retrieve_chat_context(self.corpus, self.profile, self.depth, query)
        self._last_decision['retrieval'] = retrieval
        return {'answer': answer, 'profile': self.profile, 'context': self.context,
                'current_topic': self._current_topic(), 'depth': self.depth,
                'retrieved_context': retrieval,
                'indicator_ids': [r['id'] for r in self.bank['indicators']],
                'original_context': list(reversed(selected)), 'priority_context': deepcopy(priority), 'current_answer_id': current_id, 'omitted_context_ids': [m['id'] for m in self.active_evidence() if m['id'] not in ids],
                'previous_questions': previous_questions,
                'comparison': comparison}

    def _current_topic(self):
        if self.concerns:
            return self.concerns[-1]['topic']
        active = self.active_evidence()
        return active[-1].get('topic', 'opening') if active else 'opening'

    def _apply_context_facts(self, result, answer, evidence_id):
        """Accept optional scope annotations only when their quote is exact."""
        accepted = []
        for fact in result.get('context_facts', []):
            value, field = fact['quote'].strip(), fact['field']
            if not value or value not in answer:
                continue
            if field == 'city':
                self.context['city'] = value
                self.context['city_status'] = 'respondent_provided_unverified'
            else:
                self.context[field] = value
                self.context['scope_status'] = 'respondent_described'
            accepted.append({'field': field, 'evidence_id': evidence_id,
                             'status': 'respondent_provided_unverified'})
        if accepted:
            row = next((m for m in reversed(self.messages) if m['role']=='respondent' and m['id']==evidence_id), None)
            if row:
                row['context_fields'] = [item['field'] for item in accepted]
        return accepted

    def _record_plain_context(self, answer, row):
        """Record an obvious answer to a context question without model extraction.

        This is intentionally narrow: the previous assistant turn must have
        asked for a broad city/area, and the reply must be a short, non-address
        value. A locality never implies that a service operates there.
        """
        previous = next((m for m in reversed(self.messages[:-1]) if m['role'] == 'assistant'), None)
        if not previous or self.context.get('city'):
            return []
        asked_area = bool(re.search(r'\b(?:which|what|your)\s+(?:city|town|area|region|locality)\b',
                                    previous['text'], re.I))
        if not asked_area:
            return []
        if withheld_area(answer):
            self.context['city'] = None
            self.context['city_status'] = 'withheld_or_uncertain'
            row.setdefault('context_fields', []).append('city')
            return [{'field':'city','evidence_id':row['id'],'status':'withheld_or_uncertain'}]
        value = answer.strip()
        if (len(value) <= 80 and not re.search(r'\d|@|\b(?:street|road|avenue|postcode|zip)\b', value, re.I)
                and not re.search(r'\b(?:i live at|my address|located at)\b', value, re.I)):
            self.context['city'] = value
            self.context['city_status'] = 'respondent_provided_unverified'
            row.setdefault('context_fields', []).append('city')
            return [{'field':'city','evidence_id':row['id'],'status':'respondent_provided_unverified'}]
        return []

    def _update_concern_ledger(self, row, result):
        if (row.get('context_fields') and result.get('topic') in {'local context','respondent context'}
                and set(row['context_fields']) <= {'city','organisation_or_unit','responsibilities','technical_object','object_version','intended_environment'}):
            return 'context_only'
        topic = (result.get('topic') or '').strip()
        try:
            require_safe_data({'topic': topic})
        except Exception:
            topic = ''
        if not topic:
            topic = 'Respondent-raised concern or question'
        known = {i['id'] for i in self.bank['indicators']}
        indicator_ids = [value for value in result.get('indicator_ids', []) if value in known]
        intent = (result.get('respondent_intent') or '').casefold()
        kind = ('information_request' if re.search(r'\b(?:what|how|explain|know|information)\b', intent)
                else 'opinion_only' if self.objective == 'opinion' or re.search(r'\b(?:support|oppose|like|dislike)\b', intent)
                else 'existing_indicator_topic' if indicator_ids else 'emerging_topic')
        existing = next((item for item in self.concerns if item['topic'].casefold() == topic.casefold()), None)
        if existing:
            if row['id'] not in existing['evidence_ids']:
                existing['evidence_ids'].append(row['id'])
            existing['explored'] = True
            existing['last_turn_id'] = row['id']
            existing['indicator_ids'] = list(dict.fromkeys(existing['indicator_ids'] + indicator_ids))
            if indicator_ids:
                existing['mapping_status'] = 'candidate_unreviewed'
        else:
            self.concerns.append({'topic': topic, 'kind': kind, 'evidence_ids': [row['id']],
                'explored': True, 'priority': len(self.concerns) < 3 or self.objective in {'open_priorities','priorities'},
                'clarification_needed': result.get('act') == 'clarify',
                'indicator_ids': indicator_ids,
                'mapping_status': 'candidate_unreviewed' if indicator_ids else 'not_mapped',
                'interpretation_status': 'unreviewed', 'last_turn_id': row['id']})
        row['topic'] = topic
        return kind

    def _trace(self, before_id, before_state, error=None):
        new_messages = self.messages[before_id:]
        respondents = [m for m in new_messages if m['role'] == 'respondent']
        assistants = [m for m in new_messages if m['role'] == 'assistant']
        decision = deepcopy(self._last_decision)
        accepted_action = decision.get('accepted_action') or (assistants[-1].get('act') if assistants else 'recorded_without_reply')
        postcondition = decision.get('postcondition') or {
            'respondent_messages_added':len(respondents),
            'assistant_messages_added':len(assistants),
            'state_transition_applied':before_state != {'stage':self.stage,'objective':self.objective,'profile':self.profile,'revision':self.revision}}
        # Verify effects against authoritative in-memory state rather than
        # trusting the model's action label or its concise justification.
        postcondition_checks = {
            'respondent_evidence_ids_exist': all(
                evidence_id in {m['id'] for m in self.active_evidence()}
                for evidence_id in [m['id'] for m in respondents if m.get('evidence_status') == 'respondent_provided']),
            'accepted_question_ids_exist': all(
                item['message_id'] in {m['id'] for m in self.messages if m['role'] == 'assistant'}
                for item in [{'message_id':m['id']} for m in assistants if m.get('act') in {'question','authored_fallback','wrap_offer'}]),
            'profile_remains_controller_selected': self.profile == before_state['profile'] or before_state['profile'] is None,
            'recorded_exposure_ids_exist': (
                not postcondition.get('exposure_recorded') or
                postcondition.get('exposure_id') in {exposure['id'] for exposure in self.exposures}),
            'controller_state_matches_observation': postcondition.get('state_transition_applied', True) ==
                (before_state != {'stage':self.stage,'objective':self.objective,'profile':self.profile,'revision':self.revision})
                if 'state_transition_applied' in postcondition else True,
        }
        if decision.get('assessment') is not None:
            postcondition_checks['assessment_matches_controller_result'] = (
                decision['assessment'].get('selected_anchor_id') == (self.suggestion or {}).get('anchor_id') and
                decision['assessment'].get('status') == (self.suggestion or {}).get('status'))
        retrieval = decision.get('retrieval', {'status':'not_used','guidance':[],'passages':[]})
        retrieval_trace = {'status':retrieval.get('status'), 'guidance':[], 'passages':[],
            'model_referenced_source_ids':deepcopy(decision.get('source_ids',[])),
            'controller_rendered_source_id':postcondition.get('participant_text_from_source')}
        for group in ('guidance','passages'):
            for item in retrieval.get(group, []):
                retrieval_trace[group].append({key:deepcopy(item.get(key)) for key in
                    ('id','source','source_type','source_status','source_verification','permitted_use') if key in item})
        self.decision_traces.append({'turn_id': len(self.decision_traces) + 1,
            'profile': self.profile, 'current_topic': self._current_topic(),
            'respondent_evidence_ids': [m['id'] for m in respondents if m.get('evidence_status') == 'respondent_provided'],
            'accepted_actions': [{'act': m.get('act'), 'message_id': m['id']} for m in assistants],
            'accepted_questions': [{'message_id':m['id'],'text':m['text'],'act':m.get('act')}
                for m in assistants if m.get('act') in {'question','authored_fallback','wrap_offer'}],
            'model_proposal': {key: decision[key] for key in ('proposed_action','act','topic','respondent_intent','question_goal','justification','considered_alternatives','evidence_ids','source_ids','uncertainty') if key in decision},
            'action_validation': {'validated_action':decision.get('validated_action'),
                'decision':'rejected_or_fallback' if decision.get('fallback_used') or decision.get('rejected_action_reasons') else 'accepted',
                'rejection_reasons':deepcopy(decision.get('rejected_action_reasons',[]))},
            'retrieval': retrieval_trace,
            'fallback_source':decision.get('fallback_source'),
            'assessment': deepcopy(decision.get('assessment')),
            'validated_context_facts': decision.get('validated_context_facts', []),
            'concerns': deepcopy(self.concerns),
            'indicator_mappings': [{'evidence_id':row['evidence_id'],'indicator_ids':row['indicator_ids'],
                'status':'candidate_unreviewed' if row['evidence_id'] in {m['id'] for m in self.active_evidence()} else 'superseded'}
                for row in self.annotations],
            'validation': decision.get('validation', {'privacy':'passed','evidence_integrity':'original_text_authoritative'}),
            'rejected_optional_annotations': decision.get('rejected_optional_annotations', []),
            'controller_execution': {'accepted_action':accepted_action,
                'postcondition':postcondition, 'observed_postcondition_checks':postcondition_checks,
                'all_observed_postconditions_passed':all(postcondition_checks.values()),
                'state_before':before_state,'state_after':{'stage':self.stage,'objective':self.objective,'profile':self.profile,'revision':self.revision}},
            'execution': {'model_calls': decision.get('model_calls',0),
                'latency_seconds': decision.get('latency_seconds',0),
                'fallback_used': decision.get('fallback_used',False), 'error':error or decision.get('error')}})

    def _generate(self, client, request):
        if self.calls + 4 > self.limits['calls']:
            raise AssessmentError('Chat call limit.', code='budget')
        started = time.monotonic()
        try:
            result = client.turn(request)
            # Validate injected fixture clients through the identical public contract.
            from .chat_client import validate_reply
            return validate_reply(result, request)
        finally:
            metrics = getattr(client, 'last_metrics', {})
            observed = metrics.get('generation_calls')
            calls = observed if observed is not None else 1
            elapsed = round(time.monotonic()-started, 3)
            self.calls += calls
            self._last_decision['model_calls'] = self._last_decision.get('model_calls',0) + calls
            self._last_decision['latency_seconds'] = round(self._last_decision.get('latency_seconds',0)+elapsed,3)
            self.metrics.append({'generation_calls': observed, 'wall_seconds': elapsed,
                                 'context_ids': [m['id'] for m in request['original_context']], 'current_answer_id':request['current_answer_id'],
                                 'priority_evidence_id':(request['priority_context'] or {}).get('evidence_id'),
                                 'omitted_context_ids': request['omitted_context_ids']})

    def _onboarding_answer(self, text):
        """The sole closed opening choice: profile selection, never profession."""
        if self.objective == 'perspective':
            row = self._user(text, True, 'profile_selection' if explicit_profile(text) else 'profile_clarification')
            profile = explicit_profile(text)
            if not profile:
                self.visits['perspective'] = self.visits.get('perspective', 0) + 1
                if self.visits['perspective'] >= 2:
                    self.finish('capacity_not_established_partial')
                else:
                    self._assistant('Which perspective would you like to use: your personal views, an organisation’s responsibilities, or a technology you work with?', 'perspective')
                return True
            self.profile = profile
            row['profile'] = profile
            self.covered['perspective'] = [row['id']]
            self.visits['perspective'] = 1
            self.objective = 'open_conversation'
            self._assistant('Thanks. What comes to mind when you think about healthcare drone deliveries? You can keep the setting or system general, and it is fine to say you are unsure.', 'open_conversation')
            return True
        return False

    def _correction_target(self, text):
        cues = {
            'area': r'\b(?:city|area|locality)\b', 'perspective': r'\b(?:perspective|profile|role)\b',
            'scope': r'\b(?:object|system|subsystem|component|responsibilit|unit|organisation|organization)\b'
        }
        matched = [objective for objective, pattern in cues.items() if re.search(pattern, text, re.I)]
        rows = [m for m in self.active_evidence() if m['objective_id'] in matched
                or any(name in {'city' if objective == 'area' else objective for objective in matched}
                       for name in m.get('context_fields', []))]
        return rows[-1] if len(matched) == 1 and rows else None

    def _apply_correction(self, target, text):
        row = self._user(text, True, 'correction')
        row['objective_id'] = target['objective_id']
        for key, value in list(self.context.items()):
            if key not in {'city','organisation_or_unit','responsibilities','technical_object','object_version','intended_environment'}: continue
            if isinstance(value, str) and value and value in target['text']:
                self.context[key] = None if key == 'city' else ''
        if target['objective_id']=='area' or 'city' in target.get('context_fields',[]):
            self.context['city'] = None if withheld_area(text) else text
            self.context['city_status'] = 'withheld_or_uncertain' if withheld_area(text) else 'respondent_provided_unverified'
        target['active'] = False
        row['supersedes'] = target['id']
        for objective in list(self.covered):
            if target['id'] in self.covered[objective]: del self.covered[objective]
        self.pending_correction = None
        self._invalidate('Respondent corrected evidence')
        if target['objective_id'] in {'perspective','scope'}:
            row['evidence_status'] = 'scope_change_unresolved'
            self.stage = 'scope_change'
            self._assistant('This changes the assessed perspective or object. Download this record, then use New conversation so incompatible scopes remain separate.', act='scope_clarification')
        elif self.stage == 'summary':
            self._assistant('Your corrected words are in the summary. Say “no changes” when you are ready to continue.', act='summary')
        else:
            self.objective = 'open_conversation'
            self._assistant('Your correction is recorded. What else would you like to discuss?', self.objective, 'authored_fallback')

    def _summary(self):
        """Compact exact-passages overview; scoring always uses all originals."""
        originals = self.active_evidence()
        groups = {}
        for message in originals:
            if message['objective_id']=='perspective':
                key='perspective'
            elif 'city' in message.get('context_fields',[]) or message['objective_id']=='area':
                key='area'
            elif message.get('context_fields'):
                key='scope'
            elif message.get('act')=='opinion':
                key='opinion'
            else:
                key='topic:'+str(message.get('topic') or message['id'])
            if key!='opinion': groups[key]=message
            if re.search(r"not sure|don't know|do not know|unknown|uncertain|no opportunity",message['text'],re.I):
                groups['uncertainty']=message
        priority_ids = [row['evidence_id'] for row in self.priorities[:3]]
        selected={};size=0
        ordered = [groups[key] for key in ('perspective','area','scope') if key in groups]
        ordered += [next((m for m in originals if m['id']==eid),None) for eid in priority_ids]
        ordered += [groups[key] for key in groups if key.startswith('topic:') or key=='uncertainty']
        for message in ordered:
            if message and message['id'] not in selected and size+len(message['text'])<=3200:
                selected[message['id']]=message;size+=len(message['text'])
        return [{'evidence_id':m['id'],'quote':m['text'],'objective_id':m['objective_id'],'topic':m.get('topic')}
                for m in originals if m['id'] in selected]

    def finish(self, reason='respondent_finish'):
        self.pending_comparison = None
        self.stop_reason = reason
        self.stage = 'summary'
        self._assistant('Here is a copy of the points you shared, including uncertainties. Does this capture your situation, or is there something to correct before seeing the scale and provisional summary?', act='summary')

    def _indicator_report(self, client):
        """At most two scoped matches, never fifteen calls per turn or score averaging."""
        self.indicator_results = []
        if client is None or not self.profile: return
        from .indicator_client import validate_match
        scope = {**self.context, 'response_profile': self.profile, 'context': 'healthcare_drone_conversation',
                 'use_case': 'Healthcare drones in general'}
        if self.profile == 'technical' and not scope['technical_object']: return
        if self.profile == 'organisational' and not (scope['organisation_or_unit'] and scope['responsibilities']): return
        original = {m['id']: m for m in self.active_evidence()}
        candidates = list(dict.fromkeys(i for a in self.annotations if a['evidence_id'] in original for i in a['indicator_ids']))[:2]
        # Include ALL active scoped originals, including contradictory/correcting ones.
        # If the full evidence cannot fit, abstain rather than hide omitted context.
        for indicator_id in candidates:
            if self.calls + 4 > self.limits['calls']: break
            row = {'indicator_id': indicator_id, 'profile': self.profile, 'scope': deepcopy(scope),
                   'evidence_revision': self.revision, 'participant_reviewed': False,
                   'policy_version': POLICY, 'evidence_contract':'respondent_provided',
                   'bank_version':self.bank.get('bank_version'), 'source':deepcopy(self.bank['source']),
                   'review_status': 'unreviewed', 'generic_result_validation': False}
            if sum(len(m['text']) for m in original.values()) > 4800:
                row.update(status='insufficient_evidence', reason='Complete scoped evidence exceeds the bounded reporting request; nothing was silently omitted.')
                self.indicator_results.append(row); continue
            evidence = [{'evidence_id': m['id'], 'answer': m['text'], 'question': m['objective_id'],
                         'observations': [], 'active': True, 'evidence_status': 'respondent_provided',
                         'scope': scope} for m in original.values()]
            scale = [s for s in self.bank['statements'] if s['indicator_id']==indicator_id and s['profile']==self.profile]
            indicator = next(i for i in self.bank['indicators'] if i['id']==indicator_id)
            started = time.monotonic()
            try:
                value = client.match(indicator, scope, scale, evidence, evidence_contract='respondent_provided')
                value = validate_match(value, scale, evidence, scope, 'respondent_provided')
                value['statement']=deepcopy(next((s for s in scale if s['id']==value['selected_statement_id']),None))
                row.update(status='suggested' if value['selected_statement_id'] else 'abstained', tool=value)
            except (AssessmentError, httpx.HTTPError, ValueError) as exc:
                code = getattr(exc, 'code', 'model_failure')
                row.update(status='unavailable', reason=code)
                diagnostics = getattr(client, 'last_diagnostics', [])
                last = diagnostics[-1] if diagnostics else {}
                self.failures.append({'stage':'indicator_projection','category':'model_schema' if code=='schema' else 'evidence_integrity' if code=='evidence' else 'model_transport',
                    'code':code,'indicator_id':indicator_id,
                    'attempts':sum(1 for d in diagnostics if d.get('stage')=='indicator_match' and 'attempt' in d),
                    'generation_calls':getattr(client,'last_metrics',{}).get('generation_calls'),
                    'transport_attempts':sum(1 for d in diagnostics if 'transport_attempt' in d),
                    'validation_field':getattr(exc,'field',None) or last.get('validation_field'),
                    'completion_status':last.get('completion_status')})
                if last.get('validation_fields'):
                    self.failures[-1]['validation_errors'] = deepcopy(last['validation_fields'])
            finally:
                count = getattr(client, 'last_metrics', {}).get('generation_calls')
                elapsed=round(time.monotonic()-started,3)
                self.calls += count if count is not None else 1
                self._last_decision['model_calls']=self._last_decision.get('model_calls',0)+(count if count is not None else 1)
                self._last_decision['latency_seconds']=round(self._last_decision.get('latency_seconds',0)+elapsed,3)
                self.metrics.append({'generation_calls': count, 'wall_seconds': elapsed,
                                     'report_indicator_id': indicator_id, 'considered_evidence_ids': list(original)})
            self.indicator_results.append(row)

    def _report(self, indicator_client=None, score_client=None):
        self.stage = 'review'
        from .chat_score import validate_profile_match
        scale = self._rubric() if self.profile else None
        self.suggestion = {'status': 'abstained', 'level': None, 'anchor_id': None,
            'policy_version': POLICY, 'revision': self.revision, 'rubric_version': (scale or {}).get('rubric_version'),
            'explanation': 'There is not enough usable scoped evidence for an overall level.',
            'gaps': [], 'considered_evidence_ids': [], 'evidence_sufficiency': 'insufficient', 'external_verification': 'not_performed'}
        originals = [{'id': m['id'], 'text': m['text'], 'objective': m['objective_id'],
                      'information_exposure_ids': m['information_exposure_ids']} for m in self.active_evidence()]
        scope_ready = self.profile=='citizen' or (self.profile=='organisational' and self.context['organisation_or_unit'] and self.context['responsibilities']) or (self.profile=='technical' and self.context['technical_object'])
        if score_client and scale and scope_ready and originals and self.calls + 4 <= self.limits['calls']:
            if sum(len(m['text']) for m in originals) > 5000:
                self.suggestion['gaps'] = ['Complete original evidence exceeds this bounded judgment request. No evidence was silently omitted.']
            else:
                payload = {'profile': self.profile, 'scope': self.context, 'anchors': scale['anchors'],
                           'guidance': scale['guidance'], 'originals': originals, 'supplied_information': self.exposures}
                started = time.monotonic()
                try:
                    value = score_client.match_profile(payload)
                    value = validate_profile_match(value, payload)
                    anchor = next((a for a in scale['anchors'] if a['id']==value['selected_anchor_id']), None)
                    self.suggestion.update(status='suggested' if anchor else 'abstained',
                        level=anchor['level'] if anchor else None, anchor_id=anchor['id'] if anchor else None,
                        anchor=anchor, explanation=value['explanation'], boundary=value['boundary'],
                        citations=value['citations'], alternative_anchor_id=value['alternative_anchor_id'],
                        material_conflict=value['material_conflict'], evidence_incomplete=value['evidence_incomplete'],
                        considered_evidence_ids=[m['id'] for m in originals],
                        evidence_sufficiency='provisionally_sufficient' if anchor else 'insufficient')
                except (AssessmentError, httpx.HTTPError, ValueError) as exc:
                    code=getattr(exc,'code','model_failure')
                    self.suggestion.update(status='unavailable', explanation='A valid provisional profile judgment is unavailable. Your original words are retained.',
                                           gaps=[code])
                    diagnostics=getattr(score_client,'last_diagnostics',[])
                    last=diagnostics[-1] if diagnostics else {}
                    self.failures.append({'stage':'generic_profile_match','category':'model_schema' if code=='schema' else 'evidence_integrity' if code=='evidence' else 'model_transport',
                        'code':code,'attempts':sum(1 for d in diagnostics if d.get('stage')=='chat_profile_match' and 'attempt' in d),
                        'generation_calls':getattr(score_client,'last_metrics',{}).get('generation_calls'),
                        'transport_attempts':sum(1 for d in diagnostics if 'transport_attempt' in d),
                        'validation_field':getattr(exc,'field',None) or last.get('validation_field'),
                        'completion_status':last.get('completion_status')})
                    validation_errors = [
                        item for item in diagnostics
                        if item.get('stage') == 'chat_profile_match' and item.get('validation_fields')
                    ]
                    if validation_errors:
                        self.failures[-1]['validation_errors'] = [
                            {'attempt': item.get('attempt'), 'fields': deepcopy(item['validation_fields'])}
                            for item in validation_errors
                        ]
                finally:
                    count=getattr(score_client,'last_metrics',{}).get('generation_calls')
                    elapsed=round(time.monotonic()-started,3)
                    self.calls+=count if count is not None else 1
                    self._last_decision['model_calls']=self._last_decision.get('model_calls',0)+(count if count is not None else 1)
                    self._last_decision['latency_seconds']=round(self._last_decision.get('latency_seconds',0)+elapsed,3)
                    self.metrics.append({'generation_calls':count,'wall_seconds':elapsed,'stage':'generic_profile_match',
                                         'considered_evidence_ids':[m['id'] for m in originals]})
        self._indicator_report(indicator_client)
        considered_ids = [m['id'] for m in originals]
        citation_ids = list(dict.fromkeys(c['evidence_id'] for c in self.suggestion.get('citations', [])))
        self._last_decision['assessment'] = {
            'profile': self.profile,
            'scope': {key:{'present':bool(self.context.get(key)),'status':self.context.get('scope_status')}
                for key in ('organisation_or_unit','responsibilities','technical_object','object_version','intended_environment')},
            'scale_source':deepcopy((scale or {}).get('source')),
            'scale_version':(scale or {}).get('rubric_version'),
            'candidate_anchor_ids':[a['id'] for a in (scale or {}).get('anchors',[])],
            'candidate_scope':'all nine anchors were supplied to the bounded comparison request; model reasoning is not independently observable',
            'selected_anchor_id':self.suggestion.get('anchor_id'),
            'closest_alternative_anchor_id':self.suggestion.get('alternative_anchor_id'),
            'supporting_evidence_ids':citation_ids,
            'contradictory_evidence_ids':None,
            'contradiction_note':'The score response reports a conflict flag, not message-level contradiction attribution.',
            'material_conflict_flag':self.suggestion.get('material_conflict',False),
            'evidence_incomplete_flag':self.suggestion.get('evidence_incomplete',True),
            'missing_evidence':deepcopy(self.suggestion.get('gaps',[])),
            'considered_evidence_ids':considered_ids,'omitted_evidence_ids':[],
            'status':self.suggestion.get('status'),
            'validation':'exact_quote_and_active_evidence_checked' if self.suggestion.get('status')=='suggested' else 'abstained_or_unavailable',
            'uncertainty':self.suggestion.get('evidence_sufficiency')}
        self._assistant('The scale and provisional summary are shown below. How well do they describe your situation, or what is missing?', act='result_review')

    def show_case(self, text, card):
        self.revision += 1
        self._user(text,False,'example_request')
        if card is None:
            self._assistant('No applicable source-backed example is available. We can continue in general.',act='example_unavailable')
            return
        exposure={'id':f'x{len(self.exposures)+1}', 'kind':'illustrative_case',
            'source_id':card['id'], 'source':deepcopy(card.get('source',{})),
            'source_status':card.get('source_status','illustrative_source_record'),
            'source_verification':card.get('source_verification','not_independently_verified'),
            'unknowns':deepcopy(card.get('unknowns',[])), 'text':card['text'],
            'revision':self.revision,'prior_knowledge':False,'actual_activity':False}
        self.exposures.append(exposure)
        self._assistant('Illustrative example — '+exposure['source_status']+'; '+exposure['source_verification']+'. '+card['text']+
            ' Unknowns: '+'; '.join(exposure['unknowns'])+'. This example does not establish an operation in your city or your prior experience. What thoughts does it raise for you?', self.objective, 'supplied_example')

    def send(self, text, client, indicator_client=None, score_client=None):
        before_id = len(self.messages)
        before_state = {'stage':self.stage,'objective':self.objective,'profile':self.profile,'revision':self.revision}
        started = time.monotonic()
        self._last_decision = {}
        error = None
        try:
            return self._send(text, client, indicator_client, score_client)
        except Exception as exc:
            error = getattr(exc, 'code', 'controller_error')
            raise
        finally:
            self._last_decision.setdefault('latency_seconds', round(time.monotonic()-started, 3))
            self._trace(before_id, before_state, error)

    def _send(self, text, client, indicator_client=None, score_client=None):
        if self.stage == 'ended': raise ValueError('This conversation has ended.')
        self.revision += 1
        intent = direct_intent(text)
        retry_row = None
        if intent == 'retry':
            retry_row=next((m for m in self.active_evidence() if m['id']==self.failed_turn_id),None)
            self._user(text,False,'retry_request')
            if retry_row is None:
                self._assistant('There is no failed answer waiting to retry. You can continue or finish.',act='recovery')
                return
            text=retry_row['text']
        if intent == 'withdraw':
            bank,depth,synthetic,assisted,corpus = self.bank,self.depth,self.synthetic,self.assisted,self.corpus
            self.__init__(bank,depth,synthetic,assisted,corpus)
            self.messages = []
            self.withdrawn = True
            self.stage = 'ended'
            self.stop_reason = 'respondent_withdrawal'
            self._assistant('Your temporary conversation content has been cleared. Previously downloaded copies remain with whoever downloaded them.', act='withdrawal')
            return
        if intent == 'pause':
            self._user(text, False, 'pause')
            self.stage = 'paused'
            self._assistant('We can pause here. Progress remains temporary; download a copy if you need to leave. Say “continue” when you are ready.', act='pause')
            return
        if self.stage == 'scope_change' and intent not in {'stop','withdraw'}:
            self._user(text,False,'unresolved_scope')
            self._assistant('Please download this scoped conversation if you need it, then use New conversation for the new perspective or object.',act='scope_clarification')
            return
        if self.stage == 'paused':
            self._user(text, False, 'resume')
            self.stage = 'conversation'
            self._assistant('Welcome back. What would you like to continue discussing?', self.objective)
            return
        if intent == 'stop':
            self._user(text, False, 'stop')
            if self.stage in {'summary', 'review', 'review_addition'}:
                self.stage = 'ended'
                self._assistant('We can stop here. Download a copy if you would like to keep it.', act='end')
            else: self.finish()
            return
        if self.pending_comparison:
            match = re.match(r'^\s*(?:(?:i prefer|option|wording)\s+)?(?:the\s+)?(1|2|first|second|neither|no preference|either)\b(?:\s+(?:one|wording|option))?[.!,:;\s]*(.*)$', text, re.I | re.S)
            if not match:
                self._user(text, False, 'preference_clarification')
                self._assistant('You may choose 1, 2, neither, or no preference. You can also add a separate answer after your choice.', act='preference')
                return
            choice, rest = match.groups()
            choice={'first':'1','second':'2','either':'no preference'}.get(choice.lower(),choice.lower())
            comparison = self.pending_comparison
            comparison.update(choice=choice.lower(), response_revision=self.revision,
                response_id=self._user(match.group(1), False, 'preference')['id'], training_eligible=False)
            self.preferences.append(comparison)
            self.pending_comparison = None
            self._assistant('Thank you. That preference is feedback about wording only.', act='preference_acknowledgement')
            if not rest.strip(): return
            comparison['response_text'] = text
            if re.match(r'^(because|it (?:is|feels)|clearer|shorter|easier)\b',rest,re.I) and re.search(r'\balso[,: ]+',rest,re.I):
                parts=re.split(r'\balso[,: ]+',rest,maxsplit=1,flags=re.I)
                comparison['reason']=parts[0].strip()
                rest=parts[1].strip()
            if re.match(r'^(because|it (?:is|feels)|clearer|shorter|easier)\b',rest,re.I) and 'my answer:' not in rest.lower():
                comparison['reason'] = rest
                return
            if 'my answer:' in rest.lower():
                cut=rest.lower().index('my answer:')
                comparison['reason']=rest[:cut].strip()
                rest=rest[cut+len('my answer:'):].strip()
            text = rest
        if self.pending_explanation:
            explanation_kind = self.pending_explanation
            self._user(text, False, 'explanation_permission')
            self.pending_explanation = False
            if re.fullmatch(r'(yes|yes please|please explain|go ahead|ok|okay)[.! ]*', text, re.I):
                explanation = ('Some drones can create strong air movement near take-off and landing areas. Its strength and safe separation depend on the aircraft and conditions.' if explanation_kind=='air_movement' else 'A drone is an aircraft without a pilot on board. Some drones can carry items such as medicines or samples. Whether this is useful depends on the service and conditions; no local operation is assumed.')
                self._assistant(explanation, act='supplied_information')
                self.exposures.append({'id': f'x{len(self.exposures)+1}', 'text': explanation, 'revision': self.revision,
                    'origin': 'authored_neutral_explanation', 'prior_knowledge': False})
            if explanation_kind=='air_movement':
                self._assistant('What would you want to know before judging whether such a landing location was safe?', self.objective)
                return
            self._assistant('What benefits, concerns or questions come to mind for you?', 'open_priorities')
            self.covered['familiarity'] = []; self.covered['healthcare'] = []
            self.objective = 'open_priorities'
            return
        if intent in {'short', 'extended'}:
            self._user(text, False, 'depth_preference'); self.depth = intent
            wording = ('We can keep this brief and focus on what matters most to you. '
                       if intent == 'short' else
                       'We can explore the issues you choose in more depth. ')
            self._assistant(wording + 'What would you like to discuss next?', 'open_conversation')
            return
        if intent == 'scale':
            self._user(text, False, 'methodology_request')
            if not self.profile:
                self._assistant('There are different scales for personal views, an organisation, and a technology. Which perspective would you like to discuss?', 'perspective')
                return
            self.exposures.append({'id': f'x{len(self.exposures)+1}', 'kind': 'reference_scale', 'revision': self.revision, 'prior_knowledge': False})
            self._assistant('The summary considers the meaning of your answers, with opinion and actual activity kept distinct. The full scale from the supplied interview example is shown below. This is a provisional profile judgment, not an overall societal SRL. This exposure is recorded.', act='methodology')
            return
        if intent == 'topic':
            self._user(text, False, 'change_topic')
            self.objective = 'open_conversation'
            self._assistant('Of course. What would you prefer to talk about?', self.objective)
            return
        if intent == 'back':
            self._user(text, False, 'back')
            earlier = self.active_evidence()
            if earlier:
                self.pending_correction = earlier[-1]['id']
                self._assistant('What would you like to change about this earlier point: “' + earlier[-1]['text'] + '”?', act='correction')
            else: self._assistant('We are at the beginning. ' + WELCOME, 'perspective')
            return
        if self.pending_correction == 'clarify':
            target = self._correction_target(text)
            if target:
                self._apply_correction(target, text)
                return
            self._user(text, False, 'correction_clarification')
            attempts = self.visits.get('correction_clarification', 0) + 1
            self.visits['correction_clarification'] = attempts
            if attempts == 1:
                self._assistant('Which point should I change: your perspective, city or area, organisation responsibilities, or technical object? Please include what it should say.', act='correction')
            else:
                self.pending_correction = None
                if self.stage == 'summary':
                    self._assistant('I could not link that correction to an earlier point, so I have not changed the original answers. Say “no changes” to continue or use “go back” to edit a specific answer.', act='summary')
                else:
                    self._assistant('I could not link that correction to an earlier point, so the original answer remains. You can use “go back” to edit a specific answer or continue.', self.objective, 'correction')
            return
        if self.stage == 'summary' and not self.pending_correction:
            self._user(text, False, 'summary_review')
            if re.fullmatch(r'(yes|looks right|no changes|continue|show the result|show summary|okay|ok|that is right)[.! ]*', text, re.I):
                self._report(indicator_client, score_client)
                return
            self.pending_correction = 'clarify'
            self._assistant('Which earlier point should I correct, and what should it say? You can also say “no changes” to continue.', act='correction')
            return
        if self.stage == 'review':
            message = self._user(text, False, 'result_review')
            self.participant_review = {'text': text, 'response_id': message['id'], 'status': 'pending_human_review',
                'preferred_level': None, 'independent_validation': False}
            preferred = re.search(r'\b(?:prefer|level|CRL|ORL|TRL)\s*([1-9])\b', text, re.I)
            if preferred: self.participant_review['preferred_level'] = int(preferred[1])
            self._assistant('Your response is recorded separately from the tool result. What additional facts, if any, would you like a reviewer to consider? No follow-up service is available; download your feedback to keep it.', act='review_addition')
            self.stage = 'review_addition'
            return
        if self.stage == 'review_addition':
            row = self._user(text, True, 'additional_evidence')
            self._invalidate('Additional evidence after result')
            self.stage = 'review_addition'
            self._assistant('I recorded that as additional information, with review pending. The initial result is preserved; I will not automatically change it. You can add anything else or say stop.', act='review_recorded')
            return
        if self.pending_correction == 'clarify' and re.fullmatch(r'(no changes|continue)[.! ]*', text, re.I):
            self.pending_correction = None
            self._user(text, False, 'summary_review')
            self._report(indicator_client, score_client)
            return
        if self.pending_correction and self.pending_correction != 'clarify':
            target = next((m for m in self.active_evidence() if m['id'] == self.pending_correction), None)
            if target:
                self._apply_correction(target, text)
            else:
                self.pending_correction = None
                self._user(text, False, 'correction_clarification')
                self._assistant('I could not find that earlier answer. Your existing answers remain unchanged; use “go back” to select one.', act='correction')
            return
        if intent == 'simplify':
            self._user(text, False, 'simplification')
            request = self._request(text)
            request['simplification'] = True
            try:
                result = self._generate(client, request)
                if result.get('_quality_issues'):
                    self._assistant(self._fallback_question(text), self.objective, 'authored_fallback')
                else:
                    self._assistant(result['message'], self.objective)
            except (AssessmentError, httpx.HTTPError):
                self._last_decision['fallback_used'] = True
                self._assistant('I could not rephrase that just now. You can leave this question open, change topic or finish.', act='failure')
            return
        if intent == 'skip':
            self._user(text, False, 'skip')
            self._assistant('No problem; we can leave that open. What else would you like to discuss?', 'open_conversation')
            return
        if len(self.active_evidence()) >= self.limits['turns'] or sum(m['wall_seconds'] for m in self.metrics) >= self.limits['processing_seconds']:
            self._user(text, True)
            self.finish('operational_limit_partial')
            return
        if intent == 'comparison':
            self._user(text, False, 'comparison_request')
            request = self._request('', comparison=True)
            try: result = self._generate(client, request)
            except AssessmentError as exc:
                self.failures.append({'code': exc.code, 'revision': self.revision})
                self._assistant('Two wordings are unavailable right now. You can answer the current question or finish.', act='failure')
                return
            question = next((m['text'] for m in reversed(self.messages) if m['role']=='assistant' and m.get('act')=='question'),
                            'What would you like to explore about this topic?')
            variant_texts = result['variants'] if result['variants'] and not result.get('_quality_issues') else [question, 'What part of this topic matters most to you, and why?']
            variants = [{'response_id': f'v{self.revision}-{i}', 'text': t} for i, t in enumerate(variant_texts)]
            random.SystemRandom().shuffle(variants)
            self.pending_comparison = {'objective_id': self.objective, 'context_revision': self.revision,
                'variants': variants, 'display_order': [v['response_id'] for v in variants], 'semantic_review': 'pending', 'training_eligible': False}
            self._assistant('Which wording do you prefer, 1 or 2? You can also say neither or no preference.', act='preference')
            return
        if self._onboarding_answer(text):
            return
        row = retry_row or self._user(text)
        self._invalidate('New respondent evidence')
        self._last_decision['validated_context_facts'] = self._record_plain_context(text, row)
        request = self._request(text)
        try:
            result = self._generate(client, request)
        except (AssessmentError, OSError, httpx.HTTPError) as exc:
            code = getattr(exc, 'code', 'transport')
            diagnostics = getattr(client, 'last_diagnostics', []) if client is not None else []
            last = diagnostics[-1] if diagnostics else {}
            category = ('context_budget' if code == 'budget' else 'model_schema' if code == 'schema' else
                        'evidence_integrity' if code == 'evidence' else 'model_transport' if code in {'timeout','transport','service_busy','service_request'} else
                        'generated_output_privacy' if code in {'privacy','privacy_unavailable'} and last.get('privacy_boundary') == 'model_output' else
                        'response_view_export_privacy' if code in {'privacy','privacy_unavailable'} and last.get('privacy_boundary') == 'assessment_record' else
                        'controller_state' if code in {'state','stale','conflict'} else
                        'input_privacy' if code in {'privacy','privacy_unavailable'} else 'model_failure')
            failure = {'stage':'chat_turn','category':category,'code':code,'revision':self.revision,
                       'attempts':sum(1 for d in diagnostics if d.get('stage')=='chat_turn' and 'attempt' in d),
                       'generation_calls':getattr(client, 'last_metrics', {}).get('generation_calls'),
                       'transport_attempts':sum(1 for d in diagnostics if d.get('stage')=='chat_turn' and 'transport_attempt' in d),
                       'completion_status':last.get('completion_status'),
                       'validation_field':getattr(exc,'field',None) or last.get('validation_field'),
                       'wall_seconds':round(sum(d.get('latency_seconds',0) for d in diagnostics if d.get('stage')=='chat_turn'),3)}
            if last.get('privacy_boundary'):
                failure['privacy_boundary'] = last['privacy_boundary']
                failure['entity_types'] = last.get('entity_types', [])
                failure['field_paths'] = last.get('field_paths', [])
            self.failures.append(failure)
            self._last_decision.update(validation={'model_action':'rejected','reason':category,
                'original_evidence':'retained_once','controller_action':'authored_fallback'}, fallback_used=True,
                model_calls=self._last_decision.get('model_calls',failure['generation_calls'] or 0),
                latency_seconds=self._last_decision.get('latency_seconds',failure['wall_seconds']), error=category)
            if getattr(exc,'code',None)=='budget':
                self.finish('call_or_context_budget_partial')
                return
            self.failed_turn_id = None
            self.routing_events.append({'event':'authored_fallback','evidence_id':row['id'],'reason':category})
            self._last_decision['fallback_source'] = self._fallback_source(text)
            self._assistant('I kept your answer. ' + self._fallback_question(text), 'open_conversation', 'authored_fallback')
            self._last_decision['postcondition'] = {'evidence_retained_once': row['id'] in {m['id'] for m in self.active_evidence()},
                                                     'fallback_added': self.messages[-1]['act']=='authored_fallback'}
            return
        self.failed_turn_id = None
        unauthorized_scope_change = result['act'] == 'scope_change'
        if result['act'] == 'scope_change':
            self._last_decision['model_scope_change'] = 'rejected_model_cannot_change_scope'
        if self.objective in {'open_priorities','priorities'}:
            self.priorities.append({'evidence_id':row['id'],'text':text,'origin':'spontaneous' if self.objective=='open_priorities' else 'selected_after_open_question'})
        self._last_decision.update({key:deepcopy(result.get(key)) for key in
            ('source_ids','act','topic','respondent_intent','question_goal','justification','considered_alternatives','evidence_ids','uncertainty')})
        self._last_decision['proposed_action'] = result.get('_model_proposed_action', result['proposed_action'])
        self._last_decision['validated_action'] = result['proposed_action']
        self._last_decision.setdefault('validated_context_facts', [])
        self._last_decision['validated_context_facts'] += self._apply_context_facts(result, text, row['id'])
        kind = self._update_concern_ledger(row, result)
        if kind != 'context_only' and row.get('topic') and len(self.priorities) < 3 and not any(p['evidence_id']==row['id'] for p in self.priorities):
            self.priorities.append({'evidence_id':row['id'],'text':text,
                'origin':'spontaneous_topic_in_open_conversation','topic':row['topic']})
        self.annotations.append({'evidence_id': row['id'], 'indicator_ids': result['indicator_ids'],
            'dialogue_act':result['act'], 'covered_objectives':[], 'quote': None,
            'status': 'interpretation_unreviewed',
            'elicitation': 'spontaneous' if self.objective == 'open_priorities' else 'prompted',
            'evidence_type':kind, 'revision': self.revision})
        warnings = result.get('_annotation_warnings', [])
        self._last_decision['rejected_optional_annotations'] = list(warnings)
        issues = result.get('_quality_issues', [])
        self._last_decision['rejected_action_reasons'] = list(issues) if issues else []
        if unauthorized_scope_change:
            issues.append('unauthorized_scope_change')
        self._last_decision['validation'] = {'privacy':'passed','question_quality':'rejected' if issues else 'passed',
            'evidence_ids':'rejected_optional_annotation' if 'evidence_ids' in warnings else 'validated',
            'indicator_ids':'rejected_optional_annotation' if 'indicator_ids' in warnings else 'candidate_only',
            'context_facts':'rejected_optional_annotation' if 'context_facts' in warnings else 'exact_quote_checked',
            'source_ids':'rejected_optional_annotation' if 'source_ids' in warnings else 'membership_checked',
            'retrieved_sources':'read_only_context'}
        if result['act'] == 'correction':
            self.pending_correction = 'clarify'
            self._assistant('Which earlier point would you like to correct? You can name the topic, such as your city, and tell me what should replace it.', act='correction')
            return
        if result['act'] == 'explanation_offer':
            self.pending_explanation = 'air_movement' if re.search(r'downwash|outwash|air movement',text,re.I) else 'drone'
            subject = 'air movement near landing areas' if self.pending_explanation=='air_movement' else 'what a drone is'
            self._assistant('Would you like a brief explanation of '+subject+'? You can say no and continue.', act='explanation_permission')
            return
        if result['proposed_action'] == 'provide_information':
            source_id = next((sid for sid in result['source_ids']
                              if any(row['id']==sid for row in request['retrieved_context']['passages'])), None)
            passage = next((row for row in request['retrieved_context']['passages'] if row['id']==source_id), None)
            if passage:
                source = passage.get('source', {})
                text_out = (f"From {source.get('document','the reviewed project sources')} ({source.get('locator','source location')}): "
                            f"{passage.get('text','')} This passage is source context, not evidence about a service operating in your area.")
                require_safe_data({'text': text_out})
                exposure = {'id':f'x{len(self.exposures)+1}','kind':'retrieved_source_information',
                    'source_id':source_id,'source':deepcopy(source),'text':text_out,'revision':self.revision,
                    'prior_knowledge':False,'actual_activity':False,'permitted_use':'participant_information'}
                self.exposures.append(exposure)
                self._assistant(text_out, 'retrieved_information', 'supplied_information')
                self._last_decision['validation']['information_action'] = 'accepted_source_text_rendered_by_controller'
                self._assistant('What would you like to understand better about this information?', 'open_conversation', 'question')
                self._last_decision['accepted_action'] = 'provide_information'
                self._last_decision['postcondition'] = {'exposure_recorded': self.exposures[-1]['id']==exposure['id'],
                    'exposure_id': exposure['id'],
                    'source_membership_checked': True,'participant_text_from_source': source_id}
                return
            self._last_decision['validation']['information_action'] = 'rejected_no_valid_passage'
        if result['proposed_action'] == 'offer_comparison' and len(result['variants']) == 2:
            variants = [{'response_id':f'v{self.revision}-{i}','text':text_value}
                        for i,text_value in enumerate(result['variants'])]
            random.SystemRandom().shuffle(variants)
            self.pending_comparison = {'topic':result.get('topic') or self._current_topic(),
                'context_revision':self.revision,'variants':variants,
                'display_order':[v['response_id'] for v in variants],
                'semantic_review':'pending','training_eligible':False}
            self._assistant('Would you like to compare these two ways of asking? Which wording do you prefer, 1 or 2? You can also say neither.', act='preference')
            self._last_decision['accepted_action'] = 'offer_comparison'
            return
        self.objective = 'open_conversation'
        if warnings:
            self.routing_events.append({'event':'optional_annotation_rejected','fields':warnings,'evidence_id':row['id']})
        if issues:
            self.routing_events.append({'event':'question_fallback','issues':issues,'evidence_id':row['id']})
        if result['proposed_action']=='propose_conclusion' and len(self.active_evidence()) < 3:
            issues = list(issues) + ['conclusion_below_minimum_evidence_turns']
            self._last_decision['validation']['conclusion_action'] = 'rejected_insufficient_conversation_evidence'
        if issues:
            message, action = self._fallback_question(text), 'authored_fallback'
            self._last_decision['fallback_used'] = True
            self._last_decision['fallback_source'] = self._fallback_source(text)
        elif (result['proposed_action'] == 'propose_conclusion' or result['act'] == 'finish') and len(self.active_evidence()) >= 3:
            self._assistant(result['message'], self.objective, 'wrap_offer')
            self.finish('model_proposed_wrap_pending_respondent_review')
            action = 'wrap_offer'
            self._last_decision['accepted_action'] = 'propose_conclusion_pending_respondent_review'
        else:
            message, action = result['message'], 'question'
        if action != 'wrap_offer':
            self._assistant(message, self.objective, action)
        if 'accepted_action' not in self._last_decision:
            self._last_decision['accepted_action'] = ('authored_fallback' if action=='authored_fallback'
                else 'record_concern' if result['proposed_action']=='record_concern' else 'ask_question')
        self._last_decision['postcondition'] = {'respondent_evidence_retained': row['id'] in {m['id'] for m in self.active_evidence()},
            'assistant_action': self.messages[-1].get('act'), 'profile_unchanged': self.profile in {'citizen','organisational','technical'},
            'source_retrieval_read_only': True}

    def view(self):
        participant_messages = [{key:message[key] for key in ('id','role','text','act') if key in message}
                                for message in self.messages]
        return {'mode': SCHEMA, 'stage': self.stage, 'depth': self.depth, 'profile': self.profile,
                'messages': deepcopy(participant_messages), 'pending_comparison': deepcopy(self.pending_comparison),
                'summary': self._summary() if self.stage != 'conversation' else [],
                'scale': self._rubric() if self.profile and (self.stage in {'review','review_addition','ended'} or any(e.get('kind')=='reference_scale' for e in self.exposures)) else None,
                'suggestion': deepcopy(self.suggestion), 'participant_review': deepcopy(self.participant_review),
                'initial_suggestion': deepcopy(self.initial_results[0]['suggestion']) if self.initial_results and self.participant_review else None,
                'assisted': self.assisted,
                'completion': {'conversation': self.stage == 'ended',
                               'evidence_sufficiency': (self.suggestion or {}).get('evidence_sufficiency', 'pending_after_new_evidence' if self.initial_results else 'not_judged'),
                               'participant_review': 'provided' if self.participant_review else 'not_provided',
                               'review': (self.participant_review or {}).get('status', 'not_reviewed')}}

    def export(self):
        objective_coverage = []
        for objective in self._all_objectives():
            evidence_ids = list(self.covered.get(objective['id'], []))
            status = 'respondent_provided' if evidence_ids else ('not_selected' if objective['id'] in self.covered else 'not_explored')
            objective_coverage.append({'objective_id': objective['id'], 'status': status, 'evidence_ids': evidence_ids})
        return {**self.view(), 'messages':deepcopy(self.messages), 'schema_version': SCHEMA, 'policy_version': POLICY,
                'classification': 'synthetic' if self.synthetic else 'unlabelled_not_verified',
                'objective_coverage':objective_coverage,'routing_events':deepcopy(self.routing_events),
                'training_eligible': False, 'context': deepcopy(self.context),
                'evidence_revision': self.revision, 'annotations': deepcopy(self.annotations), 'priorities':deepcopy(self.priorities),
                'objectives': self._all_objectives(), 'information_exposures': deepcopy(self.exposures),
                'response_preferences': deepcopy(self.preferences), 'initial_results': deepcopy(self.initial_results),
                'indicator_projection': {'participant_reviewed': False, 'results': deepcopy(self.indicator_results),
                    'coverage': [{'indicator_id': i['id'], 'status': next((r['status'] for r in self.indicator_results if r['indicator_id']==i['id']), 'explored_unmatched' if any(i['id'] in a['indicator_ids'] and a['evidence_id'] in {m['id'] for m in self.active_evidence()} for a in self.annotations) else 'not_explored'),
                        'evidence_ids': [a['evidence_id'] for a in self.annotations if i['id'] in a['indicator_ids'] and a['evidence_id'] in {m['id'] for m in self.active_evidence()}]} for i in self.bank['indicators']]},
                'concern_ledger': deepcopy(self.concerns),
                'stop_reason': self.stop_reason, 'failures': deepcopy(self.failures), 'observable_metrics': deepcopy(self.metrics),
                'limits': self.limits, 'overall_srl': None, 'retention': 'temporary_memory_download_required',
                'source_versions': {'interview_version': self.source_register['version'], 'interview_sources':self.source_register['sources'],
                                    'workbook_source':self.bank['source'], 'bank_version':self.bank.get('bank_version')}}
