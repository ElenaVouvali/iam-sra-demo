"""Source identity, retrieval provenance and non-authority boundary checks."""
from iam_sra.chat_retrieval import retrieve_chat_context
from iam_sra.conversation_corpus import load_corpus


def test_rag_is_profile_contextual_bounded_and_provenance_preserving():
    collection=load_corpus()
    result=retrieve_chat_context(collection,'citizen','short','noise effects, measured levels and sleep',limit=2)
    assert result['status']=='retrieved'
    assert len(result['passages'])<=2
    assert all(row.get('source',{}).get('document') and row.get('source',{}).get('locator')
               and row.get('source',{}).get('sha256') for row in result['passages'])
    assert all(row.get('source_type')=='methodological_guidance' for row in result['guidance'])


def test_rag_unavailable_is_not_a_permission_or_interview_stop():
    result=retrieve_chat_context(None,'citizen','short','nesting birds and wildlife')
    assert result=={'guidance':[],'passages':[],'status':'corpus_unavailable'}
