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
    if re.fullmatch(r"(?:please )?(?:retry|try again)", value): return 'retry'
    if re.fullmatch(r"(?:please )?(?:show (?:me )?an example|give (?:me )?an example|show an illustrative example)", value): return 'example'
    if re.fullmatch(r"(?:please )?(?:show two ways of asking that|show two wordings)", value): return 'comparison'
    if re.fullmatch(r"(?:please )?(?:shorter conversation|keep it short)", value): return 'short'
    if re.fullmatch(r"(?:please )?(?:more detail|extended conversation)", value): return 'extended'
    return None


def explicit_capacity_choice(profile, quote):
    """Reject ambiguous role descriptions; this never infers capacity from a job."""
    patterns = {'citizen':r'personal|citizen|resident|myself|own views?|my views?',
                'organisational':r'organi[sz]ation|on behalf|representing|team|institution|unit.*responsibil',
                'technical':r'technical|technology|system|component|subsystem'}
    matches = [key for key,pattern in patterns.items() if re.search(pattern,quote,re.I)]
    if profile not in matches:return False
    return len(matches)==1 or bool(re.search(r'prefer|choos|today|personal views|own views|on behalf|answer.*as',quote,re.I))


class ChatSession:
    def __init__(self, bank, depth='short', synthetic=False, assisted=False):
        self.source_scales, self.source_register = load_rubrics()
        self.bank = deepcopy(bank)
        self.depth = depth
        self.synthetic = synthetic
        self.assisted = assisted
        self.withdrawn = False
        self.profile = None
        self.context = {'city': None, 'organisation_or_unit': '', 'responsibilities': '',
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

    def _eligible(self):
        rows = self._all_objectives()
        if not self.profile: return rows[:1]
        remaining = [r for r in rows if r['id'] not in self.covered]
        return remaining[:3]

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
        eligible = self._eligible()
        if comparison:
            eligible = [r for r in self._all_objectives() if r['id'] == self.objective]
        return {'answer': answer, 'profile': self.profile, 'context': self.context,
                'current_objective': self.objective, 'eligible': eligible,
                'objective_ids': [r['id'] for r in self._all_objectives()],
                'indicator_ids': [r['id'] for r in self.bank['indicators']],
                'prior_ids': [m['id'] for m in self.active_evidence()],
                'original_context': list(reversed(selected)), 'priority_context': deepcopy(priority), 'current_answer_id': current_id, 'omitted_context_ids': [m['id'] for m in self.active_evidence() if m['id'] not in ids],
                'comparison': comparison, 'depth': self.depth}

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
            self.calls += observed if observed is not None else 1
            self.metrics.append({'generation_calls': observed, 'wall_seconds': round(time.monotonic()-started, 3),
                                 'context_ids': [m['id'] for m in request['original_context']], 'current_answer_id':request['current_answer_id'],
                                 'priority_evidence_id':(request['priority_context'] or {}).get('evidence_id'),
                                 'omitted_context_ids': request['omitted_context_ids']})

    def _summary(self):
        """Compact exact-passages overview; scoring always uses all originals."""
        originals = self.active_evidence()
        groups = {}
        for message in originals:
            key = message['objective_id']
            if key in {'open_priorities','priorities'}: key='priorities'
            elif key in {'opportunity','influence','testing','integration','operational','qualification'}: key='activity'
            elif key not in {'perspective','area','scope','opinion'}: key='reasoning'
            if key!='opinion': groups[key]=message
            if re.search(r"not sure|don't know|do not know|unknown|uncertain|no opportunity",message['text'],re.I):
                groups['uncertainty']=message
        selected={};size=0
        for key in ['perspective','area','scope','priorities','activity','uncertainty','reasoning']:
            message=groups.get(key)
            if message and message['id'] not in selected and size+len(message['text'])<=3200:
                selected[message['id']]=message;size+=len(message['text'])
        return [{'evidence_id':m['id'],'quote':m['text'],'objective_id':m['objective_id']}
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
                row.update(status='unavailable', reason=getattr(exc, 'code', 'model_failure'))
            finally:
                count = getattr(client, 'last_metrics', {}).get('generation_calls')
                self.calls += count if count is not None else 1
                self.metrics.append({'generation_calls': count, 'wall_seconds': round(time.monotonic()-started,3),
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
                        assessments=value['assessments'], alternative_anchor_id=value['alternative_anchor_id'],
                        considered_evidence_ids=[m['id'] for m in originals],
                        evidence_sufficiency='provisionally_sufficient' if anchor else 'insufficient')
                except (AssessmentError, httpx.HTTPError, ValueError) as exc:
                    self.suggestion.update(status='unavailable', explanation='A valid provisional profile judgment is unavailable. Your original words are retained.',
                                           gaps=[getattr(exc,'code','model_failure')])
                finally:
                    count=getattr(score_client,'last_metrics',{}).get('generation_calls')
                    self.calls+=count if count is not None else 1
                    self.metrics.append({'generation_calls':count,'wall_seconds':round(time.monotonic()-started,3),'stage':'generic_profile_match',
                                         'considered_evidence_ids':[m['id'] for m in originals]})
        self._indicator_report(indicator_client)
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
            bank,depth,synthetic,assisted = self.bank,self.depth,self.synthetic,self.assisted
            self.__init__(bank,depth,synthetic,assisted)
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
            question = next(r for r in self._all_objectives() if r['id']==self.objective)
            self._assistant(question['question'], self.objective)
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
            self._assistant('We can adjust the depth. ' + next(r['question'] for r in self._all_objectives() if r['id'] == self.objective), self.objective)
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
            self.objective = 'priorities'
            self.covered.pop('priorities',None)
            self._assistant('What would you prefer to talk about?', 'priorities')
            return
        if intent == 'back':
            self._user(text, False, 'back')
            earlier = self.active_evidence()
            if earlier:
                self.pending_correction = earlier[-1]['id']
                self._assistant('What would you like to change about this earlier point: “' + earlier[-1]['text'] + '”?', act='correction')
            else: self._assistant('We are at the beginning. ' + WELCOME, 'perspective')
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
            row = self._user(text, True, 'correction')
            if target:
                for key,value in list(self.context.items()):
                    if key not in {'city','organisation_or_unit','responsibilities','technical_object','object_version','intended_environment'}: continue
                    if isinstance(value,str) and value and value in target['text']:
                        self.context[key]=None if key=='city' else ''
                target['active'] = False
                row['supersedes'] = target['id']
                for objective in list(self.covered):
                    if target['id'] in self.covered[objective]: del self.covered[objective]
            self.pending_correction = None
            self._invalidate('Respondent corrected evidence')
            if target and target['objective_id'] in {'perspective','scope'}:
                row['evidence_status']='scope_change_unresolved'
                self.stage='scope_change'
                self._assistant('This changes the assessed perspective or object. Please download this record, then use New conversation so incompatible scopes are kept separate.',act='scope_clarification')
                return
            if self.stage == 'summary':
                self._assistant('Your corrected words are in the summary. Say “no changes” when you are ready to continue.', act='summary')
            elif self._eligible():
                self.objective = self._eligible()[0]['id']
                self._assistant('Your correction is recorded. ' + self._eligible()[0]['question'], self.objective)
            else: self.finish('corrected_partial')
            return
        if intent == 'simplify':
            self._user(text, False, 'simplification')
            request = self._request(text)
            request['eligible'] = [r for r in self._all_objectives() if r['id']==self.objective]
            request['simplification'] = True
            try:
                result = self._generate(client, request)
                self._assistant(result['message'], self.objective)
            except (AssessmentError, httpx.HTTPError):
                self._assistant('I could not rephrase that just now. You can leave this question open, change topic or finish.', act='failure')
            return
        if intent == 'skip':
            row = self._user(text, False, 'skip')
            self.covered[self.objective] = [row['id']]
            choices = self._eligible()
            if not choices: self.finish('objectives_explored')
            else:
                self.objective = choices[0]['id']
                self._assistant('We can leave that open. ' + choices[0]['question'], self.objective)
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
            variants = [{'response_id': f'v{self.revision}-{i}', 'text': t} for i, t in enumerate(result['variants'])]
            random.SystemRandom().shuffle(variants)
            self.pending_comparison = {'objective_id': self.objective, 'context_revision': self.revision,
                'variants': variants, 'display_order': [v['response_id'] for v in variants], 'semantic_review': 'pending', 'training_eligible': False}
            self._assistant('Which wording do you prefer, 1 or 2? You can also say neither or no preference.', act='preference')
            return
        row = retry_row or self._user(text)
        self._invalidate('New respondent evidence')
        request = self._request(text)
        try:
            result = self._generate(client, request)
        except (AssessmentError, OSError, httpx.HTTPError) as exc:
            self.failed_turn_id = row['id']
            self.failures.append({'code': getattr(exc, 'code', 'transport'), 'revision': self.revision})
            if getattr(exc,'code',None)=='budget':
                self.finish('call_or_context_budget_partial')
                return
            self._assistant('I saved your screened words, but could not process the next step. You can say retry, add more, ask to finish, or download a copy.', act='failure')
            return
        self.failed_turn_id = None
        if result['act'] == 'scope_change':
            self.stage = 'scope_change'
            row['evidence_status'] = 'scope_change_unresolved'
            self._assistant('That may change who or what this conversation is about. Please download this conversation, then use New conversation for the new scope.', act='scope_clarification')
            return
        if not self.profile:
            if result['profile'] == 'unknown' or not explicit_capacity_choice(result['profile'],result['profile_quote']):
                self.visits['perspective']=self.visits.get('perspective',0)+1
                if self.visits['perspective']>=2:
                    self.finish('capacity_not_established_partial')
                    return
                self._assistant('Are you choosing your personal perspective, an organisation’s responsibilities, or a technology’s development?', 'perspective')
                return
            self.profile = result['profile']
            row['profile'] = self.profile
        for fact in result['context']:
            self.context[fact['field']] = None if fact['field']=='city' and re.search(r'prefer not|withheld|unknown|keep.*general',fact['quote'],re.I) else fact['quote']
        if self.profile == 'citizen' or (self.profile == 'organisational' and self.context['responsibilities']) or (self.profile == 'technical' and self.context['technical_object']):
            self.context['scope_status'] = 'respondent_described'
        if self.objective in {'open_priorities','priorities'}:
            self.priorities.append({'evidence_id':row['id'],'text':text,'origin':'spontaneous' if self.objective=='open_priorities' else 'selected_after_open_question'})
        self.annotations.append({'evidence_id': row['id'], 'indicator_ids': result['indicator_ids'],
            'dialogue_act':result['act'], 'covered_objectives':deepcopy(result['covered']),
            'quote': result['evidence_quote'], 'status': 'interpretation_unreviewed',
            'elicitation': 'spontaneous' if self.objective == 'open_priorities' else 'prompted', 'revision': self.revision})
        if result['act'] == 'correction' or self.pending_correction == 'clarify':
            target = result['correction_target']
            if target and target != row['id']:
                self.pending_correction = target
                self._assistant('Please state the corrected information for this earlier point: “' + next(m['text'] for m in self.messages if m['id']==target) + '”.', act='correction')
            else:
                self.pending_correction = 'clarify'
                self._assistant('Which earlier point would you like to correct?', act='correction')
            return
        if result['act'] == 'explanation_offer':
            self.pending_explanation = 'air_movement' if re.search(r'downwash|outwash|air movement',text,re.I) else 'drone'
            subject = 'air movement near landing areas' if self.pending_explanation=='air_movement' else 'what a drone is'
            self._assistant('Would you like a brief explanation of '+subject+'? You can say no and continue.', act='explanation_permission')
            return
        for item in result['covered']:
            # Preserve spontaneous-first ordering; later objectives cannot bypass this stage.
            if item['objective_id'] in {'priorities', 'open_priorities'} and 'healthcare' not in self.covered and self.profile == 'citizen': continue
            self.covered[item['objective_id']] = [row['id']]
        self.visits[self.objective] = self.visits.get(self.objective, 0) + 1
        if result['act'] != 'clarify' or self.visits[self.objective] >= 2:
            self.covered[self.objective] = [row['id']]
        choices = self._eligible()
        if not choices:
            self.finish('selective_objectives_explored')
            return
        # The model may adapt within a small eligible shortlist; code resolves IDs/sources.
        chosen = next((r for r in choices if r['id'] == result['next_objective']), choices[0])
        if self.objective in {'perspective','area','scope','familiarity','healthcare','open_priorities'}:
            chosen = choices[0]
        self.objective = chosen['id']
        message = result['message'] if result['next_objective'] == chosen['id'] and result['act'] not in {'finish'} else chosen['question']
        if result['act'] == 'finish': message = 'Would you like to finish now, or continue with this question? ' + chosen['question'].rstrip('?')
        self._assistant(message, self.objective)

    def view(self):
        return {'mode': SCHEMA, 'stage': self.stage, 'depth': self.depth, 'profile': self.profile,
                'messages': deepcopy(self.messages), 'pending_comparison': deepcopy(self.pending_comparison),
                'summary': self._summary() if self.stage != 'conversation' else [],
                'scale': self._rubric() if self.profile and (self.stage in {'review','review_addition','ended'} or any(e.get('kind')=='reference_scale' for e in self.exposures)) else None,
                'suggestion': deepcopy(self.suggestion), 'participant_review': deepcopy(self.participant_review),
                'initial_suggestion': deepcopy(self.initial_results[0]['suggestion']) if self.initial_results and self.participant_review else None,
                'synthetic': self.synthetic, 'assisted': self.assisted,
                'completion': {'conversation': self.stage == 'ended',
                               'evidence_sufficiency': (self.suggestion or {}).get('evidence_sufficiency', 'pending_after_new_evidence' if self.initial_results else 'not_judged'),
                               'participant_review': 'provided' if self.participant_review else 'not_provided',
                               'review': (self.participant_review or {}).get('status', 'not_reviewed')}}

    def export(self):
        return {**self.view(), 'schema_version': SCHEMA, 'policy_version': POLICY,
                'classification': 'synthetic' if self.synthetic else 'unlabelled_not_verified',
                'training_eligible': False, 'context': deepcopy(self.context),
                'evidence_revision': self.revision, 'annotations': deepcopy(self.annotations), 'priorities':deepcopy(self.priorities),
                'objectives': self._all_objectives(), 'information_exposures': deepcopy(self.exposures),
                'response_preferences': deepcopy(self.preferences), 'initial_results': deepcopy(self.initial_results),
                'indicator_projection': {'participant_reviewed': False, 'results': deepcopy(self.indicator_results),
                    'coverage': [{'indicator_id': i['id'], 'status': next((r['status'] for r in self.indicator_results if r['indicator_id']==i['id']), 'explored_unmatched' if any(i['id'] in a['indicator_ids'] and a['evidence_id'] in {m['id'] for m in self.active_evidence()} for a in self.annotations) else 'not_explored'),
                        'evidence_ids': [a['evidence_id'] for a in self.annotations if i['id'] in a['indicator_ids'] and a['evidence_id'] in {m['id'] for m in self.active_evidence()}]} for i in self.bank['indicators']]},
                'stop_reason': self.stop_reason, 'failures': deepcopy(self.failures), 'observable_metrics': deepcopy(self.metrics),
                'limits': self.limits, 'overall_srl': None, 'retention': 'temporary_memory_download_required',
                'source_versions': {'interview_version': self.source_register['version'], 'interview_sources':self.source_register['sources'],
                                    'workbook_source':self.bank['source'], 'bank_version':self.bank.get('bank_version')}}
