import json
import os
import streamlit as st
from iam_sra.session import Session, State
from iam_sra.settings import SCENARIO, CONCERNS, POLICY, MODEL, BASE_URL, REGISTRY, config
from iam_sra.scoring import aggregate
from iam_sra.llm_client import LLMClient
from iam_sra.assessment import AssessmentError
from iam_sra.validation import conclusions
st.set_page_config(page_title="IAM · Research demo", page_icon="◈", layout="centered")
st.title("IAM · A citizen perspective")
st.caption("Experimental scenario assessment · English · No scientifically calibrated scores")
mock=os.getenv("IAM_MOCK","0")=="1"
if mock:
    st.warning("MOCK MODE — fixed uncertain fixture for UI/CI; no Qwen inference.")
    from iam_sra.mock import assess
else:
    assess=LLMClient()
if "session" not in st.session_state: st.session_state.session=Session()
s=st.session_state.session
st.button("Reset session",on_click=st.session_state.clear)
steps=list(State)
st.progress((steps.index(s.state)+1)/len(steps),text=s.state.value.replace("_"," ").title())
with st.chat_message("assistant"):
    st.subheader(SCENARIO["title"])
    st.write(SCENARIO["text"])
    st.caption("All route details and subsequent modifications are hypothetical assumptions.")
if s.text:
    with st.chat_message("user"):
        st.text(s.text)
def show(a,title):
    st.subheader(title)
    for name,label in [("awareness_understanding","Awareness and understanding"),("medical_public_benefit_support","Medical/public benefit support"),("current_route_stance","Original-route stance")]:
        d=getattr(a,name); st.write(f"**{label}:** {d.interpretation}"); st.write(d.rationale)
        for e in d.excerpts: st.text(e)
    for c in a.concerns:
        if c.status=="assessed":
            st.write(f"**{CONCERNS[c.concern_id]['label']} · {c.score}/9 (provisional)**")
            for e in c.excerpts: st.text(e)
            st.write(c.rationale)
    with st.expander("Unassessed concerns and ambiguity"):
        for c in a.concerns:
            if c.status=="unassessed" and c.excerpts:
                st.write(CONCERNS[c.concern_id]['label']+": unassessed · no score")
                for e in c.excerpts: st.text(e)
                st.write(c.rationale)
    if a.acceptance_conditions:
        st.write("**Conditions from the original answer**")
        for e in a.acceptance_conditions: st.text(e)
    totals=aggregate(a)
    st.write(f"Coverage: {totals['coverage']} concerns assessed")
    st.caption("Unassessed: "+", ".join(CONCERNS[i]['label'] for i in totals['missing']))
    st.write("Experimental scenario summary: "+(str(totals['rounded'])+"/9" if totals['rounded'] is not None else "Unavailable — insufficient concern evidence"))
    with st.expander("Arithmetic and phase coverage"): st.json(totals)
def perform(action, *args):
    st.session_state.pop("action_error", None)
    try:
        action(*args)
    except (AssessmentError, ValueError) as exc:
        st.session_state.action_error=str(exc)
def submit_answer():
    perform(s.submit, st.session_state.citizen_answer, assess)
def submit_correction():
    perform(s.correct, st.session_state.complete_original, st.session_state.correction_reason, assess)
def continue_session():
    perform(s.validate, st.session_state.interpretation_confirmed)
def submit_validation(qid):
    choice=st.session_state["choice_"+qid]
    if choice is None:
        st.session_state.action_error="Select a choice, including unsure if appropriate."
    else:
        perform(s.respond,choice,st.session_state["clarification_"+qid])
if st.session_state.get("action_error"):
    st.error(st.session_state.action_error)
if s.state==State.SCENARIO:
    st.button("Begin",on_click=perform,args=(s.begin,))
elif s.state==State.ANSWER:
    with st.form("answer"):
        st.text_area("Your response",key="citizen_answer",help="Maximum 4000 UTF-8 bytes; full prompt must also fit the context budget.")
        st.form_submit_button("Assess response",on_click=submit_answer)
elif s.state==State.INITIAL:
    show(s.original,"Original interpretation")
    if s.corrections: show(s.current,"Corrected interpretation")
    st.caption("Confirmation checks this interpretation, not measurement validity.")
    with st.expander("Correct the interpretation"):
        with st.form("correction"):
            st.text_area("Restate your complete original position",key="complete_original")
            st.text_input("What was misinterpreted?",key="correction_reason")
            st.form_submit_button("Record corrected version",on_click=submit_correction)
    st.checkbox("This interpretation reflects what I meant",key="interpretation_confirmed")
    st.button("Continue to hypothetical questions",on_click=continue_session)
elif s.state==State.VALIDATION:
    q=s.questions[len(s.responses)]
    st.subheader(f"Hypothetical question {len(s.responses)+1} of {len(s.questions)}")
    st.write(q["text"])
    st.caption("Consider only the stated hypothetical; you may retain multiple concerns.")
    with st.form("validation_"+q["id"]):
        st.radio("Your view",q["choices"],index=None,key="choice_"+q["id"])
        st.text_area("Optional clarification",key="clarification_"+q["id"])
        st.form_submit_button("Record and continue",on_click=submit_validation,args=(q["id"],))
else:
    show(s.original,"Original assessment — preserved")
    for c in s.corrections:
        st.write("Correction reason: "+c["reason"]); show(c["assessment"],"Corrected assessment")
    st.subheader("Conditional acceptance and remaining concerns")
    for r in s.responses:
        st.write(r["outcome"])
        if r["clarification"]: st.text(r["clarification"])
    st.write(conclusions(s.responses)["full_route_acceptance"])
    st.caption("No numerical validation update is justified. These outcomes do not replace original scores.")
    st.download_button("Export session JSON",json.dumps(s.export(),indent=2,ensure_ascii=False),file_name="iam-session.json",mime="application/json")
with st.expander("Developer metadata"):
    st.json({"mode":"mock" if mock else "live","model":config("model"),"endpoint":BASE_URL,"registry":REGISTRY['version'],"scenario":SCENARIO['version'],"scoring":POLICY['version'],"validation":config('validation')['version'],"prompt":config("prompts")["version"],"evidence_eligibility":config("evidence_eligibility")["version"],"context":4096,"max_output":1600})
    st.caption("In-memory session; raw citizen text is not written to routine logs. Explicit exports include citizen text.")
