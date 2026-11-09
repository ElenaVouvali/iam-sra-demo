"""Bounded, source-checked context retrieval for open-ended IAM-SRA chat.

Retrieval informs the interviewer; it never selects or constrains a question.
The existing private corpus is reused and every returned passage retains its
source locator and source identity.
"""
from copy import deepcopy

from .conversation_corpus import explanation_collection, rank
from .privacy import require_safe_data
from .chat_policy import objectives, rubric


def retrieve_chat_context(collection, profile, depth, query, limit=3):
    if not collection:
        return {"guidance": [], "passages": [], "status": "corpus_unavailable"}

    # Interview guidance is a soft, profile-specific set of source-located
    # adaptations. It is deliberately not exposed as eligible question IDs.
    adapted = objectives(profile, depth) if profile else []
    guidance_records = [{
        "id": f"guidance:{row['id']}",
        "search_text": row["purpose"] + " " + row["question"],
        "purpose": row["purpose"],
        "question_example": row["question"],
        "source": deepcopy(row["source"]),
        "source_type": "methodological_guidance",
        "permitted_use": "Interviewing guidance only; not respondent evidence or scoring authority.",
    } for row in adapted]
    guidance = rank(query, guidance_records, limit=3) if guidance_records else []

    # Source-checked explanatory passages are the reusable RAG collection.
    # They are data, not system/developer instructions or respondent evidence.
    try:
        corpus = explanation_collection(collection)
        passages = rank(query, corpus["passages"], limit=limit)
    except (KeyError, TypeError, ValueError):
        passages = []
    for passage in passages:
        status = passage.get('source_status', '')
        passage['source_type'] = ('illustrative_example' if status in {'scenario_facts','historical_hypothesis'}
            else 'project_background' if status in {'draft_explanation','explanatory_proposal'}
            else 'source_context')
        # The corpus allowlist is authoritative for actual purpose.
        passage['permitted_use'] = deepcopy(passage.get('permitted_use', []))
    clean = {"guidance": guidance, "passages": passages,
             "status": "retrieved" if guidance or passages else "no_applicable_source"}
    require_safe_data(clean)
    return clean
