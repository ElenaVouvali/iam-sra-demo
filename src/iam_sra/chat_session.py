"""Conversational evidence admission composed into the existing session/controller.

Original screened messages, not unreviewed model interpretations, are evidence.
Navigation uses bounded context; reporting never claims to have read omitted text.
"""
from copy import deepcopy
from datetime import datetime, timezone
import os
import logging
import re
import time
import httpx
from .assessment import AssessmentError
from .privacy import require_safe_data
from .settings import config
from .chat_policy import (POLICY, SCHEMA, INTRODUCTION, PERSPECTIVE, ACKNOWLEDGEMENTS,
                         CITIZEN_DURATION, EASA_BASICS, EDUCATIONAL_OPTIONS, letter_options, citizen_depth_choice, educational_choice,
                         objectives, rubric, load_rubrics)
from .fn_interview import FNInterview, specification, flow_key, literal_answer

_log = logging.getLogger(__name__)


def direct_intent(text):
    value = text.strip().lower().rstrip('.!')
    # Anchored commands prevent false withdrawal from quotations and negation.
    if re.fullmatch(r"(?:please )?(?:withdraw|withdraw my data|delete my conversation|delete this conversation)", value): return 'withdraw'
    if re.fullmatch(r"(?:i(?:'d| would) like to (?:stop|finish)|can we stop|i (?:do not|don't) want to continue)(?: now)?", value): return 'stop'
    if re.fullmatch(r"(?:please )?(?:pause|take a break|i need a break|i would like a break)", value): return 'pause'
    if re.fullmatch(r"(?:please )?(?:stop|finish|end|withdraw|finish for now|stop the interview|end the conversation|i want to stop|i would like to stop|i'd like to stop)(?: now| please)?", value): return 'stop'
    if re.fullmatch(r"(?:please )?(?:finish|end|stop) (?:this|this interview|this conversation|the interview|the conversation)", value): return 'stop'
    if re.fullmatch(r"(?:please )?(?:skip|skip this|skip this question|next question|prefer not to answer)", value): return 'skip'
    if re.fullmatch(r"(?:please )?(?:nothing[, ]+next question|move on|let.s move on|i (?:just|already) answered(?: (?:that|this))?|you (?:already asked|keep asking)(?: (?:that|this))?|i (?:did not|didn.t) say (?:that|something like that))", value): return 'advance'
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
    labels = {'a':'citizen','a. citizen':'citizen','b':'organisational','b. organisation or institution':'organisational','c':'technical','c. technology expert or researcher':'technical'}
    if value.rstrip('.!?') in labels: return labels[value.rstrip('.!?')]
    choices = {
        'citizen': r'\b(?:citizen|personal (?:view|views|perspective)|my own view|my own views|my own perspective|for myself|answer(?:ing)? as a citizen|as a resident|citizen perspective)\b',
        'organisational': r'\b(?:organisation or institution|organization or institution|our organisation responsibilities|our organization responsibilities|(?:on behalf of|representing|speaking for|answering for) (?:an? |my |our )?(?:organisation|organization|institution|municipality|team)|representing (?:an )?organisation|representing (?:an )?organization|organisation(?:al)? perspective|organization perspective|our team responsibilities|team responsibilities)\b',
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
        self.model_provenance = deepcopy(config('model'))
        from .model_spec import thinking_enabled,context_tokens,reasoning_tokens
        self.inference_configuration={'enable_thinking':thinking_enabled(),'context_tokens':context_tokens(),
            'reasoning_token_allowance':reasoning_tokens(),'reasoning_retention':'discarded',
            'reasoning_parser':'deepseek_r1' if thinking_enabled() else None}
        from .adaptive_interview import enabled as adaptive_enabled
        self.inference_configuration['fn_adaptive_mode']=adaptive_enabled()
        self.inference_configuration['fn_adaptive_policy']='natural-conversation-prototype-0.1' if adaptive_enabled() else None
        self.depth = depth
        self.depth_selection = None
        self.depth_history = []
        self.synthetic = synthetic
        self.assisted = assisted
        self.corpus = deepcopy(corpus)
        self.withdrawn = False
        self.profile = None
        self.context = {'city': None, 'city_status': 'not_established', 'organisation_or_unit': '', 'responsibilities': '',
                        'technical_object': '', 'object_version': '', 'intended_environment': '',
                        'scope_status': 'not_established', 'technical_role': '', 'expertise': '', 'language': 'en'}
        self.stage = 'conversation'
        self.objective = 'perspective'
        self.covered = {}
        self.fn = FNInterview()
        self.partial = False
        self.review_step = None
        self._paused_stage = None
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
        self.adaptive_wordings = 0
        self.adaptive_probes = 0
        self.information_needs_handled = []
        self._last_decision = {}
        self.failed_turn_id = None
        self.suggestion = None
        self.initial_results = []
        self.participant_review = None
        self.indicator_results = []
        self.stop_reason = None
        self.started = time.monotonic()
        self._assistant(INTRODUCTION,act='introduction')
        self._assistant(PERSPECTIVE,'perspective')

    def _rubric(self):
        value = rubric(self.bank, self.profile, self.depth)
        key = 'citizen_'+self.depth if self.profile=='citizen' else self.profile
        if value['source'] != self.source_register['sources'][key] or value['rubric_version'] != self.source_register['version']:
            raise ValueError('Interview sources changed during this conversation; start a new scoped session.')
        return value

    @property
    def limits(self):
        return {'turns': int(os.getenv('IAM_CHAT_MAX_TURNS', '96')),
                'calls': int(os.getenv('IAM_CHAT_MAX_CALLS', '64')),
                'processing_seconds': int(os.getenv('IAM_CHAT_PROCESSING_SECONDS', '600'))}

    def _assistant(self, text, objective=None, act='question'):
        require_safe_data({'text': text})
        self.messages.append({'id': f'm{len(self.messages)+1}', 'role': 'assistant', 'text': text,
                              'objective_id': objective, 'act': act, 'revision': self.revision})
        if self.profile and act in {'scale_disclosure','methodology'}:
            self.messages[-1]['scale']=deepcopy(self._rubric())

    def _user(self, text, evidence=True, act='answer'):
        require_safe_data({'text': text})
        row = {'id': f'm{len(self.messages)+1}', 'role': 'respondent', 'text': text,
               'objective_id': self.objective, 'act': act, 'active': True,
               'profile': self.profile, 'scope_revision': 1, 'revision': self.revision,
               'evidence_status': 'respondent_provided' if evidence else 'interaction_only',
               'interpretation_status': 'interpretation_unreviewed',
               'provenance': 'facilitator_entered_respondent_words' if self.assisted else 'respondent_entered',
               'information_exposure_ids': [e['id'] for e in self.exposures]}
        previous=next((m for m in reversed(self.messages) if m['role']=='assistant'),None)
        if previous:row['in_reply_to']=previous['id']
        self.messages.append(row)
        return row

    def active_evidence(self):
        return [m for m in self.messages if m['role'] == 'respondent' and m['active']
                and m['evidence_status'] == 'respondent_provided']

    def _invalidate(self, reason):
        if self.suggestion or self.indicator_results:
            self.initial_results.append({'suggestion': deepcopy(self.suggestion),
                'indicator_results': deepcopy(self.indicator_results), 'reason': reason,
                'revision': (self.suggestion or {}).get('revision',self.revision), 'invalidated_at_revision':self.revision})
        self.suggestion = None
        self.indicator_results = []
        if self.participant_review: self.participant_review['status'] = 'pending_after_new_evidence'

    def _all_objectives(self):
        return objectives(self.profile, self.depth)

    def _fallback_question(self, answer=''):
        node = self.fn.current(self.profile, self.depth, self.objective)
        if node:
            return 'Could you clarify your answer to this question: '+node['canonical_question']
        return 'Which point would you like to clarify before we finish?'

    def _fallback_source(self, answer=''):
        stage = self.fn.stage_for(self.profile, self.depth, self.objective)
        return {**deepcopy(self._rubric()['source']), 'locator':(stage or {}).get('source_locator'),
                'specification_version':self.fn.version} if self.profile else None

    def _discussion_progress(self):
        remaining = self.fn.next(self.profile, self.depth, self.concerns)
        return {'may_propose_conclusion': self.profile is not None and remaining is None,
                'remaining_evidence_goal': (remaining or {}).get('id'),
                'meaning':'Exploration and acknowledged uncertainty control completion; turn count is only an operational safeguard.'}

    def _request(self, answer, comparison=False):
        # Preserve every original outside the prompt. Include bounded ORIGINALS;
        # omitted IDs are explicit and never claimed as considered at judgment.
        originals = self.active_evidence()
        latest = self.messages[-1] if self.messages else {}
        if latest.get('act')=='retry_request':
            latest=next((m for m in originals if m['id']==self.failed_turn_id),latest)
        current_id = latest.get('id') if latest.get('role')=='respondent' and latest.get('text')==answer else None
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
        messages_by_id={m['id']:m for m in self.messages}
        exchanges=[]
        for row in originals:
            question=messages_by_id.get(row.get('in_reply_to'))
            if question and row['id']!=current_id:
                exchanges.append({'answer_id':row['id'],'answer':row['text'],'question':question['text']})
        current=next((row for row in self.messages if row['id']==current_id),None)
        last_question=messages_by_id.get((current or {}).get('in_reply_to'),{})
        if last_question.get('act')=='failure':
            last_question=next((m for m in reversed(self.messages) if m['role']=='assistant'
                and m.get('objective_id')==self.objective and m.get('act') in {'question','authored_fallback'}),{})
        from .chat_retrieval import retrieve_chat_context
        # Rank optional background using the actual screened answer. Concatenating
        # unrelated city/choice/evidence fields creates new prose that can be
        # misread as a person's name. Scope/memory remain structured below.
        query = answer
        retrieval = retrieve_chat_context(self.corpus, self.profile, self.depth, query)
        self._last_decision['retrieval'] = retrieval
        return {'answer': answer, 'profile': self.profile, 'context': self.context,
                'current_topic': self._current_topic(), 'depth': self.depth,
                'discussion_progress': self._discussion_progress(),
                'fn': self.fn.snapshot(self.profile,self.depth,self.objective,self.context,self.concerns),
                'retrieved_context': retrieval,
                'indicator_ids': [r['id'] for r in self.bank['indicators']],
                'original_context': list(reversed(selected)), 'priority_context': deepcopy(priority), 'current_answer_id': current_id, 'omitted_context_ids': [m['id'] for m in self.active_evidence() if m['id'] not in ids],
                'previous_questions': previous_questions, 'last_question':last_question.get('text'),
                'answered_questions':exchanges[-4:],
                'validation_context':[{'id':row['id'],'text':row['text']} for row in originals],
                'comparison': comparison}

    def _current_topic(self):
        active = self.active_evidence()
        if active and active[-1].get('topic'):return active[-1]['topic']
        mentioned=[c for c in self.concerns if c['evidence_ids']]
        return mentioned[-1]['topic'] if mentioned else 'opening'

    def _apply_context_facts(self, result, answer, evidence_id):
        """Accept optional scope annotations only when their quote is exact."""
        accepted = []
        for fact in result.get('context_facts', []):
            value, field = fact['quote'].strip(), fact['field']
            if not value or value not in answer:
                continue
            if field in {'technical_object','object_version','responsibilities','organisation_or_unit'} and self.context.get(field) and value != self.context[field]:
                self._last_decision.setdefault('rejected_scope_annotations', []).append(field)
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
        postcondition['profile_unchanged'] = self.profile == before_state['profile'] or before_state['profile'] is None
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
            'closing_policy':self._discussion_progress(),
            'fn_stage':decision.get('fn_stage'), 'fn_coverage':decision.get('fn_coverage',[]),
            'depth_change':deepcopy(decision.get('depth_change')),
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
                'prompt_context_selection':decision.get('prompt_context_selection'),
                'fallback_used': decision.get('fallback_used',False), 'error':error or decision.get('error')}})

    def _generate(self, client, request):
        if self.calls + 4 > self.limits['calls']:
            raise AssessmentError('Chat call limit.', code='budget', field='call_limit')
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
            self._last_decision['prompt_context_selection'] = deepcopy(getattr(client,'last_context_selection',None))
            self._last_decision['model_calls'] = self._last_decision.get('model_calls',0) + calls
            self._last_decision['latency_seconds'] = round(self._last_decision.get('latency_seconds',0)+elapsed,3)
            self.metrics.append({'generation_calls': observed, 'wall_seconds': elapsed,
                                 'tokenize_calls':metrics.get('tokenize_calls'),
                                 'generated_tokens':metrics.get('generated_tokens'),
                                 'reasoning_characters':metrics.get('reasoning_characters',0),
                                 'reasoning_enabled':getattr(client,'last_settings',{}).get('enable_thinking',False),
                                 'generation_http_seconds':metrics.get('generation_http_seconds'),
                                 'model_wait_seconds':metrics.get('model_wait_seconds'),
                                 'diagnostics': [{key:deepcopy(entry[key]) for key in (
                                     'stage','phase','failure','http_status','prompt_tokens','max_output_tokens',
                                     'completion_status','validation_field','validation_fields','thinking_detected',
                                     'reasoning_enabled','reasoning_characters','field_paths','privacy_boundary','transport_attempt') if key in entry}
                                     for entry in getattr(client,'last_diagnostics',[])[-6:]],
                                 'context_ids': getattr(client,'last_context_selection',{}).get('context_ids',[m['id'] for m in request['original_context']]),
                                 'prompt_context_selection':deepcopy(getattr(client,'last_context_selection',None)), 'current_answer_id':request['current_answer_id'],
                                 'priority_evidence_id':(request['priority_context'] or {}).get('evidence_id'),
                                 'omitted_context_ids': getattr(client,'last_context_selection',{}).get('omitted_context_ids',request['omitted_context_ids'])})

    def _ask_fn(self, node, act='question'):
        self.objective = node['id']
        if node['id'] not in self.fn.asked: self.fn.asked.append(node['id'])
        text = node.get('preface', '')
        if text: text += '\n\n'
        text += node['canonical_question']
        if node['id']=='citizen_duration':text=CITIZEN_DURATION
        raised=self._raised_topics()
        if self.profile=='citizen' and node['id']=='open_more' and len(raised)==1:
            topic=raised[0]['topic']
            text=f"You've mentioned {topic} so far. Is there anything else about healthcare drone services that matters to you, or is {topic} the main issue you'd like us to focus on?"
        if node['id']=='priorities':text+='\nYou can choose just one issue if that is what matters to you.'
        educational=self.profile=='citizen' and node['id']=='drone_explanation'
        if educational:
            text+='\n\n'+EDUCATIONAL_OPTIONS+'\n\nYou can also decline the explanation and continue.'
        if node['response_type'] == 'suggested_topics' or (node['id']=='priorities' and self.profile=='technical') or node['response_type']=='display':
            topics=specification()['topic_suggestions'][flow_key(self.profile,self.depth)]
            text += '\n' + '\n'.join('• '+topic for topic in topics)
            self.exposures.append({'id':f'x{len(self.exposures)+1}','kind':'suggested_topics',
                'topics':deepcopy(topics),'revision':self.revision,'prior_knowledge':False,'actual_activity':False})
            for topic in topics:
                existing=next((c for c in self.concerns if c['topic'].casefold()==topic.casefold()),None)
                if existing:existing['suggested_by_interviewer']=True
                else:self.concerns.append({'topic':topic,'kind':'suggested_topic','evidence_ids':[],
                    'spontaneously_raised':False,'suggested_by_interviewer':True,'selected_priority':False,
                    'explored':False,'priority':False,'indicator_ids':[],'mapping_status':'not_mapped','interpretation_status':'not_respondent_evidence'})
        self._assistant(text, self.objective, act)
        self.messages[-1]['source'] = {**deepcopy(self._rubric()['source']),
            'locator':node['source_locator'], 'specification_version':self.fn.version,
            'wording':'authored adaptation' if 'authored' in node['source_locator'] else 'canonical question'}
        if educational:
            self.messages[-1]['resource']=deepcopy(EASA_BASICS)
            self.messages[-1]['source']['adaptation']='optional educational exit'
            if not any(e.get('kind')=='external_resource_offered' for e in self.exposures):
                self.exposures.append({'id':f'x{len(self.exposures)+1}','kind':'external_resource_offered',
                    'resource':deepcopy(EASA_BASICS),'engagement':'offered_not_verified',
                    'prior_knowledge':False,'actual_activity':False,'revision':self.revision})
        if node['id']=='citizen_duration' or (node['id']=='open_more' and len(raised)==1) or node['id']=='priorities':
            self.messages[-1]['source']['wording']='authored adaptation of FN question'

    def _adapt_next_fn_question(self, client, earlier_answer):
        """Present a source-mapped, context-aware next question when available.

        Failure is only a presentation fallback; the canonical FN question stays.
        Neither scope nor evidence coverage nor the next objective can change.
        """
        from .adaptive_interview import enabled, max_wordings, adaptive_goal
        if not enabled() or self.stage != 'conversation' or not earlier_answer:
            return
        node = self.fn.current(self.profile, self.depth, self.objective)
        if not node or not adaptive_goal(node):
            return
        if self.adaptive_wordings >= max_wordings(self.depth):
            return
        if not self.messages or self.messages[-1].get('role') != 'assistant' or self.messages[-1].get('act') != 'question':
            return
        original = self.messages[-1]['text']
        msg_id = self.messages[-1]['id']
        self.adaptive_wordings += 1
        try:
            request = self._request('', comparison=False)
            request['fn'] = self.fn.snapshot(self.profile,self.depth,self.objective,self.context,self.concerns)
            request['retrieved_context'] = {'guidance':[], 'passages':[], 'status':'not_required_for_wording'}
            request['answer'] = ''
            request['current_answer_id'] = None
            request['last_question'] = original
            request['recent_reply'] = earlier_answer[:1600]
            request['adaptive_wording'] = True
            request['previous_questions'] = request['previous_questions'][:-1]
            response=self._generate(client,request)
            candidate=response.get('message','').strip()
            # All generic wording/privacy/repetition validation is in ChatClient.
            if not candidate or response.get('_quality_issues') or candidate.count('?') != 1:
                raise ValueError('The generated question was not eligible.')
            # The same controller-owned question message and evidence goal remain.
            current=next((m for m in self.messages if m['id']==msg_id),None)
            if current is None or current['text'] != original or self.objective != node['id']:
                raise ValueError('The interview state changed during generation.')
            current['text']=candidate
            current['source']['canonical_question']=original
            current['source']['wording']='LLM_contextual_adaptation_pending_review'
            self.routing_events.append({'event':'adaptive_question','objective_id':node['id'],
                                        'message_id':msg_id,'canonical_retained':True})
        except (AssessmentError, ValueError, httpx.HTTPError) as exc:
            self.routing_events.append({'event':'adaptive_question_fallback','objective_id':node['id'],
                                        'reason':getattr(exc,'code','unavailable_or_ineligible')})

    def _respond_to_information_need(self, text):
        """Offer conservative general background without treating it as prior knowledge."""
        from .adaptive_interview import enabled, new_background
        if not enabled() or self.profile != 'citizen':
            return
        kinds, background=new_background(text,self.information_needs_handled)
        if not kinds:
            return
        # Authored contextual background. Neither local operations nor comparisons
        # are represented as established facts. Exposed after recording the answer.
        self.information_needs_handled.extend(kinds)
        self._assistant(background,act='supplied_information')
        self.exposures.append({'id':f'x{len(self.exposures)+1}',
            'kind':'authored_general_background','categories':kinds,'text':background,
            'source':{**deepcopy(self._rubric()['source']),
                'locator':'FN citizen concerns and questions; authored contextual background',
                'status':'author_adaptation_not_verbatim_FN'},
            'prior_knowledge':False,'actual_activity':False,'revision':self.revision})
        self.routing_events.append({'event':'responded_to_information_need',
                                    'categories':kinds,'evidence_scope':'general_only'})

    def _raised_topics(self):
        return [row for row in self.concerns if row.get('evidence_ids') and (
            row.get('spontaneously_raised') or row.get('selected_priority') or row.get('suggested_by_interviewer'))]

    def _select_depth(self, depth, provenance, evidence_id):
        previous=self.depth
        old_ids={q['id'] for q in self.fn.nodes('citizen',previous)}
        old_stage=self.fn.stage_for('citizen',previous,self.objective)
        self.depth=depth
        skipped=[]
        if previous!=depth and old_stage:
            for stage in self.fn.stages('citizen',depth):
                if stage['id']==old_stage['id']:break
                for q in stage['questions']:
                    if q['id'] not in old_ids and q['id'] not in self.fn.coverage:
                        self.fn.record(q['id'],None,'not_applicable');skipped.append(q['id'])
        selection={'depth':depth,'previous_depth':previous,'provenance':provenance,
                   'evidence_id':evidence_id,'source':deepcopy(self._rubric()['source']),
                   'revision':self.revision,'readiness_inferred':False,
                   'earlier_added_probes_not_reasked':skipped}
        self.depth_selection=selection
        self.depth_history.append(deepcopy(selection))
        self._last_decision['depth_change']=deepcopy(selection)

    def _duration_turn(self, text, skipped=False):
        row=self._user(text,False,'duration_selection')
        choice=('short','default_after_skip') if skipped else citizen_depth_choice(text,letters=True)
        if choice is None:
            self._assistant('Would you prefer around 20 minutes (A) or around 35 minutes (B)? If you are unsure, say so and we will use the shorter style.','citizen_duration')
            return
        self._select_depth(*choice,row['id'])
        self.fn.record('citizen_duration',row['id'],'explored')
        self._assistant('We will use the '+('shorter' if self.depth=='short' else 'more detailed')+' conversation. You can change the depth or stop later.',act='depth_acknowledgement')
        self._route_fn()

    def _educational_exit(self, text):
        self._user(text,False,'educational_exit')
        self.partial=True;self.stage='ended';self.stop_reason='ended_early_after_recognition'
        self.failed_turn_id=None;self.fn.next_action='educational_exit'
        self.suggestion=None;self.indicator_results=[]
        self.exposures.append({'id':f'x{len(self.exposures)+1}','kind':'external_resource_selected',
            'resource':deepcopy(EASA_BASICS),'engagement':'selected_not_verified',
            'prior_knowledge':False,'actual_activity':False,'revision':self.revision})
        self._assistant('Thank you for taking part. You can read the educational resource below and finish for now. '
            'This is a partial, unassessed interview; no readiness level has been assigned.',act='educational_exit')
        self.messages[-1]['resource']=deepcopy(EASA_BASICS)

    def _route_fn(self, indicator_client=None, score_client=None):
        self.failed_turn_id=None
        while True:
            node = self.fn.next(self.profile,self.depth,self.concerns)
            if not node:
                self.fn.next_action='conclude'
                self.stop_reason='fn_goals_explored_with_uncertainty' if self.fn.unresolved_gaps else 'fn_goals_explored'
                self.partial = any(r['status']=='unresolved' for r in self.fn.coverage.values())
                self._report(indicator_client,score_client)
                return
            self.fn.next_action='canonical'
            self._ask_fn(node)
            if node['response_type']!='display': return
            self.fn.record(node['id'],None,'provided')

    def _onboarding_answer(self, text, skipped=False):
        if self.objective != 'perspective': return False
        row=self._user(text,not skipped,'profile_selection')
        profile=explicit_profile(text)
        if profile is None:
            self._assistant('Please choose the perspective you want to use today: A. Citizen, B. Organisation or institution, or C. Technology expert or researcher. A profession alone does not select a perspective.','perspective')
            return True
        self.profile=profile;row['profile']=profile
        self.covered['perspective']=[row['id']]
        self._assistant(ACKNOWLEDGEMENTS[profile],act='profile_acknowledgement')
        self._route_fn()
        return True

    def _fn_topics(self, row, interpretation):
        stage=self.fn.stage_for(self.profile,self.depth,self.objective)
        spontaneous=self.objective in {'open_priorities','open_more','different_impacts','requirements_open'}
        explicit_earlier=any(e['goal']=='priorities' and re.search(r'priorit|matter most|focus on|choos|select|most important',e['quote'],re.I) for e in interpretation.get('coverage',[]))
        selecting=((self.objective=='priorities' or explicit_earlier) and self.fn.coverage.get('priorities',{}).get('status')=='explored'
                   and interpretation['answer_kind'] not in {'uncertain','declined'}
                   and len(interpretation.get('topics',[]))<=3)
        for item in interpretation.get('topics',[]):
            topic=item.get('matches_topic') or item['topic'].strip()
            old=next((c for c in self.concerns if c['topic'].casefold()==topic.casefold()),None)
            if old is None:
                old={'topic':topic,'kind':'emerging_topic','evidence_ids':[],
                     'spontaneously_raised':False,'suggested_by_interviewer':False,
                     'selected_priority':False,'explored':False,'priority':False,
                     'indicator_ids':[],'mapping_status':'not_mapped','interpretation_status':'unreviewed'}
                self.concerns.append(old)
            old['evidence_ids']=list(dict.fromkeys(old['evidence_ids']+[row['id']]))
            old['spontaneously_raised'] |= spontaneous
            old['suggested_by_interviewer'] |= self.objective=='suggested_topics'
            if selecting and len([c for c in self.concerns if c['selected_priority']])<3:
                old['selected_priority']=True;old['priority']=True
                if not any(p['topic']==topic for p in self.priorities):
                    self.priorities.append({'topic':topic,'evidence_id':row['id'],'text':row['text'],'origin':'respondent_selected'})
            if (stage or {}).get('id') not in {'context','recognition','awareness','topics'}:
                old['explored'] |= self.fn.coverage.get(self.objective,{}).get('status')=='explored'
            old['last_turn_id']=row['id']
            row['topic']=topic

    def _topic_disposition(self, row, interpretation):
        if self.profile!='citizen' or self.objective not in {'open_priorities','open_more','different_impacts','suggested_topics','priorities'}:return False
        intent=interpretation.get('topic_intent');quote=interpretation.get('topic_intent_quote','')
        if not intent or not quote or quote not in row['text']:return False
        if self.fn.coverage.get(self.objective,{}).get('status')!='explored':return False
        if intent in {'no_more','main_only'}:
            self.fn.facts['topic_scope_closed']=True
            self.fn.facts['topic_scope_evidence_id']=row['id']
            self.fn.record('open_more',row['id'],'explored')
        raised=self._raised_topics()
        if intent=='main_only' and len(raised)==1 and interpretation['answer_kind'] not in {'uncertain','declined'}:
            topic=raised[0];topic['selected_priority']=topic['priority']=True
            self.fn.record('priorities',row['id'],'explored')
            if not any(p['topic']==topic['topic'] for p in self.priorities):
                self.priorities.append({'topic':topic['topic'],'evidence_id':row['id'],'text':row['text'],'origin':'respondent_selected'})
        if intent=='suggestions':
            self.fn.facts['topic_scope_closed']=False
            self.fn.facts.pop('topic_scope_evidence_id',None)
            node=self.fn.current(self.profile,self.depth,'suggested_topics')
            if node and 'suggested_topics' not in self.fn.coverage:
                self._ask_fn(node)
                return True
        return False

    def _fn_turn(self, text, client, indicator_client=None, score_client=None, skipped=False, retry_row=None):
        node=self.fn.current(self.profile,self.depth,self.objective)
        if node and node['response_type']=='citizen_depth':
            self._duration_turn(text,skipped)
            return
        if node is None:
            self._route_fn(indicator_client,score_client)
            return
        row=retry_row or self._user(text,not skipped and node['response_type'] not in {'opinion','permission'},'advance_request' if skipped and direct_intent(text)=='advance' else 'skip' if skipped else 'opinion' if node['response_type']=='opinion' else 'answer')
        goal=node['id']
        result=None
        self._last_decision['fn_stage']=self.fn.stage_for(self.profile,self.depth,goal)['id']
        if skipped:
            self.fn.record(goal,row['id'],'declined','declined')
            if goal=='area':
                self.context['city']=None
                self.context['city_status']='withheld_or_uncertain'
        elif node['response_type']=='city':
            unknown=withheld_area(text)
            self.context['city']=None if unknown else text.strip()
            self.context['city_status']='withheld_or_uncertain' if unknown else 'respondent_provided_unverified'
            row['context_fields']=['city']
            self.fn.record(goal,row['id'],'unknown' if unknown else 'explored')
            self._last_decision['validated_context_facts']=[{'field':'city','evidence_id':row['id'],'status':self.context['city_status']}]
            self._assistant('Thank you. We will keep the area general.' if unknown else
                'Thank you. I will use that city or urban area as the context for your answers.',act='city_acknowledgement')
        elif node['response_type']=='opinion':
            # This is administration of a separate opinion, not an inferred
            # readiness capability. It cannot nominate other goals or a score.
            self.fn.record(goal,row['id'],'unknown' if literal_answer(text)=='uncertain' else 'explored')
        else:
            # Exact explicit choices need no model. Qualified/nonliteral answers
            # use the same single inference that interprets and proposes wording.
            kind=literal_answer(text) if node['response_type'] in {'yes_no','permission'} else None
            if self.profile=='citizen' and goal=='drone_explanation':
                action=educational_choice(text)
                if action in {'explain','skip_explanation'}:kind='yes' if action=='explain' else 'no'
            result=None
            if kind is not None:
                self.fn.record(goal,row['id'],'unknown' if kind=='uncertain' else 'explored',kind)
            else:
                try:
                    request=self._request(text)
                    result=self._generate(client,request)
                    if result.get('_quality_issues'):
                        self.routing_events.append({'event':'question_fallback','issues':result['_quality_issues'],'evidence_id':row['id']})
                    interpretation=result.get('interpretation')
                    if not interpretation: raise AssessmentError('Grounded interpretation unavailable.',code='evidence',field='interpretation')
                    self.failed_turn_id=None
                    for entry in interpretation['coverage']:
                        if entry['goal']=='priorities' and goal!='priorities' and not re.search(r'priorit|matter most|focus on|choos|select|most important',entry['quote'],re.I):
                            continue
                        self.fn.record(entry['goal'],entry['evidence_id'],entry['status'],entry['answer_kind'])
                        self.covered[entry['goal']]=list(self.fn.coverage[entry['goal']]['evidence_ids'])
                    if goal in self.fn.coverage and node['response_type'] in {'yes_no','permission'}:
                        self.fn.facts[goal]=interpretation['answer_kind']
                    accepted=self._apply_context_facts(result,text,row['id'])
                    self._last_decision['validated_context_facts']=accepted
                    self._fn_topics(row,interpretation)
                    if self._topic_disposition(row,interpretation):return
                    if self.profile=='organisational' and goal in {'remit','outside_remit'} and interpretation.get('scope_disposition')=='outside_remit':
                        self.context['scope_status']='outside_remit'
                        self.partial=True
                        self.stop_reason='outside_organisation_remit'
                        self._assistant('This service falls outside the responsibilities you described. I will not assess your organisation against those activities.',act='scope_clarification')
                        self._report(indicator_client,score_client)
                        return
                    if goal=='priorities' and len(interpretation['topics'])>3:
                        self.fn.coverage.pop(goal,None)
                        self.fn.followups[goal]=self.fn.followups.get(goal,0)+1
                        if self.fn.followups[goal]<=1:
                            self._assistant('I noted those issues. Which two or three would you most like us to focus on?',goal)
                            return
                        self.fn.record(goal,row['id'],'unknown','uncertain')
                    for boundary in interpretation.get('boundary_goals',[]):
                        if boundary not in self.fn.boundary_uncertainty and self.fn.boundary_probes<2:
                            self.fn.boundary_uncertainty.append(boundary);self.fn.boundary_probes+=1
                    self.annotations.append({'evidence_id':row['id'],'indicator_ids':result['indicator_ids'],
                        'answer_kind':interpretation['answer_kind'],
                        'goal_evidence':[{key:value for key,value in entry.items() if key!='quote'} for entry in interpretation['coverage']],
                        'dialogue_act':result['act'],'covered_objectives':[e['goal'] for e in interpretation['coverage']],
                        'quote':None,'status':'interpretation_unreviewed','revision':self.revision})
                    self._last_decision.update({key:deepcopy(result.get(key)) for key in ('proposed_action','act','topic','justification','evidence_ids','source_ids','uncertainty')})
                    self._last_decision['validated_action']=interpretation['action']
                    self._last_decision['rejected_optional_annotations']=result.get('_annotation_warnings',[])
                    self._last_decision['fn_coverage']=[{k:v for k,v in e.items() if k!='quote'} for e in interpretation['coverage']]
                    if result['act']=='explanation_offer' or interpretation['action']=='explain' or result['proposed_action']=='provide_information':
                        passages=request.get('retrieved_context',{}).get('passages',[])
                        passage=next((p for p in passages if p['id'] in result['source_ids']),None)
                        requested=text.strip().endswith('?') or bool(re.search(r'\b(?:what|how|explain|tell me|information|understand)\b',text,re.I))
                        if not passage or not requested or result['act']=='explanation_offer':
                            self.pending_explanation={'goal':goal,'text':passage['text'] if passage else 'A drone is an aircraft that can fly without a pilot sitting inside it. Drones can be different sizes and can be used for many different purposes.',
                                'source':deepcopy(passage.get('source',{})) if passage else deepcopy(self._rubric()['source'])}
                            self._assistant('Would you like a short explanation before we continue?',goal,'explanation_permission')
                            return
                        if passage:
                            self._assistant(passage['text']+' This is general information; it does not establish local operations.',act='supplied_information')
                            self.exposures.append({'id':f'x{len(self.exposures)+1}','kind':'retrieved_source_information','source':deepcopy(passage.get('source',{})),
                                'source_id':passage['id'],'text':passage['text'],'prior_knowledge':False,'actual_activity':False,'revision':self.revision})
                            self._last_decision.update(accepted_action='provide_information',postcondition={'exposure_recorded':True,
                                'exposure_id':self.exposures[-1]['id'],'participant_text_from_source':passage['id']})
                    if goal not in self.fn.coverage:
                        count=self.fn.followups.get(goal,0)
                        if count<1:
                            self.fn.followups[goal]=count+1;self.fn.next_action=interpretation['action']
                            self._assistant(self._fallback_question(text) if result.get('_quality_issues') else result['message'],goal)
                            return
                        self.fn.record(goal,row['id'],'unresolved','uncertain')
                except (AssessmentError,httpx.HTTPError,ValueError) as exc:
                    code=getattr(exc,'code','model_failure')
                    category='action_contract' if code=='schema' else 'context_budget' if code=='budget' else 'interpretation_unavailable'
                    field=getattr(exc,'field',None)
                    self.failures.append({'stage':'chat_turn','code':code,'category':category,'field':field,'revision':self.revision,
                        'inference_started':bool(getattr(client,'last_metrics',{}).get('generation_calls')),
                        'privacy_entities':list(getattr(exc,'entity_types',())),
                        'privacy_field_paths':[f.get('field_path','root') for f in getattr(exc,'findings',())],
                        'validation_fields':deepcopy(getattr(exc,'validation_fields',[]))})
                    _log.warning('chat_interpretation_failure code=%s field=%s goal=%s',code,field,goal)
                    self._last_decision.update(fallback_used=True,error=code,accepted_action='answer_processing_failed')
                    self.failed_turn_id=row['id']
                    if code=='budget' and getattr(exc,'field',None)!='prompt_context':
                        self.partial=True
                        self.finish('call_or_context_budget_partial')
                        return
                    message=('The shared GPU is unavailable or could not start. Your answer is saved. '
                        'Type retry when you are ready to try again, or skip, pause or stop.' if code=='gpu_unavailable' else
                        'A technical problem prevented me from processing your answer. '
                        'Your answer is saved; you do not need to reword it. '
                        'Type retry to try again, or skip, pause or stop.')
                    self._assistant(message,goal,'failure')
                    return
            field=node.get('context_field')
            if field and not self.context.get(field) and not withheld_area(text) and self.fn.coverage.get(goal,{}).get('status')=='explored':
                self.context[field]=text;row.setdefault('context_fields',[]).append(field)
                self.context['scope_status']='respondent_described'
            if goal=='technical_object':
                obj=self.context['technical_object']
                # The FN worked-example aircraft noise question is optional.
                # Do not apply its aircraft wording to an explicitly separate
                # component. This is applicability, never a maturity judgment.
                self.fn.facts['aircraft_scope']=bool(re.search(r'\b(?:aircraft|multicopter|drone)\b',obj,re.I)
                    and not re.search(r'\bnot (?:the |an |a )?(?:aircraft|drone)|\b(?:component|subsystem)\b',obj,re.I))
            if node['response_type']=='permission' and self.fn.facts.get(goal)=='yes':
                explanation=node.get('explanation') or ('Some drones or other aircraft can create strong air movement when taking off or landing. This can matter when deciding how close people, objects or buildings can safely be to the take-off and landing area.' if goal=='air_explanation' else 'A drone is an aircraft that can fly without a pilot sitting inside it. Drones can be different sizes and can be used for many different purposes.')
                self._assistant(explanation,act='supplied_information')
                self.exposures.append({'id':f'x{len(self.exposures)+1}','kind':'FN_explanation','text':explanation,
                    'source':deepcopy(self._rubric()['source']),'prior_knowledge':False,'revision':self.revision})
        if goal in self.fn.coverage:self.covered[goal]=list(self.fn.coverage[goal]['evidence_ids'])
        from .adaptive_interview import enabled, adaptive_goal
        if (enabled() and result is not None and goal in self.fn.coverage
                and adaptive_goal(node) and goal!='priorities'
                and interpretation.get('action')=='follow_up'
                and not result.get('_quality_issues') and result.get('message','').count('?')==1
                and self.fn.followups.get(goal,0)<1
                and self.adaptive_probes < (3 if self.depth=='short' else 7)):
            self.fn.followups[goal]=self.fn.followups.get(goal,0)+1
            self.adaptive_probes+=1
            self._respond_to_information_need(text)
            self._assistant(result['message'],goal,act='question')
            self.messages[-1]['source']={**deepcopy(self._rubric()['source']),
                'locator':node['source_locator'],'specification_version':self.fn.version,
                'wording':'LLM_contextual_probe_pending_review'}
            self.routing_events.append({'event':'adaptive_probe','objective_id':goal})
            return
        if result is not None and not any(e.get('kind') in {'retrieved_source_information',
                'permissioned_explanation'} and e.get('revision')==self.revision for e in self.exposures):
            self._respond_to_information_need(text)
        self._route_fn(indicator_client,score_client)
        if result is not None:
            self._adapt_next_fn_question(client,text)

    def _correction_target(self, text):
        cues = {
            'area': r'\b(?:city|area|locality)\b', 'perspective': r'\b(?:perspective|profile)\b',
            'technical_role': r'\btechnical role\b',
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
            if key not in {'city','organisation_or_unit','responsibilities','technical_object','object_version','intended_environment','technical_role','expertise'}: continue
            if isinstance(value, str) and value and value in target['text']:
                self.context[key] = None if key == 'city' else ''
        if target['objective_id']=='area' or 'city' in target.get('context_fields',[]):
            self.context['city'] = None if withheld_area(text) else text
            self.context['city_status'] = 'withheld_or_uncertain' if withheld_area(text) else 'respondent_provided_unverified'
        if target['objective_id'] in {'organisation_context','technical_role'}:
            field = 'organisation_or_unit' if target['objective_id']=='organisation_context' else 'technical_role'
            self.context[field] = '' if withheld_area(text) else text
            row['context_fields'] = [field]
        target['active'] = False
        row['supersedes'] = target['id']
        for objective in list(self.covered):
            if target['id'] in self.covered[objective]: del self.covered[objective]
        self.pending_correction = None
        self._invalidate('Respondent corrected evidence')
        # Administrative choices and permission/skip decisions support routing,
        # while remaining excluded from readiness evidence.
        self.fn.invalidate({m['id'] for m in self.messages if m['role']=='respondent' and m['active']})
        for concern in self.concerns:
            if target['id'] in concern['evidence_ids']:
                concern['evidence_ids']=[i for i in concern['evidence_ids'] if i!=target['id']]
                concern['selected_priority']=False;concern['priority']=False;concern['explored']=False
        self.priorities=[p for p in self.priorities if p['evidence_id']!=target['id']]
        if target['objective_id'] in {'perspective','scope','technical_object'}:
            row['evidence_status'] = 'scope_change_unresolved'
            self.stage = 'scope_change'
            self._assistant('This changes the assessed perspective or object. Download this record, then use New conversation so incompatible scopes remain separate.', act='scope_clarification')
        elif self.stage == 'summary':
            self._assistant('Your corrected words are in the summary. Say “no changes” when you are ready to continue.', act='summary')
        elif self.stage in {'review','review_addition'}:
            self.stage='review_addition'
            self.participant_review=self.participant_review or {'text':text,'response_id':row['id'],
                'status':'pending_after_new_evidence','validation':'correction_pending','independent_validation':False,
                'preferred_level':None,'model_result_revision':self.initial_results[-1]['revision'] if self.initial_results else None}
            self.review_step='correction'
            self._assistant('Your correction is recorded. The initial result is preserved for review and is no longer a current judgment of the corrected evidence. No reassessment is automatic. Write “no changes” to finish.',act='review_recorded')
        else:
            self._assistant('Your correction is recorded. I will revisit any evidence goals that depended on the replaced answer.',act='correction')
            if target['objective_id']=='area': self.fn.record('area',row['id'],'unknown' if self.context['city'] is None else 'explored')
            self._route_fn()

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
            if message and message['id'] not in selected and len(selected)<8 and size+len(message['text'])<=3200:
                selected[message['id']]=message;size+=len(message['text'])
        return [{'evidence_id':m['id'],'quote':m['text'],'objective_id':m['objective_id'],'topic':m.get('topic')}
                for m in originals if m['id'] in selected]

    def finish(self, reason='respondent_finish'):
        self.pending_comparison = None
        self.stop_reason = reason
        self.stage = 'summary'
        self._assistant('Here is a copy of the points you shared, including uncertainties. Please tell me anything to correct or add. If nothing needs changing, write “no changes” to see the scale and provisional summary.', act='summary')

    def _indicator_report(self, client):
        """At most two scoped matches, never fifteen calls per turn or score averaging."""
        self.indicator_results = []
        if client is None or not self.profile: return
        if self.context['scope_status']=='outside_remit':return
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
                                     'generated_tokens':getattr(client,'last_metrics',{}).get('generated_tokens'),
                                     'generation_http_seconds':getattr(client,'last_metrics',{}).get('generation_http_seconds'),
                                     'model_wait_seconds':getattr(client,'last_metrics',{}).get('model_wait_seconds'),
                                     'report_indicator_id': indicator_id, 'considered_evidence_ids': list(original)})
            self.indicator_results.append(row)

    def _has_model_score(self):
        result=self.suggestion or {}
        return (result.get('status')=='suggested' and type(result.get('level')) is int
                and 1<=result['level']<=9 and bool(result.get('anchor_id')))

    def _report(self, indicator_client=None, score_client=None):
        self.stage = 'review'
        self._assistant('Thank you. We have finished the main questions.' if not self.partial else 'We stopped before exploring every part of the interview. This is a partial record.',act='scale_disclosure')
        self._assistant('I will now show you the scale used to understand your answers. The judgment is provisional and based on self-report.',act='scale_notice')
        if self.fn.unresolved_gaps:
            self._assistant('Some points were left uncertain or skipped. They remain explicit gaps; they do not automatically lower readiness.',act='uncertainty')
        from .chat_score import validate_profile_match
        scale = self._rubric() if self.profile else None
        self.suggestion = {'status': 'abstained', 'level': None, 'anchor_id': None,
            'policy_version': POLICY, 'revision': self.revision, 'result_version':1, 'partial_interview':self.partial, 'rubric_version': (scale or {}).get('rubric_version'),
            'explanation': 'There is not enough usable scoped evidence for an overall level.',
            'gaps': [], 'considered_evidence_ids': [], 'evidence_sufficiency': 'insufficient', 'external_verification': 'not_performed'}
        originals = [{'id': m['id'], 'text': m['text'], 'objective': m['objective_id'],
                      'information_exposure_ids': m['information_exposure_ids']} for m in self.active_evidence()]
        scope_ready = self.profile=='citizen' or (self.profile=='organisational' and self.context['organisation_or_unit'] and self.context['responsibilities']) or (self.profile=='technical' and self.context['technical_object'])
        scope_ready=scope_ready and self.context['scope_status']!='outside_remit'
        if score_client and scale and scope_ready and originals and self.calls + 4 <= self.limits['calls']:
            from .model_spec import thinking_enabled
            if not thinking_enabled() and sum(len(m['text']) for m in originals) > 5000:
                self.suggestion['gaps'] = ['Complete original evidence exceeds this bounded judgment request. No evidence was silently omitted.']
            else:
                payload = {'profile': self.profile, 'scope': self.context, 'anchors': scale['anchors'],
                           'guidance': scale['guidance'], 'originals': originals, 'supplied_information': self.exposures,
                           'exploration_gaps': self.fn.unresolved_gaps, 'partial_interview': self.partial}
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
                                         'generated_tokens':getattr(score_client,'last_metrics',{}).get('generated_tokens'),
                                         'reasoning_characters':getattr(score_client,'last_metrics',{}).get('reasoning_characters',0),
                                         'reasoning_enabled':getattr(score_client,'last_settings',{}).get('enable_thinking',False),
                                         'generation_http_seconds':getattr(score_client,'last_metrics',{}).get('generation_http_seconds'),
                                         'model_wait_seconds':getattr(score_client,'last_metrics',{}).get('model_wait_seconds'),
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
        self._review_prompt()

    def _review_prompt(self):
        if not self._has_model_score():
            self._assistant('There is not enough consistent evidence for a defensible numeric level. You may comment, say “I am not sure”, or write “no changes” to finish without a score. No level is invented.',act='assessment_gap')
            return
        config=specification()['review'][flow_key(self.profile,self.depth)]
        text=config['question'].format(level=self.suggestion['level'])
        text+='\n\n'+'\n'.join(f'{letter}. {label}' for letter,label in zip('ABCDE',config['choices']))
        self._assistant(text,act='result_review')

    def _fn_review(self, text):
        value=text.strip().casefold().rstrip('.!')
        empty=value in {'no changes','nothing to add','no additional facts','nothing','no'}
        if self.stage=='review_addition':
            if empty:
                self._user(text,False,'review_completion')
                self.stage='ended';self.stop_reason='respondent_review_complete'
                self._assistant('Thank you. Your comments are recorded with review pending. The initial model suggestion is unchanged. Contact follow-up is unavailable; download a copy to keep your record.',act='end')
                return
            row=self._user(text,True,'additional_evidence')
            self.participant_review.setdefault('additional_evidence_ids',[]).append(row['id'])
            if not self.initial_results:
                self.initial_results.append({'suggestion':deepcopy(self.suggestion),'indicator_results':deepcopy(self.indicator_results),
                    'reason':'Additional evidence after result; no automatic reassessment','revision':(self.suggestion or {}).get('revision')})
            config=specification()['review'][flow_key(self.profile,self.depth)]
            if self.review_step=='explanation' and self.participant_review.get('choice') in {'B','C','D'}:
                self.review_step='detail'
                self._assistant(config['detail'],act='review_addition')
                return
            if self.profile=='technical' and self.review_step=='detail':
                self.review_step='outstanding'
                self._assistant(config['outstanding'],act='review_addition')
                return
            self.stage='ended';self.stop_reason='respondent_review_pending'
            self._assistant('Thank you. I recorded the additional information for review. The initial provisional result has not changed. No contact follow-up service is available; download a copy to keep it.',act='end')
            return
        # Literal A–E and their conversational meanings are interaction choices,
        # never readiness evidence. A number is a separate participant preference.
        match=re.fullmatch(r'([a-e])(?:[. :]\s*(.*))?',value)
        if match and match[2] and (re.search(r'\b(?:or|maybe)\s+[a-e]\b',match[2]) or
                (match[1]=='a' and re.search(r'\b(?:but|however|missing|disagree|not)\b',match[2]))):
            self._user(text,False,'review_clarification')
            self._assistant('Which choice best fits your view: A, B, C, D or E? You can also explain what leaves you uncertain.',act='review_clarification')
            return
        choice=match[1].upper() if match else None
        preferred=re.search(r'\b(?:prefer|level|CRL|ORL|TRL|choose)\s*(?:level\s*)?([1-9])\b',text,re.I) or re.fullmatch(r'\s*([1-9])[.! ]*',text)
        if not choice:
            if re.search(r'\b(?:higher|too low)\b',value):choice='C'
            elif re.search(r'\b(?:lower|too high)\b',value):choice='D'
            elif re.search(r'\b(?:missing|mostly|disagree)\b',value):choice='B'
            elif re.search(r'\b(?:not sure|unsure|uncertain)\b',value):choice='E'
            elif empty or re.search(r'^(?:i agree|agrees?|it describes (?:me|the organisation|the system) well|that fits|looks right)',value):choice='A'
            elif preferred and self._has_model_score():choice='C' if int(preferred[1])>self.suggestion['level'] else 'D' if int(preferred[1])<self.suggestion['level'] else 'A'
        if preferred and not self._has_model_score():
            self._user(text,False,'self_assessment_unavailable')
            self._assistant('There is no valid numeric model result to validate. You can leave a comment or write “no changes” to finish without a score.',act='assessment_gap')
            return
        row=self._user(text,False,'result_review')
        self.participant_review={'text':text,'response_id':row['id'],'choice':choice or 'comment',
            'validation':'agrees' if choice=='A' and self._has_model_score() else 'uncertain' if choice=='E' else 'pending_review',
            'status':'agreed' if choice=='A' and self._has_model_score() else 'pending_human_review',
            'preferred_level':int(preferred[1]) if preferred else None,'independent_validation':False,
            'model_result_revision':(self.suggestion or {}).get('revision'),'automatic_reassessment':False}
        if choice=='A' or (not self._has_model_score() and empty):
            self.stage='ended';self.stop_reason='respondent_validation_recorded'
            if not self._has_model_score():self.participant_review.update(validation='completed_without_numeric_result',status='completed_without_numeric_result')
            self._assistant('Thank you. Your validation is recorded separately from the provisional result. Download a copy if you would like to keep it.',act='end')
            return
        config=specification()['review'][flow_key(self.profile,self.depth)]
        question=(config['higher'] if choice=='C' else
            'Why do you think the level should be lower? What evidence or limitation should be considered?' if choice=='D' else
            'What important information is missing from the explanation?' if choice=='B' else
            'Which part of the explanation or scale leaves you uncertain? You can also say you have nothing to add.')
        self.stage='review_addition';self.review_step='explanation'
        self._assistant(question,act='review_addition')

    def show_case(self, text, card):
        self.revision += 1
        self._user(text,False,'example_request')
        if card is None:
            self._assistant('An illustrative example is unavailable right now. We can continue in general.',act='example_unavailable')
            return
        exposure={'id':f'x{len(self.exposures)+1}', 'kind':'illustrative_case',
            'source_id':card['id'], 'source':deepcopy(card.get('source',{})),
            'source_status':card.get('source_status','illustrative_source_record'),
            'source_verification':card.get('source_verification','not_independently_verified'),
            'unknowns':deepcopy(card.get('unknowns',[])), 'text':card['text'],
            'revision':self.revision,'prior_knowledge':False,'actual_activity':False}
        self.exposures.append(exposure)
        self._assistant('Illustrative example only. '+card['text']+
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
        if (intent is None and self.profile=='citizen' and self.stage=='conversation'
                and self.objective!='citizen_duration' and re.search(
                    r'\b(?:switch|change|shorten|lengthen)\b|\b(?:interview|conversation)\s+(?:style|depth)|\b(?:shorter|longer|extended) (?:interview|conversation)\b',text,re.I)):
            preference=citizen_depth_choice(text)
            if preference:intent=preference[0]
        retry_row = None
        if intent == 'retry':
            retry_row=next((m for m in self.active_evidence()
                            if m['id']==self.failed_turn_id and m['objective_id']==self.objective),None)
            self._user(text,False,'retry_request')
            if retry_row is None:
                self._assistant('There is no failed answer waiting to retry. You can continue or finish.',act='recovery')
                return
            text=retry_row['text']
        elif self.failed_turn_id and intent is None:
            # Resending the same retained answer is also an idempotent retry.
            retry_row=next((m for m in self.active_evidence() if m['id']==self.failed_turn_id
                            and m['objective_id']==self.objective and m['text']==text),None)
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
            self._paused_stage = self.stage
            self.stage = 'paused'
            self._assistant('We can pause here. Progress remains temporary; download a copy if you need to leave. Say “continue” when you are ready.', act='pause')
            return
        if self.stage == 'scope_change' and intent not in {'stop','withdraw'}:
            self._user(text,False,'unresolved_scope')
            self._assistant('Please download this scoped conversation if you need it, then use New conversation for the new perspective or object.',act='scope_clarification')
            return
        if self.stage == 'paused':
            self._user(text, False, 'resume')
            self.stage = self._paused_stage or 'conversation'
            node=self.fn.current(self.profile,self.depth,self.objective)
            self._assistant('Welcome back. '+(node['canonical_question'] if node else 'You can continue the review or stop.'), self.objective)
            return
        if (self.profile=='citizen' and self.objective=='drone_explanation' and self.stage=='conversation'
                and (educational_choice(text)=='finish' or intent=='stop')):
            self._educational_exit(text)
            return
        if intent == 'stop':
            self._user(text, False, 'stop')
            if self.stage in {'summary', 'review', 'review_addition'}:
                self.stage = 'ended'
                self._assistant('We can stop here. Download a copy if you would like to keep it.', act='end')
            else:
                self.partial=True
                self.finish('respondent_finish_partial')
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
            pending=self.pending_explanation
            self._user(text,False,'explanation_permission')
            kind=literal_answer(text)
            if kind is None and intent not in {'skip','advance'}:
                request=self._request(text);request['fn']['response_type']='permission';request['fn']['allowed_objectives']={}
                try:
                    response=self._generate(client,request)
                    kind=(response.get('interpretation') or {}).get('answer_kind')
                except (AssessmentError,httpx.HTTPError):kind='uncertain'
            if kind=='yes':
                self._assistant(pending['text'],act='supplied_information')
                self.exposures.append({'id':f'x{len(self.exposures)+1}','kind':'permissioned_explanation','text':pending['text'],
                    'source':pending['source'],'prior_knowledge':False,'revision':self.revision})
            self.pending_explanation=False
            current=self.fn.current(self.profile,self.depth,pending['goal'])
            if current and pending['goal'] not in self.fn.coverage:self._ask_fn(current)
            else:self._route_fn(indicator_client,score_client)
            return
        if intent in {'short', 'extended'}:
            if self.objective=='citizen_duration':
                self._duration_turn(text)
                return
            row=self._user(text,False,'depth_preference')
            if self.stage!='conversation' or self.profile not in {None,'citizen'}:
                self._assistant('The interview version and result scale stay with this record. You can continue the current question or review; use New conversation to choose a different citizen interview version.',act='depth_notice')
                return
            if self.profile:
                self._select_depth(intent,'participant_change',row['id'])
                self._assistant('We will use the '+('shorter' if intent=='short' else 'more detailed')+' interview style. Earlier answers are retained.',act='depth_acknowledgement')
                self._route_fn(indicator_client,score_client)
            else:
                self.depth=intent
                self._assistant(PERSPECTIVE,'perspective')
            return
        if intent == 'scale':
            self._user(text, False, 'methodology_request')
            if not self.profile:
                self._assistant('There are different scales for personal views, an organisation, and a technology. Which perspective would you like to discuss?', 'perspective')
                return
            self.exposures.append({'id': f'x{len(self.exposures)+1}', 'kind': 'reference_scale', 'revision': self.revision, 'prior_knowledge': False})
            self._assistant('The summary considers the meaning of your answers, with opinion and actual activity kept distinct. The full readiness scale is shown below. This is a provisional profile judgment, not an overall societal SRL. This exposure is recorded.', act='methodology')
            return
        if intent == 'topic':
            self._user(text, False, 'change_topic')
            self._assistant('Of course. What issue would you prefer to use as an example for this point?', self.objective)
            return
        if intent == 'back':
            self._user(text, False, 'back')
            earlier = self.active_evidence()
            if earlier:
                self.pending_correction = earlier[-1]['id']
                self._assistant('What would you like to change about this earlier point: “' + earlier[-1]['text'] + '”?', act='correction')
            else: self._assistant('We are at the beginning. ' + PERSPECTIVE, 'perspective')
            return
        if self.pending_correction == 'clarify':
            if self.stage == 'summary' and re.fullmatch(r'(no changes|continue)[.! ]*', text, re.I):
                self.pending_correction = None
                self._user(text, False, 'summary_review')
                self._report(indicator_client, score_client)
                return
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
        if self.pending_correction and self.pending_correction!='clarify':
            target=next((m for m in self.active_evidence() if m['id']==self.pending_correction),None)
            if target:self._apply_correction(target,text)
            else:self.pending_correction=None
            return
        if self.stage in {'review','review_addition'}:
            self._fn_review(text)
            return
        if self.pending_correction == 'clarify' and re.fullmatch(r'(no changes|continue)[.! ]*', text, re.I):
            self.pending_correction = None
            self._user(text, False, 'summary_review')
            self._report(indicator_client, score_client)
            return
        if intent == 'simplify' and self.objective in {'perspective','area','citizen_duration','drone_recognition','drone_description','organisation_context','technical_role'}:
            self._user(text, False, 'simplification')
            question = {
                'perspective': 'Are you answering for yourself, an organisation, or a technology?',
                'area': 'Which city or broad area should we discuss? You can say you prefer not to answer.',
                'citizen_duration': 'Would you prefer a shorter conversation, around 20 minutes (A), or more detail, around 35 minutes (B)? If unsure, we can start short.',
                'drone_recognition': 'Do you know what a drone is?',
                'drone_description': 'How would you describe a drone in your own words?',
                'organisation_context': 'What kind of organisation are you speaking for? Its name is not needed.',
                'technical_role': 'What technical work do you do with drones?',
            }[self.objective]
            self._assistant(question, self.objective)
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
        if self._onboarding_answer(text): return
        if intent in {'skip','advance'}:
            self._fn_turn(text,client,indicator_client,score_client,skipped=True)
            return
        if len(self.active_evidence()) >= self.limits['turns'] or sum(m['wall_seconds'] for m in self.metrics) >= self.limits['processing_seconds'] or self.calls+4>self.limits['calls']:
            self._user(text,True)
            self.failures.append({'stage':'chat_turn','code':'budget','category':'operational_limit','revision':self.revision})
            self.partial=True
            self.finish('operational_limit_partial')
            return
        if intent == 'comparison':
            self._user(text,False,'comparison_request')
            request=self._request('',comparison=True)
            try: result=self._generate(client,request)
            except (AssessmentError,httpx.HTTPError):result={}
            node=self.fn.current(self.profile,self.depth,self.objective)
            variants=result.get('variants') or [node['canonical_question'], 'What would you want me to understand about this point?']
            self.pending_comparison={'objective_id':self.objective,'context_revision':self.revision,
                'variants':[{'response_id':f'v{self.revision}-{i}','text':t} for i,t in enumerate(variants)],
                'display_order':[f'v{self.revision}-{i}' for i in range(2)],'semantic_review':'pending','training_eligible':False}
            self._assistant('Which wording do you prefer, 1 or 2? You can also say neither or no preference.',act='preference')
            return
        self._fn_turn(text,client,indicator_client,score_client,retry_row=retry_row)

    def response_options(self):
        if self.pending_correction or self.pending_explanation or self.pending_comparison or self.failed_turn_id:
            return []
        if self.stage=='conversation':
            if self.objective=='perspective':return letter_options(PERSPECTIVE)
            if self.profile=='citizen' and self.objective=='citizen_duration':return letter_options(CITIZEN_DURATION)
            if self.profile=='citizen' and self.objective=='drone_explanation':return letter_options(EDUCATIONAL_OPTIONS)
        if self.stage=='review' and self._has_model_score():
            config=specification()['review'][flow_key(self.profile,self.depth)]
            return [{'value':key,'label':label} for key,label in zip('ABCDE',config['choices'])]
        return []

    def view(self):
        participant_messages = [{key:message[key] for key in ('id','role','text','act','resource','scale') if key in message}
                                for message in self.messages]
        educational_exit=self.stop_reason=='ended_early_after_recognition'
        return {'mode': SCHEMA, 'stage': self.stage, 'depth': self.depth, 'profile': self.profile,
                'response_options':self.response_options(),
                'citizen_depth':self.depth if self.profile=='citizen' else None,
                'depth_selection':deepcopy(self.depth_selection),'depth_history':deepcopy(self.depth_history),
                'answer_processing': {'status':'retry_required' if self.failed_turn_id else 'ready',
                                      'evidence_id':self.failed_turn_id},
                'messages': deepcopy(participant_messages), 'pending_comparison': deepcopy(self.pending_comparison),
                'summary': self._summary() if self.stage != 'conversation' else [],
                'scale': self._rubric() if self.profile and not educational_exit and (self.stage in {'review','review_addition','ended'} or any(e.get('kind')=='reference_scale' for e in self.exposures)) else None,
                'suggestion': deepcopy(self.suggestion), 'self_assessment_available':self.stage=='review' and self._has_model_score(), 'participant_review': deepcopy(self.participant_review),
                'initial_suggestion': deepcopy(self.initial_results[0]['suggestion']) if self.initial_results and self.participant_review else None,
                'assisted': self.assisted,
                'completion': {'conversation': self.stage == 'ended', 'partial':self.partial,
                               'termination_reason':self.stop_reason,
                               'methodological_progression':'incomplete' if not self.profile or self.fn.next(self.profile,self.depth,self.concerns) else 'goals_explored',
                               'evidence_sufficiency': 'unassessed' if educational_exit else (self.suggestion or {}).get('evidence_sufficiency', 'pending_after_new_evidence' if self.initial_results else 'not_judged'),
                               'participant_review': 'provided' if self.participant_review else 'not_provided',
                               'review': (self.participant_review or {}).get('status', 'not_reviewed')}}

    def export(self):
        progression=self.fn.export(self.profile,self.depth,self.concerns)
        objective_coverage=[{'objective_id':stage['id'],'status':stage['status'],
            'evidence_ids':list(dict.fromkeys(eid for goal in stage['goals'] for eid in goal['evidence_ids'])),
            'readiness_inferred':False} for stage in progression['stages']]
        return {**self.view(), 'messages':deepcopy(self.messages), 'schema_version': SCHEMA, 'policy_version': POLICY,
                'classification': 'synthetic' if self.synthetic else 'unlabelled_not_verified',
                'model_provenance':deepcopy(self.model_provenance),
                'inference_configuration':deepcopy(self.inference_configuration),
                'fn_interview':progression,
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
