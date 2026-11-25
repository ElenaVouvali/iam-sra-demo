"""Conservative evidence-to-indicator candidates from official v4 definitions.

This is a small, inspectable concept-rule projection, not an assessment model.
It runs once at interview conclusion, does not affect CRL/ORL/TRL, and fails
closed for ambiguous or unsupported concerns. Every asserted candidate carries
an exact respondent quote and the registered bank provenance.
"""
import re

from .privacy import require_clean

VERSION = 1

# These rules encode combinations of concepts present in the official
# definitions, rather than ranking indicator names. Matching a phrase is only
# a candidate; the exact quote and rationale remain reviewable.
RULES = {
    'indicator-01': (r'\b(?:SUMP|sustainable urban mobility plan|(?:urban )?mobility plan)\b',
        'The answer explicitly concerns IAM inclusion or participation in an urban mobility plan.'),
    'indicator-02': (r'\b(?:landing (?:site|pad|area)|take[- ]off site|infrastructure siting|land[- ]use restriction|site suitability)\b',
        'The answer concerns a site, supporting infrastructure, or land-use compatibility.'),
    'indicator-03': (r'\b(?:energy (?:demand|use|consumption)|electricity use|emissions?|carbon footprint|life[- ]cycle (?:impact|emissions|assessment)|manufacturing emissions)\b',
        'The answer addresses energy or environmental emissions over the technology life cycle.'),
    'indicator-04': (r'\b(?:costs?|cost[- ]effectiveness|affordab(?:le|ility)|return on investment|\bROI\b|funding|business model|operating expenses|investment costs?)\b',
        'The answer addresses financial viability, funding, affordability, or operating/investment costs.'),
    'indicator-05': (r'\b(?:remote (?:areas?|clinics?|communities|patients?)|isolated (?:communities|clinics|areas?)|vulnerable groups?|essential (?:goods|services|medicine)|barriers? to (?:access|use)|accessible (?:service|delivery)|difficulty travelling)\b',
        'The answer concerns access to essential services for remote, isolated, or vulnerable groups.'),
    'indicator-06': (r'\b(?:multimodal|transport (?:chain|network|integration)|logistics chain|replace road (?:journeys?|trips?)|substitut(?:e|ion) for road|ground (?:journeys?|transport)|congestion|end[- ]to[- ]end (?:delivery|reliability))\b',
        'The answer concerns connection or substitution across transport/logistics modes or congestion.'),
    # Generic disturbance, low flights, or wildlife alone are not evidence of
    # acoustic effects. Require an explicit acoustic or human soundscape cue.
    'indicator-07': (r'\b(?:noise|sound levels?|acoustic(?:al)?|buzz(?:ing)?|loud(?:ness)?|decibels?|soundscape|flight frequency.{0,20}noise|noise.{0,35}(?:sleep|residents?|disturb|bother))\b',
        'The answer explicitly addresses acoustic effects, soundscapes, or noise-related responses.'),
    'indicator-08': (r'\b(?:visual (?:impact|pollution)|landscape|how (?:the )?(?:place|area|square|neighbourhood) looks|appearance of (?:the )?(?:drone|landing|site)|hover(?:ing)? over (?:the )?(?:square|homes?|neighbourhood|landmark)|visibility of (?:the )?(?:drone|pad))\b',
        'The answer concerns visible aircraft or infrastructure and its effect on landscapes or everyday experience.'),
    'indicator-09': (r'\b(?:camera.{0,60}(?:window|home|house|see|record)|(?:see|observe|look) into (?:my |their )?(?:window|home|house)|personal data|who (?:can|will) (?:see|access) (?:the )?(?:image|data|recording)|feel(?:s)? unsafe|personal safety|fear of (?:a )?(?:crash|collision)|close to (?:pedestrians?|people walking))\b',
        'The answer expresses an affected person’s privacy or perceived personal-safety concern.'),
    'indicator-10': (r'\b(?:cybersecurity|cyber[- ]attack|hack(?:ed|ing)?|data breach|encryption|access controls?|authentication|unauthori[sz]ed access|technical safety|system reliability|redundan(?:cy|t)|failure rates?|validated safety|data protection controls?)\b',
        'The answer concerns technical/operational safety, system reliability, cybersecurity, or data protection.'),
    'indicator-11': (r'\b(?:downwash|outwash|rotor wash|aircraft[- ]generated airflow|turbulence.{0,35}(?:site|landing|pedestrian|structure)|wind.{0,35}(?:landing|site|pedestrian|structure)|(?:landing|site).{0,35}wind)\b',
        'The answer links wind or aircraft-generated airflow to operational safety or site placement.'),
    'indicator-12': (r'\b(?:airspace capacity|air[- ]traffic management|airspace coordination|airspace separation|U[- ]space|routes? coordinated with (?:helicopters?|aircraft)|traffic grows|airspace (?:demand|constraints?))\b',
        'The answer concerns airspace/traffic-management capacity, coordination, or separation.'),
    'indicator-13': (r'\b(?:unequal(?:ly)? (?:distributed|shared)|disproportionate(?:ly)? (?:burden|impact)|disproportionately|distribution of (?:benefits|costs|risks)|benefits? go to .{0,60}burden|burden.{0,60}benefits?|unfair(?:ness)?|equity|who benefits and who bears|inclusive decision)\b',
        'The answer concerns distribution of benefits, costs, risks, wellbeing, or inclusive decisions.'),
    'indicator-14': (r'\b(?:public awareness|public familiarity|understand(?:ing)? of (?:capabilities|limitations|impacts)|trust in (?:the )?(?:authority|institution|operator|service)|transparent information|clear and trustworthy information|explain.{0,40}(?:comments?|feedback|decision)|accountability|public dialogue)\b',
        'The answer concerns public understanding, information quality, trust, dialogue, or accountability.'),
    'indicator-15': (r'\b(?:continuing training|staff training|training on (?:service|system|safety|limits)|skills gaps?|competence building|build(?:ing)? (?:staff )?skills|access to expertise|continuing learning|technical expertise)\b',
        'The answer concerns skills, expertise, training, or continuing learning.'),
}

AMBIGUOUS = {
    'indicator-09': r'\b(?:privacy|safety|safe|security)\b',
    'indicator-10': r'\b(?:privacy|safety|safe|security)\b',
}
NEGATED_TOPICS = {
    'indicator-02': r'\b(?:no|not|never|isn.t|is not|doesn.t|does not)\b.{0,30}\b(?:landing site|landing pad|infrastructure|landscape|appearance)\b|\b(?:landing site|landing pad|infrastructure|landscape|appearance)\b.{0,20}\b(?:not a concern|no concern|doesn.t matter)\b',
    'indicator-07': r'\b(?:not worried about|not concerned about|not a concern|no concern about|doesn.t bother|does not bother|noise is not|sound is not)\b.{0,25}\b(?:noise|sound|buzz|acoustic|decibel)?\b|\b(?:noise|sound|buzz|acoustic|decibel)\b.{0,25}\b(?:not a concern|no concern|doesn.t bother|does not bother)\b',
    'indicator-08': r'\b(?:no|not|never|isn.t|is not|doesn.t|does not)\b.{0,35}\b(?:visual impact|aircraft appearance|landscape|how .* looks)\b|\b(?:visual impact|aircraft appearance|landscape)\b.{0,20}\b(?:not a concern|no concern)\b',
    'indicator-09': r'\b(?:not worried about|not concerned about|not a concern|no concern about|privacy is not|personal safety is not)\b.{0,25}\b(?:privacy|personal safety|camera|observation)\b|\b(?:privacy|personal safety|camera)\b.{0,20}\b(?:not a concern|no concern|doesn.t worry)\b',
    'indicator-10': r'\b(?:not worried about|not concerned about|not a concern|no concern about|cybersecurity is not|cybersecurity is not what worries me)\b.{0,25}\b(?:cybersecurity|cyber[- ]attack|hacking|data breach|technical safety|system reliability)?\b',
}


def _negative(indicator_id, quote):
    if indicator_id=='indicator-07' and re.search(r'\bnoise[- ]?cancell?ing (?:microphone|headphones?|device)\b',quote,re.I):
        return True
    pattern=NEGATED_TOPICS.get(indicator_id)
    return bool(pattern and re.search(pattern,quote,re.I))


def project_concerns(concerns, messages, bank):
    """Return evidence-linked internal candidates; never a readiness judgment."""
    official={row['id']:row for row in bank.get('indicators',[])}
    if len(official)!=15 or set(official)!={f'indicator-{i:02d}' for i in range(1,16)}:
        return {'status':'unavailable','version':VERSION,'results':[],
                'reason':'The validated 15-indicator bank was unavailable.'}
    source={m['id']:m for m in messages if m.get('role')=='respondent' and m.get('active',True)
            and m.get('evidence_status')=='respondent_provided'}
    by_evidence={}
    for concern in concerns:
        for eid in concern.get('evidence_ids',[]):
            row=source.get(eid)
            if not row:continue
            entry=by_evidence.setdefault(eid,{'evidence_id':eid,'quote':row['text'],'topics':[],
                'spontaneously_raised':False,'suggested_by_interviewer':False,
                'selected_priority':False,'explored':False})
            topic=concern.get('topic')
            if topic and topic not in entry['topics']:entry['topics'].append(topic)
            for key in ('spontaneously_raised','suggested_by_interviewer','selected_priority','explored'):
                entry[key]=entry[key] or bool(concern.get(key))
    results=[]
    for eid,entry in by_evidence.items():
        quote=entry['quote'];matches=[]
        for iid,(pattern,rationale) in RULES.items():
            cue=re.search(pattern,quote,re.I)
            if cue and not _negative(iid,quote):
                row=official[iid]
                matches.append({'indicator_id':iid,'indicator_name':row['name'],
                    'status':'candidate_unreviewed','rationale':rationale,
                    'evidence_id':eid,'evidence_quote':quote,'matched_cue':cue.group(0)})
        ambiguous=[]
        if not matches:
            for iid,pattern in AMBIGUOUS.items():
                if re.search(pattern,quote,re.I) and not _negative(iid,quote):ambiguous.append(iid)
        status='candidate_unreviewed' if matches else 'ambiguous' if ambiguous else 'unmapped'
        entry.update(status=status,candidate_mappings=matches,
                     possible_indicator_ids=sorted(set(ambiguous)) if status=='ambiguous' else [])
        results.append(entry)
    result={'status':'available','version':VERSION,'bank_version':bank.get('bank_version'),
        'bank_sha256':bank.get('bank_sha256'),
        'mapping_role':'internal provisional concern projection; not readiness scoring or complete indicator assessment',
        'participant_reviewed':False,'results':results}
    validate_projection(result,source,official)
    return result


def validate_projection(value, evidence, indicators):
    if value.get('status')!='available':return value
    ids=set(indicators)
    seen=set()
    for row in value.get('results',[]):
        eid=row.get('evidence_id')
        if eid in seen or eid not in evidence or row.get('quote')!=evidence[eid]['text']:
            raise ValueError('Projection evidence must be an exact active respondent answer.')
        seen.add(eid)
        expected_status='candidate_unreviewed' if row.get('candidate_mappings') else 'ambiguous' if row.get('possible_indicator_ids') else 'unmapped'
        if row.get('status')!=expected_status:raise ValueError('Projection status conflicts with its candidate rows.')
        for mapping in row.get('candidate_mappings',[]):
            if mapping.get('evidence_quote')!=row['quote']:
                raise ValueError('Projection candidate does not cite the exact respondent answer.')
            if mapping.get('indicator_id') not in ids or mapping.get('evidence_id')!=eid:
                raise ValueError('Projection candidate has unsupported source or indicator identity.')
            if not mapping.get('rationale') or not mapping.get('matched_cue') or mapping['matched_cue'] not in row['quote']:
                raise ValueError('Projection candidate rationale/cue is not grounded in source evidence.')
        if any(i not in ids for i in row.get('possible_indicator_ids',[])):
            raise ValueError('Ambiguous projection references an unknown indicator.')
    # Dynamic participant prose is screened in its own semantic field. Trusted
    # official IDs/version metadata are validated above against the bank and
    # must not be concatenated into prose for NER screening.
    for row in value.get('results',[]):
        require_clean(row['quote'])
        for topic in row.get('topics',[]):require_clean(topic)
        for mapping in row.get('candidate_mappings',[]):
            require_clean(mapping['rationale']);require_clean(mapping['matched_cue'])
    return value
