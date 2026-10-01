"""Deterministic validation of the FN gates (PDF pp.8–9)."""
from .settings import QUESTIONS, config
from .assessment import check_input

def select_questions(assessment):
    ids={c.concern_id for c in assessment.concerns if c.status=="assessed"}
    return [q for q in QUESTIONS if ids.intersection(q["relevant_concerns"])]

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
    return {"question_id":qid,"choice":choice,"code":codes[qid][index],"clarification":clarification,"outcome":messages[qid][index],"numerical_update":None,"validation_version":config("validation")["version"]}

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
    baseline=[]
    if assessment is not None:
        tested={"perceived_safety_privacy","technical_safety_security_privacy","noise","visual_pollution"}
        baseline=[c.concern_id for c in assessment.concerns if c.status=="assessed" and c.position in {"opposed","mixed"} and c.concern_id not in tested]
    source_rules={r["id"]:r for r in config("validation")["source_rules"]}
    for match in matches: match["source_reference"]=source_rules[match["rule_id"]]
    return {"conditional_outcomes":[r["outcome"] for r in responses],"matched_rules":matches,"resolved_under_hypotheses":resolved,"remaining_concerns":remaining,"untested_original_concerns":baseline,"unresolved_questions":unresolved,"policy_preference":codes.get("q3"),"overlapping_source_outcomes":len(matches)>1,"full_route_acceptance":"Not inferred from separate hypothetical questions.","numerical_update":None,"note":"All applicable FN rules are retained together. They describe different hypotheticals; no precedence or numerical update formula is provided. Original scores are preserved."}
