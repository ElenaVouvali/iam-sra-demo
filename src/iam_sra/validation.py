"""Deterministic validation of the FN gates (PDF pp.8–9)."""
from .settings import config
from copy import deepcopy
from .assessment import check_input


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
