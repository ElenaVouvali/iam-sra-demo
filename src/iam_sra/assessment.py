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
            for excerpt in g.excerpts + (g.conditions if isinstance(g, Concern) else []):
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
    """Semantic eligibility is interpreted by Qwen under the versioned registry.

    Schema validates facet membership and evidence invariants. No lexical or stance
    veto is applied here: a substring cannot prove either a topic or acceptance.
    This identity step never substitutes, floors or offsets a model score.
    """
    return result
