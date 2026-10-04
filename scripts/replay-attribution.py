"""Bounded score-free live contrasts; every attempted case and error is retained."""
import argparse,json,time
from pathlib import Path
from iam_sra.conversation_client import ConversationClient
from iam_sra.interpretation import EvidenceItem
p=argparse.ArgumentParser();p.add_argument('--output',default='.runtime/attribution-live.json');p.add_argument('--cases',nargs='+');args=p.parse_args()
fixture=json.loads(Path('eval/attribution_cases.json').read_text());results=[];deadline=time.monotonic()+240
selected=[c for c in fixture['cases'] if not args.cases or c['id'] in args.cases]
for case in selected:
    if time.monotonic()>=deadline:break
    start=time.monotonic();c=ConversationClient();c.external_deadline=min(deadline,start+45)
    row={'id':case['id'],'attempted':True,'success':False,'semantic_contract_pass':False}
    evidence={'O.p001':EvidenceItem(id='O.p001',text=case['text'],context='original',source='citizen_original')}
    try:
        m=c.interpret(evidence);ids=[x.concern_id for x in m.concerns]
        row.update(success=True,meaning=m.model_dump(),mappings=ids,semantic_contract_pass=set(case.get('require',[]))<=set(ids) and not set(case.get('exclude',[]))&set(ids),attribution_decisions=c.last_candidate_projections,settings=c.last_settings)
        if case.get('discovery'):
            row['discovery']=c.discovery_facts(evidence).model_dump();row['boundary_decisions']=c.last_candidate_projections
    except Exception as exc:row.update(success=False,error_type=type(exc).__name__,error=str(exc))
    row.update(latency_seconds=round(time.monotonic()-start,3),last_diagnostics=c.last_diagnostics,last_raw_trace=c.last_trace)
    results.append(row);print(json.dumps({k:row[k] for k in ['id','success','semantic_contract_pass','latency_seconds','error'] if k in row}),flush=True)
record={'fixture_version':fixture['version'],'live':True,'scientific_validation':False,'attempts':results,'not_attempted':[c['id'] for c in selected if c['id'] not in {r['id'] for r in results}]}
path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(record,indent=2)+'\n')
