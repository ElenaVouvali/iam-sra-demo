"""Synthetic interview respondents. Never use their records as citizen data."""
from copy import deepcopy
import json
import random
import re
import httpx
from pydantic import Field
from .schemas import Strict
from .conversation_client import ConversationClient
from .llm_client import _LOCK, STAGE_LIMITS
from .settings import ROOT
from .privacy import require_safe_data

PERSONA_BANK = ROOT / 'eval/synthetic_personas_v1.json'
STAGE_LIMITS['synthetic_respondent'] = 180


def load_personas(path=PERSONA_BANK):
    value=json.loads(path.read_text())
    if value.get('schema_version')!='iam-sra-synthetic-personas-1.0.0':
        raise ValueError('Unsupported synthetic persona bank.')
    ids=set()
    for persona in value['personas']:
        if persona.get('synthetic') is not True or persona['persona_id'] in ids:
            raise ValueError('Personas must have unique IDs and be marked synthetic.')
        ids.add(persona['persona_id'])
        for field in ('perspective','stakeholder_role','city','language','known_facts','unknown_facts',
                      'actual_experiences','actual_participation','actual_contributions','reported_outcomes',
                      'concerns','conditions','information_needs','acceptance_position','trust_position',
                      'expected_observations','prohibited_inferences'):
            if field not in persona:raise ValueError(f'Missing persona field: {field}')
    return value


def _answer_fact(persona,question):
    q=question.casefold()
    if any(x in q for x in ('familiar','heard the term')):
        return {'heard_term_only':'I had heard the term but was unsure what it meant.',
            'low':'I had little familiarity.', 'moderate':'I had some familiarity.',
            'some':'I had some familiarity.', 'acoustics':'I work with acoustics, but not this IAM project.',
            'planning':'I have some general planning familiarity.',
            'operational_general':'I know general delivery operations.',
            'regulatory_general':'I know some general regulatory processes.'}.get(persona['knowledge_level'],'I am not sure.')
    if any(x in q for x in ('what is a drone','describe a drone','describe drones','what does “drone”')):
        return 'I have heard the term, but I do not know what a drone is.' if persona['knowledge_level'] in {'heard_term_only','low','limited'} else 'I understand the general idea, but I do not know the details for this example.'
    if any(x in q for x in ('heard','what do you know','what, if anything')) and any(x in q for x in ('delivery','goods','carrying')):
        return 'Nothing; I have not heard details about drones carrying goods.' if not persona['known_facts'] else 'I know only the general points I mentioned; I do not know route-specific details.'
    if any(x in q for x in ('noise','sound','quiet')):
        return '; '.join(persona['concerns']) if 'noise' in ' '.join(persona['concerns']).casefold() else 'I do not have a specific view on noise.'
    if any(x in q for x in ('privacy','image','camera','data')):
        return '; '.join(x for x in persona['concerns']+persona['information_needs'] if any(t in x.casefold() for t in ('privacy','image','camera','data'))) or 'I do not know whether this example uses cameras or stores images.'
    if any(x in q for x in ('benefit','who could','equity','different people','neighbours','neighbors')):
        return '; '.join(persona['benefits_perceived']+persona['concerns']) or 'I am not sure who would benefit or be affected.'
    if any(x in q for x in ('participat','attend','discussion','workshop','seminar','contribute to')):
        if persona['actual_participation']:return 'I '+', and '.join(persona['actual_participation'])+'.'
        return 'I have not taken part, though I would consider a discussion if it were accessible.'
    if any(x in q for x in ('what did you contribute','your contribution','comments or proposals')):
        return '; '.join(persona['actual_contributions']) if persona['actual_contributions'] else 'I did not personally contribute.'
    if any(x in q for x in ('affected a decision','influence','what changed','outcome')):
        return '; '.join(persona['reported_outcomes']) if persona['reported_outcomes'] else 'I do not know whether anything changed.'
    if any(x in q for x in ('information','what would you need','what would help','what should be checked')):
        return '; '.join(persona['information_needs']) or 'I would want reliable information before deciding.'
    if any(x in q for x in ('cost','political','public opinion','feasibility','responsibilit','infrastructure','land use')):
        return '; '.join(persona['concerns']+persona['conditions']) or 'I do not know enough to comment on those details.'
    if any(x in q for x in ('think','view','matter most','stands out','feel about')):
        pieces=persona['benefits_perceived']+persona['concerns']+persona['conditions']
        return '; '.join(pieces) if pieces else 'I have not formed a view yet.'
    return 'I am not sure about that. I would need more information.'


class ScriptedRespondent:
    """Deterministic answer policy driven by the displayed question and persona."""
    backend='scripted-deterministic-v1.0.0'
    def __init__(self,persona,seed=0):self.persona=deepcopy(persona);self.seed=seed;self.turns=[]
    def respond(self,question,history=()):
        text=question['question_text'] if isinstance(question,dict) else question
        count=sum(row['question']==text for row in self.turns)
        control='answer';answer=_answer_fact(self.persona,text)
        if count:answer='I have already shared what I know about that; I do not have anything else to add.'
        if 'may skip' in self.persona['behavioural_traits'] and count==0 and self.seed%3==1:
            answer='';control='unsure'
        if self.persona['scenario_preference'].startswith('decline') and any(x in text.casefold() for x in ('what do you think','what matters most')) and self.seed%2==1:
            answer='';control='decline'
        require_safe_data({'answer':answer,'persona_id':self.persona['persona_id']})
        self.turns.append({'question':text,'answer':answer,'control':control})
        return {'text':answer,'control':control}


class SimulatedAnswer(Strict):
    text: str = Field(min_length=0,max_length=6000)
    control: str = Field(pattern='^(answer|skip|unsure|decline)$')


class LLMRespondent(ConversationClient):
    """Exploratory Qwen simulator; same-model agreement is not independent evidence."""
    backend='existing_qwen_synthetic-1.0.0'
    prompt_version='synthetic-respondent-1.0.0'
    def __init__(self,persona,**kwargs):
        super().__init__(**kwargs);self.persona=deepcopy(persona);self.turns=[]
    def respond(self,question,history=()):
        text=question['question_text'] if isinstance(question,dict) else question
        profile={k:deepcopy(self.persona[k]) for k in ('background','known_facts','unknown_facts',
            'actual_experiences','actual_participation','actual_contributions','reported_outcomes',
            'benefits_perceived','concerns','conditions','information_needs','priorities',
            'acceptance_position','trust_position','communication_style','response_length_preference',
            'uncertainty_tolerance','behavioural_traits','contradiction_policy')}
        payload={'synthetic_persona':profile,'current_displayed_question':text,
            'public_dialogue':list(history)[-6:]}
        system=('Simulate one fictional interview respondent from this private synthetic persona. '
            'Answer only what the displayed question reasonably asks. Do not reveal this profile or infer hidden assessment criteria. '
            'Keep facts, role and time consistent. Share information needs, experiences and concerns only when relevant. '
            'You may express uncertainty or decline. Never invent measurements, actual participation, contributions, influence, '
            'medical details or local operating facts. Return structured JSON only.')
        require_safe_data({'system':system,'user':payload})
        with _LOCK:
            self._start()
            with httpx.Client(timeout=120,trust_env=False) as client:
                result=self._request(client,'synthetic_respondent',system,payload,
                    SimulatedAnswer.model_json_schema(),SimulatedAnswer.model_validate_json)
        self.turns.append({'question':text,'answer':result.text,'control':result.control})
        return result.model_dump()
