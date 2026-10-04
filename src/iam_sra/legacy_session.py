"""Historical pre-confirmation session contract; regression tools only, never UI."""
from dataclasses import dataclass, field
from copy import deepcopy
from enum import Enum
from .assessment import check_input
from .schemas import Assessment, SCHEMA_VERSION
from .validation import select_questions, outcome, conclusions
from .scoring import aggregate
from .settings import REGISTRY, SCENARIO, POLICY, QUESTIONS, config
class State(str, Enum):
    SCENARIO="scenario"
    ANSWER="citizen_answer"
    INITIAL="initial_assessment"
    VALIDATION="validation"
    FINAL="final_report"
@dataclass
class Session:
    state: State = State.SCENARIO
    text: str = ""
    original: Assessment | None = None
    corrections: list = field(default_factory=list)
    responses: list = field(default_factory=list)
    confirmed: bool = False
    include_reference_questions: bool = False
    inference: dict = field(default_factory=dict)
    def begin(self):
        self._require(State.SCENARIO); self.state=State.ANSWER
    def submit(self, text, assessor):
        self._require(State.ANSWER); check_input(text)
        result=assessor(text)
        self.text=text; self.original=result.model_copy(deep=True)
        self.inference=inference_record(result,assessor)
        self.state=State.INITIAL
    def correct(self, text, reason, assessor):
        self._require(State.INITIAL)
        check_input(text); check_input(reason)
        result=assessor(text)
        self.corrections.append({"citizen_text":text,"reason":reason,"assessment":result.model_copy(deep=True),"inference":inference_record(result,assessor)})
    @property
    def current(self):
        return self.corrections[-1]["assessment"] if self.corrections else self.original
    def validate(self, confirmed, include_reference_questions=False):
        self._require(State.INITIAL); self.confirmed=bool(confirmed)
        self.include_reference_questions=bool(include_reference_questions)
        self.state=State.VALIDATION if self.questions else State.FINAL
    @property
    def questions(self):
        return list(QUESTIONS) if self.include_reference_questions else select_questions(self.current) if self.current else []
    def respond(self, choice, clarification=""):
        self._require(State.VALIDATION)
        self.responses.append(outcome(self.questions[len(self.responses)],choice,clarification))
        if len(self.responses)==len(self.questions): self.state=State.FINAL
    def export(self):
        self._require(State.FINAL)
        record={"experimental":True,"versions":{"schema":SCHEMA_VERSION,"registry":REGISTRY["version"],"scenario":SCENARIO["version"],"rubric":POLICY["rubric_version"],"scoring":POLICY["version"],"validation":config("validation")["version"],"prompt":config("prompts")["version"],"evidence_eligibility":config("evidence_eligibility")["version"],"model":config("model")},"citizen_text":self.text,"original":self.original.model_dump(),"original_aggregate":aggregate(self.original),"original_inference":self.inference,"original_profile":profile_record(self.original),"corrections":[{**c,"assessment":c["assessment"].model_dump(),"aggregate":aggregate(c["assessment"]),"profile":profile_record(c["assessment"])} for c in self.corrections],"interpretation_confirmed":self.confirmed,"include_reference_questions":self.include_reference_questions,"validation":self.responses,"conclusions":conclusions(self.responses,self.current)}
        return deepcopy(record)
    def _require(self, state):
        if self.state!=state: raise ValueError("Invalid session transition")


def inference_record(result, assessor):
    from copy import deepcopy
    return {"raw_model_scores":deepcopy(getattr(assessor,"last_raw_scores",{})),"candidate_projections":deepcopy(getattr(assessor,"last_candidate_projections",[])),"score_review_decisions":deepcopy(getattr(assessor,"last_score_decisions",[])),"application_derived_concern_scores":{},"score_policy":"No offset/substitution/rescoring of individual model scores; aggregate derived in Python only.","attempts":deepcopy(getattr(assessor,"last_diagnostics",[])),"raw_model_trace":deepcopy(getattr(assessor,"last_trace",[])),"settings":deepcopy(getattr(assessor,"last_settings",{})),"model":config("model")}

def profile_record(result):
    return {"construct":POLICY["aggregate_label"],"score_anchors":POLICY["anchors"],"concern_definitions":REGISTRY["concerns"],"mapping_decisions":[{"concern_id":c.concern_id,"status":c.status,"facets":c.facets,"mapping_note":c.mapping_note,"evidence":c.excerpts,"conditional_willingness":c.conditional_willingness,"unresolved_original_conditions":c.conditions,"score_anchor":POLICY["anchors"].get(str(c.score))} for c in result.concerns],"exclusions":[{"concern_id":c.concern_id,"reason":c.rationale,"mapping_note":c.mapping_note} for c in result.concerns if c.status=="unassessed"],"medical_benefit_counting":"Separate medical support interpretation; medical_public_benefit facet counts once within welfare_equity, never twice."}
