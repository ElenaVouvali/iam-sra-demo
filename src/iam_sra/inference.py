"""Shared inference audit snapshot for the current confirmed assessment flow."""
from .settings import config

def inference_record(result, assessor):
    from copy import deepcopy
    return {"raw_model_scores":deepcopy(getattr(assessor,"last_raw_scores",{})),"candidate_projections":deepcopy(getattr(assessor,"last_candidate_projections",[])),"score_review_decisions":deepcopy(getattr(assessor,"last_score_decisions",[])),"application_derived_concern_scores":{},"score_policy":"No offset/substitution/rescoring of individual model scores; aggregate derived in Python only.","attempts":deepcopy(getattr(assessor,"last_diagnostics",[])),"raw_model_trace":deepcopy(getattr(assessor,"last_trace",[])),"settings":deepcopy(getattr(assessor,"last_settings",{})),"model":config("model")}
