from decimal import Decimal, ROUND_HALF_UP
from .settings import CONCERNS, POLICY
def aggregate(assessment, policy=None):
    p = policy or POLICY
    assessed = [c for c in assessment.concerns if c.status == "assessed"]
    scores = [c.score for c in assessed]
    phases = {}
    for phase in (1, 2, 3):
        vals = [c.score for c in assessed if CONCERNS[c.concern_id]["phase"] == phase]
        phases[str(phase)] = {"assessed": len(vals), "total": sum(c["phase"] == phase for c in CONCERNS.values()), "mean": sum(vals)/len(vals) if len(vals) >= p["phase_minimum_assessed"] else None}
    missing = [i for i in CONCERNS if i not in {c.concern_id for c in assessed}]
    mean = sum(scores)/len(scores) if len(scores) >= p["minimum_assessed"] else None
    eligible = [c.score for c in assessed if CONCERNS[c.concern_id]["phase"] in p["bottleneck_phases"] and c.score <= p["bottleneck_threshold"]]
    cap = min(eligible)+p["bottleneck_offset"] if p["bottleneck_enabled"] and eligible else None
    adjusted = min(mean, cap) if mean is not None and cap is not None else mean
    return {"mean":mean, "cap":cap, "adjusted":adjusted, "rounded":int(Decimal(str(adjusted)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) if adjusted is not None else None, "coverage":f"{len(scores)}/15", "missing":missing, "phases":phases, "policy_version":p["version"]}
