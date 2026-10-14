"""Session factory for the updated citizen interviews."""
def Session(*, assessment_mode="general_baseline", **kwargs):
    if assessment_mode == "general_baseline":
        from .baseline_session import BaselineSession
        return BaselineSession(**kwargs)
    if assessment_mode == "acceptance_and_readiness_evidence":
        from .readiness_session import ReadinessSession
        return ReadinessSession(**kwargs)
    if assessment_mode == "retrieval_grounded_conversation":
        from .conversation_session import ConversationSession
        return ConversationSession(**kwargs)
    raise ValueError("Unknown assessment mode; the historical demo is on the legacy branch.")
