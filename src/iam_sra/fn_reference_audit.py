"""Independent expected-branch audit for registered FN reference replays."""


def expected_goals(case, fixture, spec):
    fixture_flows=fixture.get('flows',fixture)
    flow=fixture_flows[case]
    rows={row['id']:row for row in flow}
    concerns=[]
    selected={topic.casefold() for row in flow if row['id']=='priorities' for topic in row.get('topics',[])}
    for row in flow:
        for topic in row.get('topics',[]):
            concerns.append({'topic':topic,'selected_priority':topic.casefold() in selected,
                             'spontaneously_raised':row['id'] in {'open_priorities','open_more','different_impacts'}})
    depth='short' if case.endswith('short') else 'extended'
    stages=spec['flows'][case]
    def applies(node):
        goal=node['id']
        if goal=='drone_explanation' and rows.get('drone_recognition',{}).get('answer_kind') in {'yes','partial'}:
            return rows.get('drone_description',{}).get('answer_kind') in {'uncertain','declined'}
        if not node.get('when'):
            return not node.get('optional')
        condition=node.get('when')
        if isinstance(condition,list):return all(applies({**node,'when':part}) for part in condition)
        if not condition or condition in {'boundary','aircraft_scope'}:return False
        if condition=='other_priority':
            selected_topics=[r['topic'].casefold() for r in concerns if r['selected_priority']]
            return any(t not in {'noise','fairness'} for t in selected_topics) and not any(t in {'noise','fairness'} for t in selected_topics)
        if condition.startswith('gap:'):return False
        if condition.startswith('asked:'):
            ref=rows.get(condition.split(':',1)[1],{})
            return bool(ref) and ref.get('answer_kind','substantive') not in {'no','uncertain','declined'}
        if ':' not in condition:return False
        source,wanted=condition.split(':',1)
        if source in {'topic','raised'}:
            return any(wanted in r['topic'].casefold() and
                       (r['selected_priority'] if source=='topic' else r['spontaneously_raised'])
                       for r in concerns)
        kind=rows.get(source,{}).get('answer_kind','unknown')
        if wanted=='yes':return kind in {'yes','partial'}
        if wanted=='yes_only':return kind=='yes'
        if wanted=='no':return kind in {'no','uncertain','partial','declined'}
        if wanted=='not_no':return kind!='no'
        return False
    return [node['id'] for stage in stages for node in stage['questions'] if applies(node)]


def audit(case,data,fixture,spec):
    fixture_flows=fixture.get('flows',fixture)
    conversation=data.get('conversation',data)
    expected=expected_goals(case,fixture,spec)
    actual={goal['id']:goal for stage in conversation.get('fn_interview',{}).get('stages',[])
            for goal in stage.get('goals',[])}
    all_goals={q['id'] for stage in spec['flows'][case] for q in stage['questions']}
    conditional_goals={q['id'] for stage in spec['flows'][case] for q in stage['questions']
                        if q.get('optional') or q.get('when')}
    optional_goals={q['id'] for stage in spec['flows'][case] for q in stage['questions'] if q.get('optional')}
    model_optional=set(conversation.get('fn_interview',{}).get('boundary_uncertainty',[])) & optional_goals
    presented={m.get('objective_id') for m in conversation.get('messages',[])
               if m.get('role')=='assistant' and m.get('objective_id') in all_goals}
    answered={m.get('objective_id') for m in conversation.get('messages',[])
              if m.get('role')=='respondent' and m.get('active',True) and m.get('objective_id') in all_goals}
    asked=presented
    covered_by_evidence_reuse={goal:sorted(set(row.get('evidence_ids',[])))
        for goal,row in actual.items() if goal in expected and goal not in presented
        and row.get('evidence_ids')}
    expected_set=set(expected);actual_set=set(actual)
    fixture_rows={row['id']:row for row in fixture_flows[case]}
    uncertainty=[]
    for goal,row in fixture_rows.items():
        if row.get('answer_kind') in {'uncertain','declined'}:
            observed=actual.get(goal,{}).get('status','not_asked')
            message=next((m for m in conversation.get('messages',[]) if m.get('role')=='respondent'
                          and m.get('objective_id')==goal and m.get('active',True)),None)
            annotation=next((a for a in conversation.get('annotations',[]) if message
                             and a.get('evidence_id')==message.get('id')), {})
            observed_kind=annotation.get('answer_kind')
            okay=(observed in {'unknown','declined','unresolved'} or observed_kind in {'uncertain','partial'}
                  if row['answer_kind']=='uncertain' else observed in {'declined','not_explored'})
            uncertainty.append({'goal':goal,'expected':row['answer_kind'],'observed_status':observed,
                                'observed_kind':observed_kind,'preserved':okay})
    exposure_rows=conversation.get('information_exposures',[])
    exposure_ids={e['id'] for e in exposure_rows}
    awareness_ids=set(actual.get('healthcare_awareness',{}).get('evidence_ids',[]))
    separation=bool(awareness_ids) and not (awareness_ids & exposure_ids) and all(
        e.get('prior_knowledge') is False for e in exposure_rows)
    return {'case':case,'expected_applicable_goals':expected,'asked_goals':sorted(asked),
        'expected_but_unasked':sorted(expected_set-presented),
        'expected_but_unasked_without_evidence_reuse':sorted(
            (expected_set-presented)-set(covered_by_evidence_reuse)),
        'expected_but_uncovered':sorted(expected_set-(actual_set|answered)),
        'covered_without_canonical_question':covered_by_evidence_reuse,
        'unexpectedly_triggered':sorted((presented & conditional_goals)-expected_set-model_optional),
        'model_triggered_optional_goals':sorted(model_optional & presented),
        'inapplicable_but_asked':sorted((conditional_goals-expected_set)&presented-model_optional),
        'correctly_inapplicable':sorted(conditional_goals-expected_set-presented-model_optional),
        'uncertainty_checks':uncertainty,'uncertainty_preserved':all(x['preserved'] for x in uncertainty),
        'information_exposure_ids':sorted(exposure_ids),'healthcare_prior_knowledge_not_exposure_id':separation,
        'result_status':(conversation.get('suggestion') or {}).get('status'),
        'result_level':(conversation.get('suggestion') or {}).get('level')}
