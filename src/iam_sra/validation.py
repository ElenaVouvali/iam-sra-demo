from .settings import QUESTIONS
from .assessment import check_input
def select_questions(assessment):
    ids = {c.concern_id for c in assessment.concerns if c.status == "assessed"}
    return [q for q in QUESTIONS if ids.intersection(q["relevant_concerns"])]
def outcome(question, choice, clarification=""):
    if choice not in question["choices"]:
        raise ValueError("Unknown choice")
    if clarification:
        check_input(clarification)
    index = question["choices"].index(choice)
    qid = question["id"]
    unresolved = index == len(question["choices"])-1
    messages = {
      "q1": ["Stated privacy concern resolved only under hypothetical shielding; full-route acceptance is not established.", "Telemetry or cybersecurity access concern remains under the hypothetical shielding.", "Camera-presence boundary remains under hypothetical shielding."],
      "q2": ["Conditional acceptance of the bundled altitude, sound and curfew modification; no single causal effect is identified.", "Visual clutter remains a concern under the bundled modification.", "Residential routing remains a concern under the bundled modification."],
      "q3": ["Policy preference: prioritize medical transit speed under the stated hypothetical trade-off.", "Policy preference: prioritize neighborhood privacy and tranquility under the stated hypothetical trade-off."]}
    return {"question_id":qid,"choice":choice,"clarification":clarification,"outcome":"Unresolved: unsure / none of these." if unresolved else messages[qid][index],"numerical_update":None}
def conclusions(responses):
    return {"conditional_outcomes":[r["outcome"] for r in responses], "full_route_acceptance":"Not inferred from separate hypothetical questions.", "note":"Outcomes can coexist; each applies to its own hypothetical. Original scores are preserved."}
