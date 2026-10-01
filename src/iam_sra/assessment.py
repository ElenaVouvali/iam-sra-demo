from .schemas import Assessment, Concern
from .settings import CONCERNS, MAX_INPUT_BYTES
class AssessmentError(ValueError):
    def __init__(self, message, code="input"):
        super().__init__(message)
        self.code=code
def check_input(text):
    if not text.strip() or len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise AssessmentError(f"Enter 1–{MAX_INPUT_BYTES} UTF-8 bytes; input is never truncated.")
def parse_assessment(raw, text):
    check_input(text)
    try:
        try:
            result = Assessment.model_validate_json(raw)
        except ValueError as exc:
            raise AssessmentError("Model output failed JSON/schema checks; no assessment was saved.", code="schema") from exc
        groups = list(result.concerns) + [result.awareness_understanding, result.medical_public_benefit_support, result.current_route_stance]
        for g in groups:
            for excerpt in g.excerpts:
                if not excerpt.strip() or excerpt not in text:
                    raise AssessmentError("Model output contains an unsupported evidence excerpt; no assessment was saved.", code="evidence")
        for condition in result.acceptance_conditions:
            if not condition.strip() or condition not in text:
                raise AssessmentError("Model output contains an unsupported acceptance condition; no assessment was saved.", code="evidence")
        present = {c.concern_id for c in result.concerns}
        result.concerns.extend(Concern(concern_id=i, status="unassessed", position="unassessed", score=None, excerpts=[], rationale="No explicit evidence assessed.") for i in CONCERNS if i not in present)
        return result
    except AssessmentError:
        raise
    except ValueError as exc:
        raise AssessmentError("Model output failed checks; no assessment was saved.",code="schema") from exc


def check_eligibility(result):
    from .settings import config
    eligibility=config("evidence_eligibility")
    patterns=eligibility["patterns"]
    for concern in result.concerns:
        if concern.status != "assessed": continue
        evidence=" ".join(concern.excerpts).casefold()
        if not any(term in evidence for term in patterns[concern.concern_id]):
            raise AssessmentError("Insufficient explicit topic evidence for "+concern.concern_id+"; no assessment saved.",code="eligibility")
        if concern.position == "supported" and not any(cue in evidence for cue in eligibility["support_cues"]):
            raise AssessmentError("Supported position lacks an explicit acceptance cue for "+concern.concern_id+"; no assessment saved.",code="eligibility")
    return result
