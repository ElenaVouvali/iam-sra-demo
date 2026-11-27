"""Declared synthetic semantic double. Never imported by production routing."""
from iam_sra.fn_interview import literal_answer


def excerpt(text,limit):
    """Keep exact, bounded quotes without manufacturing a partial word/name."""
    if len(text)<=limit:return text
    boundary=text.rfind(' ',0,limit+1)
    return text[:boundary if boundary>0 else limit]


def reply(request, *, kind='substantive', status='explored', topics=(), action='advance', coverage=None, boundary=()):
    answer=request['answer'];eid=request.get('current_answer_id')
    goal=request.get('fn',{}).get('evidence_goal')
    return {'message':'What would you like to clarify about this point?', 'proposed_action':'ask_question',
        'interpretation': {'action':action, 'answer_kind':kind,'answer_quote':excerpt(answer,200),
            'coverage':coverage if coverage is not None else ([{'goal':goal,'evidence_id':eid,'quote':excerpt(answer,200),
                'status':status,'answer_kind':kind}] if eid else []),
            'topics':[{'topic':t,'quote':excerpt(answer,160)} for t in topics], 'boundary_goals':list(boundary)}}


class SyntheticInterpreter:
    def turn(self, request):
        answer=request['answer'];kind=literal_answer(answer) or 'substantive'
        lower=answer.casefold()
        if kind=='substantive' and request.get('fn',{}).get('response_type') in {'yes_no','permission'}:
            kind='uncertain'
        topics=[t for t in ('noise','privacy','fairness','wildlife','safety','landing') if t in lower]
        return reply(request,kind=kind,status='unknown' if kind=='uncertain' else 'explored',topics=topics)


class ScoreFixture:
    """Arbitrary selection tests result plumbing, NOT semantic scoring accuracy."""
    def __init__(self, index=3): self.index=index;self.calls=[]
    def match_profile(self,payload):
        self.calls.append(payload)
        assert len(payload['anchors'])==9
        quote=payload['originals'][-1]
        return {'selected_anchor_id':payload['anchors'][self.index]['id'],
                'alternative_anchor_id':payload['anchors'][self.index+1]['id'],
                'citations':[{'evidence_id':quote['id'],'quote':excerpt(quote['text'],120)}],
                'explanation':'Synthetic score transport fixture, not a methodological judgment.',
                'boundary':f"The respondent evidence does not demonstrate the {payload['anchors'][self.index+1]['label']} capability or related participation in this synthetic fixture.",
                'material_conflict':False,'evidence_incomplete':False}
