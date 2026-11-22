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

VERSION = 'fn-adaptive-interview-1.0.0'


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


class FNInterview:
    def __init__(self):
        self.version = VERSION
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
        if source == 'asked': return (value in self.asked and self.coverage.get(value, {}).get('status')=='explored'
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

    def snapshot(self, profile, depth, objective, scope, concerns):
        node = self.current(profile, depth, objective)
        stage = self.stage_for(profile, depth, objective)
        stages = self.stages(profile, depth)
        # Only current-stage goals plus the primary goal of later stages. The
        # model sees capability purposes, not the complete question bank/PDFs.
        allowed = {q['id']: s['id'] for s in stages for q in s['questions']
                   if s is stage or q is s['questions'][0] or q['id']=='priorities'}
        return {'version': VERSION, 'stage': (stage or {}).get('id'),
                'evidence_goal': (node or {}).get('id'), 'purpose': (stage or {}).get('purpose'),
                'response_type': (node or {}).get('response_type'),
                'allowed_objectives': allowed,
                'optional_goals': [q['id'] for s in stages for q in s['questions'] if q.get('optional')],
                'selected_priorities': [r['topic'] for r in concerns if r.get('selected_priority')],
                'covered_capabilities': {k: v['status'] for k,v in self.coverage.items() if k in allowed},
                'unresolved_gaps': self.unresolved_gaps[-6:],
                'boundary_uncertainty': self.boundary_uncertainty[:2],
                'scope': {k:v for k,v in scope.items() if v and k not in {'language','city_status'}},
                'next_action': self.next_action}

    def invalidate(self, active_ids):
        """Corrections remove dependent coverage, never retain superseded support."""
        removed=[]
        for goal, row in list(self.coverage.items()):
            if row['evidence_ids'] and not set(row['evidence_ids']) <= active_ids:
                del self.coverage[goal]
                self.facts.pop(goal, None)
                if goal in self.asked: self.asked.remove(goal)
                removed.append(goal)
        self.unresolved_gaps = [g for g in self.unresolved_gaps if g in self.coverage]
        return removed

    def export(self, profile, depth, concerns):
        stages=[]
        for stage in self.stages(profile, depth):
            applicable=[q for q in stage['questions'] if self.applicable(q, concerns)]
            stages.append({'id':stage['id'],'source_locator':stage['source_locator'],
                'status':'explored' if all(q['id'] in self.coverage for q in applicable) else 'not_fully_explored',
                'goals':[{'id':q['id'], **deepcopy(self.coverage.get(q['id'],{'status':'not_explored','evidence_ids':[]}))} for q in applicable]})
        return {'version': VERSION, 'stages': stages, 'unresolved_gaps':list(self.unresolved_gaps),
                'boundary_uncertainty':list(self.boundary_uncertainty),
                'next_action':self.next_action,'coverage_is_readiness':False}
