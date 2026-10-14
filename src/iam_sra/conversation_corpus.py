"""Small private, source-checked collections; metadata-filtered lexical retrieval."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import math
import subprocess
from pathlib import Path
from .settings import ROOT,config
from .privacy import require_clean,require_safe_data
from .readiness_retrieval import tokens


def load_corpus():
    path=ROOT/config('conversation')['corpus_path']
    if not path.is_file():raise ValueError('Prepare the local source collection with scripts/build-conversation-corpus.py before starting this mode.')
    value=json.loads(path.read_text())
    if value.get('version')!='conversation-corpus-1.1.0':raise ValueError('Rebuild the local collection with scripts/build-conversation-corpus.py for the updated conversation.')
    for name in ('baseline','conversation'):
        if value.get('configuration',{}).get(name)!=sha256((ROOT/'configs'/f'{name}.json').read_bytes()).hexdigest():
            raise ValueError('The local collection is out of date. Re-run scripts/build-conversation-corpus.py.')
    for source in value['sources']:
        p=ROOT/source['path']
        if not p.is_file() or sha256(p.read_bytes()).hexdigest()!=source['sha256']:
            raise ValueError('A supplied source changed or is unavailable. Rebuild and review the local collection.')
    known={s['document']:s['sha256'] for s in value['sources']}
    for record in value['questions']+value['scenarios']+value['explanations']+value.get('source_comparisons',[]):
        if record['source']['sha256']!=known.get(record['source']['document']):raise ValueError('Unknown collection source membership.')
    expected=config('scenario')
    from .conversation_sources import grant_scenarios
    ga_text=subprocess.check_output(['pdftotext','-layout',str(ROOT/'references/private/GA.pdf'),'-'],text=True)
    def source(document,locator):
        return {'document':document,'locator':locator,'sha256':known[document],
                'version':known[document],'source_status':'contract'}
    ga={c['id']:c for c in grant_scenarios(ga_text,config('baseline'),source)}
    if {c['id'] for c in value['scenarios']}!={expected['id'],*ga}:
        raise ValueError('Scenario collection membership differs from the source-checked cases.')
    for card in value['scenarios']:
        original=ga.get(card['id'])
        if original:
            if card!=original:raise ValueError('A grant scenario differs from its source-checked card.')
        elif card['facts']!=expected['illustrative_context'] or card['text']!=expected['text'].split(' How do you feel')[0]:
            raise ValueError('Scenario facts differ from the source-checked illustrative card.')
    require_safe_data(value['questions']);require_safe_data(value['scenarios']);require_safe_data(value['explanations']);require_safe_data(value.get('source_comparisons',[]))
    return value


def runtime_provenance(collection):
    files=[ROOT/'app.py',*sorted((ROOT/'src/iam_sra').glob('*.py')),
        *sorted((ROOT/'configs').glob('*.json')),*sorted((ROOT/'prompts').glob('*.txt')),
        ROOT/'scripts/build-conversation-corpus.py',ROOT/'scripts/smoke-baseline.py',
        ROOT/'eval/conversation_meeting_cases.json',ROOT/'eval/conversation_meeting_cases_v2.json',ROOT/'references/source-register.json']
    hashes={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in files}
    hashes['conversation_collection_canonical.json']=sha256(json.dumps(collection,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    try:
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True))
    except (OSError,subprocess.CalledProcessError):commit=None;dirty=None
    return {'code_commit':commit,'working_tree_dirty':dirty,'file_sha256':hashes,
        'code_snapshot_sha256':sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()}


def rank(query,records,limit=3):
    require_clean(query);require_safe_data(records)
    words=set(tokens(query))
    docs=[Counter(tokens(r['search_text'])) for r in records]
    average=sum(sum(d.values()) for d in docs)/max(1,len(docs)) or 1
    result=[]
    for record,doc in zip(records,docs):
        score=0.0
        for term in words & doc.keys():
            df=sum(term in other for other in docs)
            idf=math.log(1+(len(docs)-df+.5)/(df+.5))
            f=doc[term];score+=idf*f*2.2/(f+1.2*(.25+.75*sum(doc.values())/average))
        result.append((round(score,6),record['id'],record))
    return [dict(deepcopy(r),retrieval_score=score) for score,_,r in sorted(result,key=lambda x:(-x[0],x[1]))[:limit]]


def retrieve_questions(collection,eligible,perspective,role,query,stage,limit=3):
    allowed={(q['id'],q['variant_id']):q for q in eligible}
    rows=[r for r in collection['questions'] if r['stage']==stage and r['locale']=='en'
          and (r['question_id'],r['variant_id']) in allowed and perspective in r['applicability']['perspectives']
          and role in r['applicability']['roles'] and 'planner' in r['permitted_use']]
    chosen=rank(query,rows,limit)
    # Membership is authoritative; retrieval relevance never overrides prerequisites.
    return [dict(r,question=deepcopy(allowed[(r['question_id'],r['variant_id'])])) for r in chosen]


def retrieve_scenarios(collection,context,profile=None):
    rows=[r for r in collection['scenarios'] if context['perspective'] in r['applicability']['perspectives']
          and context['stakeholder_category'] in r['applicability']['roles'] and r['locale']==context['language']]
    topics={t for claim in (profile or {}).get('claims',[]) for t in claim.get('topic_ids',[])}
    city=context['city']
    return deepcopy(sorted(rows,key=lambda r:(-int(r.get('city')==city),
        -len(topics.intersection(r.get('topic_ids',[]))),-int(r['id']=='urban_medical_corridor'),r['id'])))


def retrieve_scenario(collection,context,profile=None):
    rows=retrieve_scenarios(collection,context,profile)
    return rows[0] if rows else None


def explanation_collection(collection,scenario_id='urban_medical_corridor'):
    c=deepcopy(config('readiness_corpus'))
    rows=[p for p in collection['explanations'] if p['scenario_applicability'] in {'all',scenario_id}]
    for p in (rows:=deepcopy(rows)):p['scenario_applicability']=scenario_id
    c.update(version=collection['version'],use_case_id=scenario_id,passages=rows)
    return c
