from dataclasses import dataclass, field
from enum import Enum
from .assessment import check_input
from .schemas import Assessment
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
    def begin(self):
        self._require(State.SCENARIO); self.state=State.ANSWER
    def submit(self, text, assessor):
        self._require(State.ANSWER); check_input(text)
        result=assessor(text)
        self.text=text; self.original=result.model_copy(deep=True); self.state=State.INITIAL
    def correct(self, text, reason, assessor):
        self._require(State.INITIAL)
        check_input(text); check_input(reason)
        result=assessor(text)
        self.corrections.append({"citizen_text":text,"reason":reason,"assessment":result.model_copy(deep=True)})
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
        return {"experimental":True,"versions":{"registry":REGISTRY["version"],"scenario":SCENARIO["version"],"rubric":POLICY["version"],"scoring":POLICY["version"],"validation":config("validation")["version"],"prompt":config("prompts")["version"],"evidence_eligibility":config("evidence_eligibility")["version"],"model":config("model")},"citizen_text":self.text,"original":self.original.model_dump(),"original_aggregate":aggregate(self.original),"corrections":[{**c,"assessment":c["assessment"].model_dump(),"aggregate":aggregate(c["assessment"])} for c in self.corrections],"interpretation_confirmed":self.confirmed,"include_reference_questions":self.include_reference_questions,"validation":self.responses,"conclusions":conclusions(self.responses,self.current)}
    def _require(self, state):
        if self.state!=state: raise ValueError("Invalid session transition")
