"""Extract planned Living Lab examples from the supplied private grant agreement."""
import re
from copy import deepcopy

GRANT_SCENARIO_IDS=tuple(f'ga_{city}_{n}' for city,count in (('madrid',2),('milan',2),('coimbra',4)) for n in range(1,count+1))
# Public route labels verified in GA PDF pp.56–59, not participant identities.
GRANT_ROUTE_LABELS=('Hospital Carlos III – La Paz University Hospital',
    'Escorial Hospital – Fresnedillas de la Oliva','San Raffaele – Villa Turro',
    'San Raffaele – Istituto Galeazzi','Local pharmacy → Sobral de Baixo',
    'Local pharmacy → Sobral de Cima','Local pharmacy → Moninho','Local pharmacy → Póvoa')


def grant_scenarios(text, baseline, source):
    pages=text.split('\f')
    def page(number,marker):
        value=pages[number-1]
        if marker not in value:raise ValueError('Grant agreement layout changed; review the scenario extraction.')
        return value
    madrid=page(56,'Madrid Living Lab:')+'\n'+page(57,'Route 2:')
    milan=page(58,'Milan Living Lab:')
    coimbra=page(59,'Coimbra Living Lab:')
    examples=[]
    for number in (1,2):
        match=re.search(r'Route '+str(number)+r':\s*(.*?)(?=\n\s*[•®]|Interventions:)',madrid,re.S)
        if not match:raise ValueError('A Madrid route could not be extracted.')
        # Page furniture interrupts the first route; retain its complete route sentence.
        paragraph=' '.join(match.group(1).split())
        if number==1:paragraph=paragraph[:paragraph.index(').')+2]
        examples.append((f'ga_madrid_{number}','madrid',paragraph,56 if number==1 else 57,
                         ['multimodality_congestion','infrastructure_land_use','noise','welfare_equity']))
    for number,route in enumerate(('San Raffaele – Villa Turro:','San Raffaele – Istituto Galeazzi:'),1):
        match=re.search(re.escape(route)+r'\s*(.*?)(?=\n\s*•|\n Authorisation pathways)',milan,re.S)
        if not match:raise ValueError('A Milan route could not be extracted.')
        examples.append((f'ga_milan_{number}','milan',' '.join((route+' '+match.group(1)).split()),58,
                         ['technical_safety_security_privacy','wind_downwash','infrastructure_land_use','welfare_equity']))
    for number in range(1,5):
        match=re.search(r'Route '+str(number)+r':\s*([^\n]+)',coimbra)
        if not match:raise ValueError('A Coimbra route could not be extracted.')
        paragraph=' '.join(match.group(1).split())+'.'
        paragraph+=' The grant agreement describes routine medical deliveries and tests under emergency conditions, including wildfire isolation and blocked roads.'
        examples.append((f'ga_coimbra_{number}','coimbra',paragraph,59,
                         ['accessibility','welfare_equity','perceived_safety_privacy','noise']))
    cards=[]
    for identifier,city,paragraph,pdf_page,topics in examples:
        title=paragraph.split(':',1)[0].split(' (',1)[0]
        description=paragraph[len(title):].lstrip(': ')
        # Spell out approximate distances; the NLP detector misreads "~2.8 km"
        # as a person. The numerical value and approximation remain unchanged.
        description=re.sub(r'~(\d+(?:\.\d+)?) km',r'approximately \1 kilometres',description)
        facts={'status':'planned_in_supplied_grant_agreement','city':city,'route_label':title,'source_description':description,
               'current_operational_status':'not_verified','source_pdf_page':pdf_page}
        cards.append({'id':identifier,'type':'scenario','title':title,'version':'1.0.0','locale':'en',
            'topic_ids':topics,'target_criterion':'contextual_application','city':city,
            'applicability':{'perspectives':list(baseline['perspectives']),'roles':list(baseline['stakeholders'])},
            'facts':facts,'text':'The supplied grant agreement describes a planned medical-delivery route in '+city.capitalize()+'. Route details in the source: '+description+
                ' This discussion uses the source-described plan; it does not establish that the service is currently operating.',
            'unknowns':['Current operational and authorisation status','Measured sound and privacy/data-handling policies',
                        'Routine schedules and verified service outcomes','Existing delivery arrangements and local participation channels'],
            'source':source('GA.pdf',f'PDF p.{pdf_page}; Part B p.{pdf_page-37}'),
            'derivation':'Route details extracted from the supplied grant agreement with approximate distance units expanded; contextual introduction authored for the prototype.',
            'review_status':'source_described_plan_pending_local_review','approved_by':None,
            'permitted_use':['illustrative_scenario','researcher_reference'],
            'search_text':city+' '+description+' '+' '.join(topics)})
    return cards


def scenario_explanations(cards):
    passages=[]
    for card in cards:
        source=card['source']
        passages.append({'id':card['id']+'_facts','type':'explanation','document_title':source['document'],
            'location':source['locator'],'source_version':source['version'],'source_sha256':source['sha256'],
            'topic':'scenario medical deliveries route logistics','locale':'en','scenario_applicability':card['id'],
            'source_status':card.get('source_status','source_described_plan'),'review_status':card['review_status'],'approved_by':None,
            'permitted_use':['citizen_explanation','researcher_reference'],'text':card['text'],
            'source':deepcopy(source),'target_criterion':'contextual_application','topic_ids':card['topic_ids'],
            'applicability':deepcopy(card['applicability']),'derivation':card['derivation'],'search_text':card['search_text']})
        if card.get('scenario_bank_version'):
            passages[-1].update(source_refs=deepcopy(card['source_refs']),source_verification=card['source_verification'],
                text=card['text']+'\nSource status: '+card['source_status']+'. Verification: '+card['source_verification']+
                '. Still unknown: '+'; '.join(card['unknowns']))
    return passages
