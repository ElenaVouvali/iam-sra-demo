"""Small local, allowlisted, lexical RAG prototype. No model-memory answers."""
import json
import math
import re
import time
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import httpx
from pydantic import Field
from .schemas import Strict
from .settings import ROOT, config
from .conversation_client import ConversationClient
from .llm_client import _LOCK, STAGE_LIMITS
from .assessment import AssessmentError

EXPLANATION_PROMPT_VERSION = 'retrieval-extractive-1.0.0'
STAGE_LIMITS['readiness_explanation'] = 600
STOP = set('a an the is are be this that what how about does do can could would of for and or in to at it my me i some actually known difference between'.split())


def tokens(text):
    words = [('scenario' if w == 'example' else w) for w in re.findall(r'[a-z0-9]+', text.casefold()) if w not in STOP]
    # Small documented plural normalisation, independent of any assessment case.
    return [w[:-3] + 'y' if w.endswith('ies') and len(w)>4 else
            w[:-1] if w.endswith('s') and not w.endswith('ss') and len(w)>3 else w for w in words]


def corpus():
    return json.loads((ROOT / 'configs/readiness_corpus.json').read_text())


def corpus_hash(collection):
    return sha256(json.dumps(collection, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def retrieve(question, purpose='citizen_explanation', collection=None):
    c = collection or corpus()
    if purpose not in {'citizen_explanation', 'researcher_reference'}:
        raise ValueError('Unknown retrieval purpose.')
    if not question.strip() or len(question) > c['maximum_question_characters']:
        raise ValueError('Ask a short question of 1–300 characters.')
    rows = [p for p in c['passages'] if purpose in p['permitted_use'] and
            p['locale'] == 'en' and p['scenario_applicability'] == c['use_case_id']]
    query = set(tokens(question)); docs = [Counter(tokens(p['text'] + ' ' + p['topic'])) for p in rows]
    average = sum(sum(d.values()) for d in docs) / max(1, len(docs))
    ranked = []
    for p, d in zip(rows, docs):
        matched = query & d.keys()
        score = 0.0
        for word in matched:
            df = sum(word in doc for doc in docs)
            idf = math.log(1 + (len(docs) - df + .5) / (df + .5))
            f = d[word]; score += idf * f * 2.2 / (f + 1.2 * (.25 + .75 * sum(d.values()) / average))
        if query & set(tokens(p['topic'])):
            score += 2.0  # Explicit topic metadata gets a small, deterministic boost.
        # Transparent minimum relevance gate, not a factual sufficiency oracle.
        if len(matched) >= 2:
            ranked.append(dict(deepcopy(p), retrieval_score=round(score, 5), matched_terms=sorted(matched)))
    return sorted(ranked, key=lambda p: (-p['retrieval_score'], p['id']))[:c['maximum_passages']]


class Excerpt(Strict):
    passage_id: str
    quotation: str = Field(min_length=1, max_length=800)


class Composition(Strict):
    excerpts: list[Excerpt] = Field(min_length=1, max_length=3)


def validate_composition(raw, passages):
    value = Composition.model_validate_json(raw)
    supplied = {p['id']: p for p in passages}
    for item in value.excerpts:
        if item.passage_id not in supplied or item.quotation not in supplied[item.passage_id]['text']:
            raise AssessmentError('Explanation must quote a supplied passage exactly.', code='evidence')
        text = supplied[item.passage_id]['text']; start = text.index(item.quotation)
        prefix = text[:start].rstrip(); suffix = text[start + len(item.quotation):]
        if (prefix and prefix[-1] not in '.!?') or item.quotation[-1] not in '.!?' or (suffix and not suffix[0].isspace()):
            raise AssessmentError('Quote complete sentences so negation and qualifiers cannot be dropped.', code='evidence')
    return value


class ExplanationClient(ConversationClient):
    prompt_version = EXPLANATION_PROMPT_VERSION

    def compose(self, question, passages):
        with _LOCK:
            self._start()
            system = (ROOT / 'prompts/readiness-explanation.txt').read_text()
            schema = Composition.model_json_schema()
            schema['$defs']['Excerpt']['properties']['passage_id'] = {'type':'string', 'enum':[p['id'] for p in passages]}
            with httpx.Client(timeout=120, trust_env=False) as http:
                return self._request(http, 'readiness_explanation', system,
                    {'question':question, 'source_data':[{'id':p['id'], 'text':p['text']} for p in passages]},
                    schema, lambda raw:validate_composition(raw, passages))


def explain(question, client=None, *, purpose='citizen_explanation', collection=None):
    """Model composes exact sourced excerpts; fallback cannot invent prose facts."""
    c = collection or corpus(); started = time.monotonic()
    passages = retrieve(question, purpose, c)
    result = {'schema_version':'1.0.0', 'question':question, 'purpose':purpose,
        'corpus_version':c['version'], 'corpus_sha256':corpus_hash(c),
        'review_status':c['review_status'], 'approved_by':c['approved_by'],
        'label':'Draft demo explanation · awaiting FN review',
        'status':'unavailable', 'excerpts':[], 'passages':passages,
        'notice':'Only the supplied collection is used. These excerpts may not fully answer your question. No verified engineering guarantees or local policies are supplied.',
        'model_used':False, 'prompt_version':EXPLANATION_PROMPT_VERSION,
        'prompt_sha256':sha256((ROOT/'prompts/readiness-explanation.txt').read_bytes()).hexdigest(),
        'model_provenance':deepcopy(config('model')), 'diagnostics':[], 'error':None}
    if not passages:
        result['notice'] = 'This collection has no sufficiently relevant passage for that question. Local policies, measurements and service guarantees are unknown unless explicitly documented; no answer from model memory is supplied.'
    else:
        try:
            if client is None: raise ValueError('No explanation model is configured.')
            result['model_used'] = True
            composition = client.compose(question, passages)
            composition = validate_composition(composition.model_dump_json(), passages)
            result.update(status='sourced_extracts', excerpts=[e.model_dump() for e in composition.excerpts])
        except (AssessmentError, httpx.HTTPError, ValueError, KeyError) as exc:
            result.update(status='sourced_fallback', error=type(exc).__name__,
                excerpts=[{'passage_id':p['id'], 'quotation':p['text']} for p in passages],
                notice='We could not compose an answer. Relevant sourced excerpts are shown instead; they may not fully answer your question.')
        result['diagnostics'] = deepcopy(getattr(client, 'last_diagnostics', []))
    result['latency_seconds'] = round(time.monotonic()-started, 3)
    return result
