#!/usr/bin/env python3
"""Reproducible private demo collection. Never index transcripts or contact lists."""
import json
import argparse
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from iam_sra.settings import ROOT,config
from iam_sra.privacy import require_safe_data,PrivacyError
from iam_sra.conversation_sources import grant_scenarios,scenario_explanations


def workbook(path):
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with ZipFile(path) as z:
        strings=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)]
        sheets={}
        for i,name in enumerate(('Read me','SRA IAM indicators','Use case(s) per LL'),1):
            cells={}
            for c in ET.fromstring(z.read(f'xl/worksheets/sheet{i}.xml')).findall('.//m:c',ns):
                v=c.find('m:v',ns)
                if v is not None:cells[c.attrib['r']]=strings[int(v.text)] if c.attrib.get('t')=='s' else v.text
            sheets[name]=cells
        comments={}
        for key in z.namelist():
            if '/comments' in key and key.endswith('.xml'):
                for c in ET.fromstring(z.read(key)).iter():
                    if c.tag.endswith('}comment') and c.attrib.get('ref') in ('C8','D8','H8','J8'):
                        text=' '.join(c.itertext());comments[c.attrib['ref']]=text.split('Comment:')[-1].strip()
        return sheets,comments


def build(output=None):
    private=ROOT/'references/private';spec=config('conversation');base=config('baseline')
    names=['GA.pdf','IAM-CC_Topic_experts.xlsx','IAM-CC_UI_guidelines_for_tools.pdf',
           'WP3_IAM-CC_Minutes_20261008.docx','IAM-CC_WP3_2026.09.10.pptx','SRA_LLM_FN_concept.pdf']
    missing=[name for name in names if not (private/name).is_file()]
    if missing:raise ValueError('Missing original sources: '+', '.join(missing))
    sources=[];pdfs={}
    for name in names:
        p=private/name;entry={'document':name,'path':str(p.relative_to(ROOT)),'sha256':sha256(p.read_bytes()).hexdigest()}
        if p.suffix=='.pdf':
            text=subprocess.check_output(['pdftotext','-layout',str(p),'-'],text=True)
            pdfs[name]=text;entry['pages']=len([x for x in text.split('\f') if x.strip()])
        sources.append(entry)
    by_name={s['document']:s for s in sources}
    sheets,comments=workbook(private/names[1]);ind=sheets['SRA IAM indicators'];readme=sheets['Read me']
    reviewed_rows=(3,4,6,8,10,14,15,16)
    for key in [f'{col}{row}' for row in reviewed_rows for col in 'DI']+['H8','H15','H16','J2','J8']:
        if not ind.get(key):raise ValueError('Required workbook cell missing: '+key)
    if 'Task 3.3.' not in pdfs['GA.pdf'] or 'IAM-SRA2' not in pdfs['GA.pdf']:raise ValueError('GA extraction is incomplete.')
    if '60 meters' not in pdfs['SRA_LLM_FN_concept.pdf'] or '15 times' not in pdfs['SRA_LLM_FN_concept.pdf']:
        raise ValueError('FN source scenario facts could not be checked.')
    for anchor in config('readiness_levels')['crl']:
        if ' '.join(anchor['description'].split())!=' '.join(readme.get('L'+str(anchor['level']+4),'').split()):
            raise ValueError('Workbook anchors changed; review the existing provisional score module.')
    def source(document,locator):
        return {'document':document,'locator':locator,'sha256':by_name[document]['sha256'],
                'version':by_name[document]['sha256'],'source_status':'contract' if document=='GA.pdf' else 'historical_concept' if document=='SRA_LLM_FN_concept.pdf' else 'partner_draft'}
    questions=[]
    source_rows={'understanding':8,'reasoning':8,'familiarity':15,'delivery':15,'needs':15,'influence':15}
    for q in base['core_questions']+base['probes']:
        variants=dict(q['variants'])
        if q.get('when_exposure_already_reported'):variants['contribution_after_exposure']=q['when_exposure_already_reported']
        for variant,text in variants.items():
            perspectives=['organisation'] if variant.startswith('organisation') else ['personal','withheld'] if variant=='personal' else list(base['perspectives'])
            questions.append({'id':'general_'+q['id']+'_'+variant,'type':'question','stage':'general',
                'question_id':q['id'],'variant_id':variant,'target_criterion':q['dimension'] or 'scope','topic_ids':[],
                'applicability':{'perspectives':perspectives,'roles':q['applicable_roles']},'locale':'en',
                'original_wording':q['text'],'revised_wording':text,'wording_options':list(dict.fromkeys([text]+([spec['plain_variants'][q['id']]] if q['id'] in spec['plain_variants'] else []))),
                'source':source('IAM-CC_Topic_experts.xlsx',spec['source_locators'][q['id']]),
                'original_source_reference':spec['source_locators'][q['id']],
                'source_comparison_id':'workbook_row_'+str(source_rows.get(q['id'],16)),
                'derivation':'Existing prototype registry, reviewed against workbook definitions and corrective feedback; not FN-approved wording.',
                'review_status':'draft_pending_FN','permitted_use':['planner','researcher_reference'],
                'search_text':str(q['dimension'])+' '+q['target_requirement']+' '+text})
    for q in spec['scenario_questions']:
        for variant in ('personal','organisation'):
            questions.append({'id':q['id']+'_'+variant,'type':'question','stage':'scenario',
                'question_id':q['id'],'variant_id':variant,'target_criterion':q['criterion'],'topic_ids':q.get('topic_ids',[]),
                'applicability':{'perspectives':['organisation'] if variant=='organisation' else ['personal','withheld'],
                    'roles':list(base['stakeholders'])},'locale':'en','original_wording':q['personal'],
                'revised_wording':q[variant],'wording_options':list(dict.fromkeys([q[variant]]+([spec['plain_variants'][q['id']]] if q['id'] in spec['plain_variants'] else []))),
                'source':source('SRA_LLM_FN_concept.pdf' if q['initial'] else 'IAM-CC_Topic_experts.xlsx',q['source_locator']),
                'derivation':'Authored neutral, context-specific question; preserves the workbook feedback distinction between views and agency.',
                'review_status':'draft_pending_FN','permitted_use':['planner','researcher_reference'],
                'search_text':q['criterion']+' '+q[variant]})
    scenario=config('scenario')
    card={'id':scenario['id'],'type':'scenario','title':scenario['title'],'version':scenario['version'],
        'locale':'en','topic_ids':scenario['target_concerns'],'target_criterion':'contextual_application',
        'applicability':{'perspectives':list(base['perspectives']),'roles':list(base['stakeholders'])},
        'facts':scenario['illustrative_context'],'text':scenario['text'].split(' How do you feel')[0],
        'unknowns':['Actual sound measurements','Whether images are retained, recorded or shared','Verified mitigation feasibility',
                    'Named city, sites and endpoints','Local permissions and participation channels','Existing logistics'],
        'source':source('SRA_LLM_FN_concept.pdf','p.5; hypothetical changes pp.8–9'),
        'derivation':'Fixed FN illustrative scenario; source narrative is not a verified local plan or engineering guarantee.',
        'review_status':'historical_illustrative','permitted_use':['illustrative_scenario','researcher_reference'],
        'search_text':'hospital medical deliveries noise cameras privacy illustrative corridor'}
    cards=[card]+grant_scenarios(pdfs['GA.pdf'],base,source)
    grant_cards=deepcopy(cards[1:])
    from iam_sra.scenario_expansion import load_expansion
    additions,expansion_sources,expansion_identity=load_expansion()
    cards+=additions
    existing={s['document'] for s in sources}
    for item in expansion_sources:
        if item['document'] not in existing:sources.append(item);existing.add(item['document'])
    explanations=deepcopy(config('readiness_corpus')['passages'])
    for p in explanations:
        p.update(type='explanation',target_criterion=p['topic'],topic_ids=[],
            applicability={'perspectives':list(base['perspectives']),'roles':list(base['stakeholders'])},
            source=source(p['document_title'],p['location']),
            derivation='Existing curated passage rechecked against the supplied original; purpose permissions keep historical/reference material out of citizen explanations.',
            search_text=p['topic']+' '+p['text'])
    # Workbook construct explanations apply across cases. FN-specific facts do not.
    for passage in explanations:
        if passage['document_title']=='IAM-CC_Topic_experts.xlsx':passage['scenario_applicability']='all'
    explanations+=scenario_explanations(grant_cards+additions)
    for row in questions+cards+explanations:
        row['approved_by']=None;row.setdefault('version',spec['version'])
    comparisons=[{'id':'workbook_row_'+str(row),
        'original_cells':{name:'SRA IAM indicators!'+col+str(row) for name,col in [('definition','D'),('original_draft_question','H'),('corrective_feedback','I')]},
        'source':source('IAM-CC_Topic_experts.xlsx',f'SRA IAM indicators!D/H/I{row}'),
        'review_status':'draft_pending_FN','permitted_use':['researcher_reference'],
        'derivation':'Original wording, feedback and comments retained in the private source-notes sidecar, outside retrieval. Neither is an approved final questionnaire.'} for row in reviewed_rows]
    notes_path=private/'meeting_notes'
    inventory=[{'path':str(p.relative_to(ROOT)),'kind':'file','bytes':p.stat().st_size,
                'sha256':sha256(p.read_bytes()).hexdigest()} for p in ([notes_path] if notes_path.is_file() else sorted(notes_path.rglob('*'))) if p.is_file()]
    data={'version':'conversation-corpus-1.2.0','scenario_expansion':expansion_identity,'review_status':'draft_pending_FN','approved_by':None,
        'configuration':{name:sha256((ROOT/'configs'/f'{name}.json').read_bytes()).hexdigest() for name in ('baseline','conversation')},
        'sources':sources,'meeting_notes_inventory':inventory,'questions':questions,'scenarios':cards,'explanations':explanations,
        'source_comparisons':comparisons,
        'coverage':{'general_objectives':list(base['dimensions']),'roles':list(base['stakeholders']),
                    'scenario_followup_criteria':sorted({q['criterion'] for q in spec['scenario_questions']}),
                    'counts':{'questions':len(questions),'scenarios':len(cards),'explanations':len(explanations)},
                    'scenario_cities':sorted({c.get('city','illustrative') for c in cards}),
                    'missing':['Approved FN questionnaire and operational evidence-to-level policy (draft v4 anchor bank is available separately)','Consortium-validated FN report (D3.1 v0.18 draft is available)','Populated reviewed LL cases',
                               'Full paper texts (bibliographies are not paper findings)','Approved assets/fonts and hub/privacy ownership decisions'],
                    'LL_template':'Use case(s) per LL!A2; B2:D2 empty; no real city scenario inferred'}}
    # No participant/contact lists or meeting administration enter these collections.
    require_safe_data(questions);require_safe_data(cards);require_safe_data(explanations);require_safe_data(comparisons)
    target=(output or ROOT/spec['corpus_path']).resolve()
    if not target.is_relative_to(private.resolve()):raise ValueError('Generated source text must stay under references/private/.')
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    notes={'source':source('IAM-CC_Topic_experts.xlsx','Reviewed definitions, original drafts, feedback and J2/J8 revisions'),
        'cells':{key:ind[key] for key in ind if key in {f'{col}{row}' for col in 'CDHIJ' for row in reviewed_rows}|{'J2'}},'comments':comments,
        'use':'Private researcher comparison only; never a planner/citizen retrieval collection.'}
    if target==(ROOT/spec['corpus_path']).resolve():
        (private/'conversation-source-notes.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
        (private/'conversation-coverage.json').write_text(json.dumps(data['coverage'],ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'built_private','version':data['version'],**data['coverage']['counts'],'meeting_notes_files':len(inventory)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='Private review corpus path; an alternate output leaves deployed corpus and sidecars unchanged.')
    parser.add_argument('--inspect-case',choices=[f'expansion-{n:02d}' for n in range(1,7)],help='Researcher view of source basis/status; builds nothing.')
    args=parser.parse_args()
    try:
        if args.inspect_case:
            from iam_sra.scenario_expansion import load_expansion
            card=next(c for c in load_expansion()[0] if c['id']==args.inspect_case)
            print(json.dumps(card,ensure_ascii=False,indent=2))
        else:build(args.output)
    except PrivacyError as exc:
        print(json.dumps({'status':'screening_blocked','code':exc.code,'findings':list(exc.findings)}));raise SystemExit(1)
