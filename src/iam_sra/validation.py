"""Deterministic validation of the FN gates (PDF pp.8–9)."""
from .settings import QUESTIONS, config
from copy import deepcopy
from .assessment import check_input

def select_questions(assessment):
    ids={c.concern_id for c in assessment.concerns if c.status=="assessed"}
    selected=[]
    for q in QUESTIONS:
        if not ids.intersection(q['relevant_concerns']):continue
        # The preserved Q1 wording presupposes opposition to the route. Do not
        # present that premise automatically to a supportive/unknown citizen.
        if q['id']=='q1':
            opposition=assessment.current_route_stance.interpretation in {'opposed','mixed'}
            privacy_objection=any(c.status=='assessed' and c.concern_id in q['relevant_concerns'] and c.position in {'opposed','mixed'} for c in assessment.concerns)
            if not (opposition and privacy_objection):continue
        selected.append(q)
    return selected

def outcome(question, choice, clarification=""):
    if choice not in question["choices"]: raise ValueError("Unknown choice")
    if clarification: check_input(clarification)
    index=question["choices"].index(choice)
    qid=question["id"]
    codes={"q1":["privacy_resolved","data_access_remaining","camera_presence_remaining","unresolved"],"q2":["bundle_accepted","visual_clutter_remaining","residential_routing_remaining","unresolved"],"q3":["medical_speed_priority","local_rights_priority","unresolved"]}
    messages={
      "q1":["Stated privacy concern resolved only under hypothetical shielding; full-route acceptance is not established.","Telemetry or cybersecurity access concern remains under the hypothetical shielding.","Camera-presence boundary remains under hypothetical shielding.","Unresolved: unsure / none of these."],
      "q2":["Conditional acceptance of the bundled altitude, sound and curfew modification; no single causal effect is identified.","Visual clutter remains a concern under the bundled modification.","Residential routing remains a concern under the bundled modification.","Unresolved: unsure / none of these."],
      "q3":["Policy preference: prioritize medical transit speed under the stated hypothetical trade-off.","Policy preference: prioritize neighborhood privacy and tranquility under the stated hypothetical trade-off.","Unresolved: unsure / none of these."]}
    return {"question_id":qid,"choice":choice,"code":codes[qid][index],"clarification":clarification,"outcome":messages[qid][index],"numerical_update":None,"validation_version":config("validation")["version"],"presented_question":deepcopy(question)}

def _code(response):
    # Existing in-memory sessions may contain pre-upgrade records without codes.
    if "code" in response: return response["code"]
    q=next(q for q in QUESTIONS if q["id"]==response["question_id"])
    return outcome(q,response["choice"])["code"]

def conclusions(responses, assessment=None):
    codes={r["question_id"]:_code(r) for r in responses}
    matches=[]; remaining=[]; resolved=[]
    if codes.get("q1")=="privacy_resolved": resolved.append("Privacy concern under the shielding assumption only.")
    if codes.get("q2")=="bundle_accepted": resolved.append("Acceptance of the noise/altitude/curfew bundle; changes were not tested independently.")
    concerns={"data_access_remaining":"Telemetry/cybersecurity data access", "camera_presence_remaining":"Physical camera presence", "visual_clutter_remaining":"Visual clutter", "residential_routing_remaining":"Routing over a residential area"}
    remaining.extend(concerns[c] for c in codes.values() if c in concerns)
    if codes.get("q1")=="privacy_resolved" and codes.get("q2")=="bundle_accepted":
        matches.append({"rule_id":"physical_adjustments_accepted","interpretation":"Both stated modifications are accepted. This supports conditional acceptance under those separate assumptions; it does not prove all original opposition was explained or establish full-route acceptance."})
    if any(c in concerns for q,c in codes.items() if q in {"q1","q2"}):
        matches.append({"rule_id":"remaining_objection","interpretation":"At least one objection remains after a proposed adjustment. Preserve each remaining concern; rejection does not establish irrationality, anti-technology bias or psychological mistrust."})
    if codes.get("q3")=="local_rights_priority":
        matches.append({"rule_id":"local_rights_priority","interpretation":"The citizen prioritizes local privacy/tranquility in this policy trade-off. This records a priority, not a numerical score or a personality diagnosis."})
    unresolved=[q for q,c in codes.items() if c=="unresolved"]
    tracking=concern_tracking(responses,assessment) if assessment is not None else []
    baseline=[r["concern_id"] for r in tracking if r["status"]=="untested" and r["original_position"] in {"opposed","mixed"}]
    source_rules={r["id"]:r for r in config("validation")["source_rules"]}
    for match in matches: match["source_reference"]=source_rules[match["rule_id"]]
    return {"conditional_outcomes":[r["outcome"] for r in responses],"matched_rules":matches,"resolved_under_hypotheses":resolved,"remaining_concerns":remaining,"untested_original_concerns":baseline,"concern_validation":tracking,"residential_routing":{"status":"remaining" if codes.get("q2")=="residential_routing_remaining" else "untested","question_id":"q2" if "q2" in codes else None,"scored_concern":False},"unresolved_questions":unresolved,"policy_preference":codes.get("q3"),"overlapping_source_outcomes":len(matches)>1,"full_route_acceptance":"Not inferred from separate hypothetical questions.","numerical_update":None,"note":"All applicable FN rules are retained together. They describe different hypotheticals; no precedence or numerical update formula is provided. Original scores are preserved."}


def concern_tracking(responses, assessment):
    """Track actual gates by facet, without silently rewriting original scores."""
    codes={r["question_id"]:_code(r) for r in responses}
    records=[]
    for c in assessment.concerns:
        if c.status!="assessed": continue
        tests=[]
        q1=codes.get("q1");q2=codes.get("q2");q3=codes.get("q3")
        if c.concern_id=="perceived_safety_privacy" and "personal_privacy" in c.facets and q1:
            status="resolved_under_assumptions" if q1=="privacy_resolved" else "unresolved" if q1=="unresolved" else "remaining"
            tests.append({"question_id":"q1","status":status,"facets":["personal_privacy"],"reason":"Shielding tests viewing private property only; other personal safety concerns are not tested."})
        if c.concern_id=="technical_safety_security_privacy" and "data_security" in c.facets and q1:
            status="remaining" if q1=="data_access_remaining" else "unresolved" if q1=="unresolved" else "partially_tested"
            tests.append({"question_id":"q1","status":status,"facets":["data_security"],"reason":"Camera shielding cannot establish technical/data-security assurance."})
        if c.concern_id in {"noise","visual_pollution"} and q2:
            if q2=="unresolved":status="unresolved"
            elif c.concern_id=="noise" and q2=="bundle_accepted":status="resolved_under_assumptions"
            elif c.concern_id=="visual_pollution" and q2=="visual_clutter_remaining":status="remaining"
            else:status="partially_tested"
            tests.append({"question_id":"q2","status":status,"facets":c.facets,"reason":"Bundled altitude/sound/curfew gate; a routing or visual objection does not independently resolve noise."})
        if c.concern_id=="welfare_equity" and "medical_public_benefit" in c.facets and q3:
            tests.append({"question_id":"q3","status":"unresolved" if q3=="unresolved" else "partially_tested","facets":["medical_public_benefit"],"reason":"Policy priority under hypothetical delay; does not establish distribution/equity or update welfare score."})
        status="untested"
        if tests:
            statuses={t["status"] for t in tests}
            status=next(s for s in ["remaining","unresolved","partially_tested","resolved_under_assumptions"] if s in statuses)
            tested_facets={f for t in tests for f in t["facets"]}
            if set(c.facets)-tested_facets and status=="resolved_under_assumptions":status="partially_tested"
        records.append({"concern_id":c.concern_id,"original_score":c.score,"original_position":c.position,"status":status,"tests":tests,"untested_facets":sorted(set(c.facets)-{f for t in tests for f in t["facets"]})})
    return records
