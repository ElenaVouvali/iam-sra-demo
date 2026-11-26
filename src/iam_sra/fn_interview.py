"""Small FN specification and evidence-aware routing, independent of the UI.

Coverage describes exploration, never a readiness level. All semantic claims
remain fallible annotations grounded in screened originals. No example-answer
matching, scoring formula, external tools or per-turn second model is used.
"""
from copy import deepcopy
from functools import lru_cache
import json
import re
from .settings import ROOT

VERSION = 'fn-adaptive-interview-1.1.0'


@lru_cache(maxsize=1)
def specification():
    data = json.loads((ROOT / 'configs/fn_interview.json').read_text())
    if data['version'] != VERSION:
        raise ValueError('Unsupported FN interview specification.')
    for stages in data['flows'].values():
        ids = [q['id'] for stage in stages for q in stage['questions']]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate FN evidence goals.')
    return data


def flow_key(profile, depth):
    return 'citizen_' + depth if profile == 'citizen' else profile


def literal_answer(text):
    """Fast path for explicit choices only; qualified answers go to Qwen."""
    value = text.strip().casefold().rstrip('.!')
    if re.fullmatch(r'(yes|yes please|yes i do|yes i have|i do|i have|go ahead|okay|ok)', value): return 'yes'
    if re.fullmatch(r'(no|not really|none|nothing|no thanks|no thank you)', value): return 'no'
    if re.fullmatch(r"(unsure|uncertain|not sure|i (?:do not|don.t) know|not that i know of|unknown|prefer not to say)", value): return 'uncertain'
    if re.fullmatch(r'(partly|partially|not completely|only partly)', value): return 'partial'
    return None


def explicit_unknown_drone_description(answer):
    """Recognise explicit inability; do not grade correctness or general knowledge."""
    value = ' '.join(answer.casefold().split())
    # Preserve an explicit refusal, even if the person also says
    # that they cannot describe the concept.
    if re.search(
        r"\b(?:prefer not to answer|rather not answer|"
        r"don't want to answer|do not want to answer|"
        r"decline to answer|refuse to answer)\b", value
    ):
        return False
    # A meaningful definition in the same response takes precedence.
    if re.search(r'\b(?:aircraft|unmanned|pilotless|without (?:a|an|the) pilot|flying (?:machine|device|vehicle))\b', value):
        return False
    return bool(re.search(
        r"\b(?:(?:do\s+not|don't|can't|cannot)\s+(?:really\s+)?(?:know\s+how\s+to\s+)?(?:describe|define|explain)\s+(?:it|them|(?:a\s+|the\s+)?drones?)\b|"
        r"(?:do\s+not|don't)\s+know\s+what\s+(?:(?:a\s+)?drones?\s+(?:is|are)|(?:it|they)\s+(?:is|are|means?))\b|"
        r"(?:not\s+sure|unsure)\s+how\s+to\s+(?:describe|define|explain)\s+(?:it|them|(?:a\s+|the\s+)?drones?)\b)",
        value))


def tentative_local_operation_report(answer):
    """Detect a tentative reported basis without asserting a verified operation."""
    value=' '.join(answer.casefold().split())
    reported=bool(re.search(r'\b(?:i think|i heard|i remember hearing|i may have heard|'
                            r'there (?:may|might|could) have been|possibly there (?:was|were))\b',value))
    activity=bool(re.search(r'\b(?:test(?:s|ed|ing)?|trial(?:s)?|demonstrat(?:ion|ions|ed)|'
                            r'operation(?:s|al)?|service(?:s)?|flight(?:s)?)\b',value))
    uncertain=bool(re.search(r'\b(?:not sure|unsure|uncertain|might|may|possibly|think|could)\b',value))
    if re.search(r'\b(?:no|not|never|haven.t|hasn.t|didn.t|don.t)\s+'
                 r'(?:(?:any|a|the|been|local|actual|confirmed)\s+){0,3}'
                 r'(?:tests?|trials?|demonstrat\w*|operations?|services?|flights?)\b',value) or re.search(
                 r'\b(?:don.t|do not) think (?:there )?(?:have been|was|were)\b[^.!?]{0,30}'
                 r'\b(?:tests?|trials?|demonstrat\w*|operations?|services?|flights?)\b',value):
        return False
    if re.search(r'\b(?:another|different|other) (?:city|area|region)|elsewhere|not here\b',value):
        return False
    return reported and activity and uncertain


def explicit_answer_uncertainty(answer):
    """Preserve clear uncertainty markers that coexist with tentative content."""
    value=' '.join(answer.casefold().split())
    if re.match(r'\bno\b[,. ]+i (?:do not|don.t) know\b|\bno\b[,. ]+i am not sure\b',value):
        return 'uncertain'
    marker=re.match(r"\b(?:i (?:do not|don't) know exactly|i am not sure|i'm not sure|not sure|uncertain)\b",value)
    if not marker:return None
    tail=value[marker.end():].strip(' .,:;!?')
    # A bare uncertainty is unknown; a meaningful qualified guess is partial.
    meaningful=[w for w in re.findall(r"[a-z']+",tail) if w not in {'i','am','is','are','was','were','do','not','dont','know','think','maybe','perhaps','the','a','an','it','they','about','how','what','whether','exactly'}]
    return 'partial' if len(meaningful)>=3 else 'uncertain'


class FNInterview:
    def __init__(self):
        from .adaptive_interview import interview_strategy
        self.version = VERSION
        self.strategy = interview_strategy()
        self.coverage = {}
        self.facts = {}
        self.asked = []
        self.unresolved_gaps = []
        self.boundary_uncertainty = []
        self.followups = {}
        self.boundary_probes = 0
        self.next_action = 'canonical'

    def stages(self, profile, depth):
        return specification()['flows'].get(flow_key(profile, depth), [])

    def nodes(self, profile, depth):
        return [q for stage in self.stages(profile, depth) for q in stage['questions']]

    def current(self, profile, depth, objective):
        return next((q for q in self.nodes(profile, depth) if q['id'] == objective), None)

    def stage_for(self, profile, depth, objective):
        return next((s for s in self.stages(profile, depth) if any(q['id'] == objective for q in s['questions'])), None)

    def record(self, goal, evidence_id, status, kind='substantive'):
        previous = self.coverage.get(goal, {})
        ids = list(dict.fromkeys(previous.get('evidence_ids', []) + ([evidence_id] if evidence_id else [])))
        self.coverage[goal] = {'status': status, 'evidence_ids': ids}
        self.facts[goal] = kind
        if status in {'unknown', 'declined', 'unresolved'} and goal not in self.unresolved_gaps:
            self.unresolved_gaps.append(goal)
        elif status == 'explored' and goal in self.unresolved_gaps:
            self.unresolved_gaps.remove(goal)

    def applicable(self, node, concerns):
        # In the model-led flow, FN's optional profile-specific topic menu is
        # still offered after an open discussion with no participant concern.
        # "Nothing else comes to mind" closes further spontaneous probing; it
        # does not mean the respondent has seen FN's suggested topics yet.
        if (self.strategy == 'model_led_fn' and node.get('id') == 'suggested_topics'
                and self.facts.get('topic_scope_closed')):
            return True
        # A citizen may recognise the term without being able to describe it.
        # Offer the existing FN explanation after the prior-knowledge probes.
        if (node.get('id') == 'drone_explanation'
                and self.facts.get('drone_recognition') in {'yes', 'partial'}):
            return self.coverage.get('drone_description', {}).get('status') == 'unknown'
        if node.get('id') in {'open_more','suggested_topics'} and self.facts.get('topic_scope_closed'):
            return False
        condition = node.get('when')
        if isinstance(condition, list):
            return all(self.applicable({**node,'when':part},concerns) for part in condition)
        if not condition:
            return not node.get('optional') or node['id'] in self.boundary_uncertainty
        if condition == 'boundary':
            return node['id'] in self.boundary_uncertainty
        if condition == 'aircraft_scope':
            return bool(self.facts.get('aircraft_scope'))
        if condition == 'other_priority':
            return any(row.get('selected_priority') and row['topic'].casefold() not in {'noise', 'fairness'} for row in concerns) and not any(row.get('selected_priority') and row['topic'].casefold() in {'noise','fairness'} for row in concerns)
        source, value = condition.split(':', 1)
        if source == 'gap': return value in self.boundary_uncertainty
        if source == 'asked': return ((value in self.asked or
                                      (self.strategy == 'model_led_fn' and value in self.coverage))
                                     and self.coverage.get(value, {}).get('status')=='explored'
                                     and self.facts.get(value) not in {'no','uncertain','declined'})
        if source in {'topic', 'raised'}:
            return any(value in row['topic'].casefold() and (row.get('selected_priority') if source == 'topic' else row.get('spontaneously_raised')) for row in concerns)
        kind = self.facts.get(source)
        if value == 'yes': return kind in {'yes', 'partial'}
        if value == 'yes_only': return kind == 'yes'
        if value == 'no': return kind in {'no', 'uncertain', 'partial', 'declined'}
        if value == 'not_no': return kind != 'no'
        return False

    def next(self, profile, depth, concerns):
        for node in self.nodes(profile, depth):
            if node['id'] in self.coverage:
                continue
            if self.applicable(node, concerns):
                return node
        return None

    def snapshot(self, profile, depth, objective, scope, concerns, model_led_active=None):
        from .adaptive_interview import enabled
        node = self.current(profile, depth, objective)
        stage = self.stage_for(profile, depth, objective)
        stages = self.stages(profile, depth)
        model_led = (self.strategy == 'model_led_fn' if model_led_active is None
                     else self.strategy == 'model_led_fn' and bool(model_led_active))
        # Model-led mode receives compact goal purposes/state, not canonical
        # participant questions or the underlying FN source documents.
        if model_led:
            allowed={q['id']:s['id'] for s in stages for q in s['questions']}
        else:
            allowed={}
            for current_stage in stages:
                for q in current_stage['questions']:
                    baseline_allowed=(not enabled() and (current_stage is stage or q is current_stage['questions'][0] or q['id']=='priorities'))
                    adaptive_allowed=bool(enabled() and (
                        current_stage is stage or
                        (profile=='citizen' and stage and stage['id']=='recognition' and q['id']=='healthcare_awareness') or
                        (profile!='citizen' and q is current_stage['questions'][0])))
                    if baseline_allowed or adaptive_allowed:
                        allowed[q['id']]=current_stage['id']
        result = {'version': VERSION, 'stage': (stage or {}).get('id'),
                'evidence_goal': (node or {}).get('id'), 'purpose': (stage or {}).get('purpose'),
                'response_type': (node or {}).get('response_type'),
                'allowed_objectives': allowed,
                'optional_goals': [q['id'] for s in stages for q in s['questions'] if q.get('optional')],
                'selected_priorities': [r['topic'] for r in concerns if r.get('selected_priority')],
                'known_topics': [{'topic':r['topic'],'selected':bool(r.get('selected_priority'))}
                                 for r in concerns if r.get('evidence_ids')][-8:],
                'covered_capabilities': {k: v['status'] for k,v in self.coverage.items() if k in allowed},
                'unresolved_gaps': self.unresolved_gaps[-6:],
                'boundary_uncertainty': self.boundary_uncertainty[:2],
                'scope': {k:v for k,v in scope.items() if v and k not in {'language','city_status'}},
                'next_action': self.next_action}
        if model_led:
            result['strategy']='model_led_fn'
            result['model_led_active']=True
            def disposition(question):
                goal=question['id'];row=self.coverage.get(goal)
                if not self.applicable(question,concerns):return 'not_applicable'
                if row is None:return 'not_explored'
                if row.get('status')=='provided':return 'provided'
                if row.get('status')=='declined':return 'declined'
                if row.get('status') in {'unknown','unresolved'}:return 'uncertain'
                if self.facts.get(goal)=='no':return 'explored_negative'
                return 'supported'
            result['stage_ledger'] = [{
                'stage_id':s['id'], 'purpose':s.get('purpose',''),
                'goals':[{'goal_id':q['id'], 'applicable':self.applicable(q,concerns),
                    'status':self.coverage.get(q['id'],{}).get('status','not_explored'),
                    'coverage_state':disposition(q),
                    'evidence_ids':self.coverage.get(q['id'],{}).get('evidence_ids',[]),
                    'optional':bool(q.get('optional'))} for q in s['questions']]}
                for s in stages]
            for stage_row, stage in zip(result['stage_ledger'], stages):
                applicable = [q for q in stage['questions'] if self.applicable(q, concerns)]
                considered = [q for q in applicable if self.coverage.get(q['id'], {}).get('status')
                              in {'explored', 'unknown', 'declined', 'not_applicable', 'provided'}]
                stage_row['methodological_status'] = (
                    'not_applicable' if not applicable else
                    'considered' if considered else 'not_explored')
            candidates=self.model_led_next_objectives(profile,depth,concerns,objective)
            result['eligible_next_objectives']=[{'goal_id':q['id'],'stage_id':self.stage_for(profile,depth,q['id'])['id'],
                'purpose':q.get('purpose',''),'priority_relevance':self._priority_relevant(q,concerns)}
                for q in candidates]
            current=self.current(profile,depth,objective)
            current_status=self.coverage.get(objective,{}).get('status')
            result['eligible_current_follow_up']=(objective if current and self.applicable(current,concerns)
                and current_status not in {'explored','unknown','declined','not_applicable','provided','unresolved'}
                and self.followups.get(objective,0)<1 else None)
        return result

    @staticmethod
    def _priority_relevant(node, concerns):
        """Whether a registered goal can naturally explore a selected issue."""
        if not any(row.get('selected_priority') for row in concerns):
            return False
        condition=str(node.get('when','')).casefold()
        terms=('topic:', 'raised:')
        return any(term in condition for term in terms) or node.get('id') in {
            'priority_understanding','conditions','conditions_why','evaluation_evidence',
            'noise_understanding','privacy_understanding','equity_understanding'}

    def model_led_next_objectives(self, profile, depth, concerns, current_goal=None):
        """Return a bounded cross-stage choice set for model-led progression.

        Evidence annotation may still cite any registered allowed objective. This
        narrower list is solely for next-question planning and prevents proposals
        for closed, inapplicable, already-asked goals. Keep at least one useful
        choice per applicable stage, then use remaining slots for selected-
        priority-relevant objectives. Python does not choose the next stage.
        """
        considered={'explored','unknown','declined','not_applicable','provided','unresolved'}
        values=[]
        for node in self.nodes(profile,depth):
            goal=node['id']
            if goal==current_goal or goal in self.asked:
                continue
            if not self.applicable(node,concerns):
                continue
            if self.coverage.get(goal,{}).get('status') in considered:
                continue
            values.append(node)
        if len(values)<=16:return values
        stage_order={stage['id']:i for i,stage in enumerate(self.stages(profile,depth))}
        node_order={node['id']:i for i,node in enumerate(self.nodes(profile,depth))}
        grouped={}
        for node in values:
            grouped.setdefault(self.stage_for(profile,depth,node['id'])['id'],[]).append(node)
        # Preserve choice across stages; within each stage expose the most
        # priority-relevant available objective first, without forcing it.
        selected=[]
        for stage_id,stage_nodes in grouped.items():
            stage_nodes.sort(key=lambda node:(not self._priority_relevant(node,concerns),
                                               node_order[node['id']]))
            selected.append(stage_nodes[0])
        remainder=[node for node in values if node not in selected]
        remainder.sort(key=lambda node:(not self._priority_relevant(node,concerns),
            stage_order[self.stage_for(profile,depth,node['id'])['id']],node_order[node['id']]))
        selected.extend(remainder[:max(0,16-len(selected))])
        return sorted(selected,key=lambda node:node_order[node['id']])

    def model_led_ready(self, profile):
        """Leave profile-specific onboarding and scope establishment stable."""
        covered=set(self.coverage)
        if profile == 'citizen':
            return 'area' in covered and ('drone_recognition' in covered or 'drone_explanation' in covered)
        if profile == 'organisational':
            return {'organisation_context','remit'} <= covered
        if profile == 'technical':
            return {'technical_role','technical_object','expertise'} <= covered
        return False

    def model_led_gaps(self, profile, depth, concerns):
        """Return uncovered applicable objectives for model-selected follow-up.

        These are opportunities for useful probing, not a mandatory question
        queue. A documented unresolved goal is not auto-asked repeatedly; it
        remains visible in unresolved_gaps and is not positive evidence. Completion is assessed at FN stage level by
        :meth:`model_led_unconsidered_stages`.
        """
        gaps=[]
        for stage in self.stages(profile,depth):
            for current in stage['questions']:
                if self.applicable(current,concerns):
                    row=self.coverage.get(current['id'])
                    if row is None or row.get('status') not in {'explored','unknown','declined','not_applicable','provided','unresolved'}:
                        gaps.append(current['id'])
        return gaps

    def model_led_unconsidered_stages(self, profile, depth, concerns):
        """Stages with no applicable goal explored, dispositioned, or documented unresolved."""
        remaining=[]
        considered_statuses={'explored','unknown','declined','not_applicable','provided','unresolved'}
        for stage in self.stages(profile,depth):
            applicable=[q for q in stage['questions'] if self.applicable(q,concerns)]
            if not applicable:
                continue
            if not any(self.coverage.get(q['id'],{}).get('status') in considered_statuses
                       for q in applicable):
                remaining.append(stage)
        return remaining

    def invalidate(self, active_ids):
        """Corrections remove dependent coverage, never retain superseded support."""
        removed=[]
        if self.facts.get('topic_scope_evidence_id') not in active_ids:
            self.facts.pop('topic_scope_closed',None)
            self.facts.pop('topic_scope_evidence_id',None)
        for goal, row in list(self.coverage.items()):
            if row['evidence_ids'] and not set(row['evidence_ids']) <= active_ids:
                del self.coverage[goal]
                self.facts.pop(goal, None)
                if goal in self.asked: self.asked.remove(goal)
                removed.append(goal)
        self.unresolved_gaps = [g for g in self.unresolved_gaps if g in self.coverage]
        return removed

    def export(self, profile, depth, concerns, model_led=False):
        stages=[]
        for stage in self.stages(profile, depth):
            applicable=[q for q in stage['questions'] if self.applicable(q, concerns)]
            methodological_status=(
                'not_applicable' if not applicable else
                'considered' if any(self.coverage.get(q['id'],{}).get('status')
                in {'explored','unknown','declined','not_applicable','provided','unresolved'} for q in applicable)
                else 'not_explored')
            stage_status=('not_applicable' if not applicable else
                'explored' if (model_led and methodological_status=='considered')
                or all(q['id'] in self.coverage for q in applicable) else 'not_fully_explored')
            stages.append({'id':stage['id'],'source_locator':stage['source_locator'],
                'status':stage_status,
                'methodological_status':methodological_status if model_led else None,
                'goals':[{'id':q['id'], **deepcopy(self.coverage.get(q['id'],{'status':'not_explored','evidence_ids':[]}))} for q in applicable]})
        return {'version': VERSION, 'stages': stages, 'unresolved_gaps':list(self.unresolved_gaps),
                'boundary_uncertainty':list(self.boundary_uncertainty),
                'next_action':self.next_action,'coverage_is_readiness':False}
