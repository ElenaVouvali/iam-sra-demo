#!/usr/bin/env python3
"""Extract only the end scales from supplied private PDFs; register exact bytes.

Run after deliberate source review. Never edits the PDFs or the existing register.
Uses the system pdftotext executable. Derived scale text remains private.
"""
from pathlib import Path
from hashlib import sha256
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = {
    'citizen_short': ('SRAA Citizen interview example 20min.pdf', [12,13]),
    'citizen_extended': ('SRAA Citizen interview example 35min.pdf', [17,18]),
    'organisational': ('SRAA Organisation interview example.pdf', [16]),
    'technical': ('SRAA Technology interview example.pdf', [17,18]),
}


def extract(path, pages, key):
    text=subprocess.check_output(['pdftotext','-layout',str(path),'-']).decode()
    sections=text.split('\f')
    anchors=[];current=None;column=None
    for page_no in pages:
        for line in sections[page_no-1].splitlines():
            if 'Example provisional result' in line or line.strip()=='Provisional result': break
            level=re.match(r'\s*Level ([1-9]) – (.*)',line)
            if level:
                meaning=re.search(r'\b(?:You |The |A representative |An integrated |A technical |Key elements)',line)
                if not meaning: raise ValueError('Missing description start: '+line)
                column=meaning.start()
                current={'id':key+'-'+level[1], 'level':int(level[1]), 'label':line[:column].split(' – ',1)[1].strip(),
                         'description':line[column:].strip(), 'source':{'document':path.name,'pdf_pages':[page_no]}}
                anchors.append(current)
            elif current and line.strip() and not any(x in line for x in ['Interviewer','What it means']):
                if not line.startswith(' '): continue
                left,right=line[:column].strip(),line[column:].strip()
                if left: current['label']+=' '+left
                if right:current['description']+=' '+right
                if page_no not in current['source']['pdf_pages']:current['source']['pdf_pages'].append(page_no)
    for anchor in anchors: anchor['label']=anchor['label'].strip()
    if len(anchors)!=9 or [a['level'] for a in anchors]!=list(range(1,10)):raise ValueError('Incomplete source scale')
    return anchors


def main():
    derived={};register={'version':'eva-interviews-2026-11-04-v1','status':'supplied_examples_prototype_pending_partner_review','sources':{}}
    for key,(name,pages) in DOCUMENTS.items():
        path=ROOT/'references/private'/name
        derived[key]=extract(path,pages,key)
        register['sources'][key]={'document':name,'sha256':sha256(path.read_bytes()).hexdigest(),'scale_pdf_pages':pages,
                                 'reviewed':'Entire PDF including branching, notes and disagreement guidance; blank terminal pages excluded.'}
    output=ROOT/'references/private/chat-rubrics-v1.json'
    output.write_text(json.dumps(derived,ensure_ascii=False,indent=2)+'\n')
    register['derived']={'path':'references/private/chat-rubrics-v1.json','sha256':sha256(output.read_bytes()).hexdigest(),
                         'normalisation':'PDF layout line wraps joined with spaces. No wording replacement.'}
    (ROOT/'references/chat-source-register.json').write_text(json.dumps(register,indent=2)+'\n')
    print('Registered four PDF scales (36 anchors); private source wording retained.')

if __name__=='__main__':main()
