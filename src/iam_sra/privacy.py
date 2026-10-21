"""Mandatory local privacy screening, failing closed when resources are unavailable."""
from dataclasses import dataclass
from functools import lru_cache, wraps
import inspect
import json
import re
from .assessment import AssessmentError

VERSION = 'privacy-1.0.0'


def screening_enabled():
    # Compatibility accessor for exports; no environment or per-case bypass.
    return True
NOTICE = ('Do not enter names, private addresses, contact details, '
          'credentials, bank details or identifiable medical information. Use general descriptions.')
UNAVAILABLE = ('Local privacy screening is unavailable. Run scripts/setup-privacy.sh and restart the UI. '
               'No answer has been sent to the model or added to the assessment.')


class PrivacyError(AssessmentError):
    def __init__(self, message, *, preview=None, unavailable=False, entity_types=(), findings=(), boundary=None):
        super().__init__(message, code='privacy_unavailable' if unavailable else 'privacy')
        self.entity_types = tuple(sorted(set(entity_types)))
        self.preview = preview  # Cleaned text only; never the original or an offset mapping.
        self.boundary = boundary if boundary in {'model_output','assessment_record'} else None
        # Safe detector metadata only; never include the detected text or offsets.
        self.findings = tuple({k:v for k,v in row.items() if k in {'field_path','entity_type','recognizer','confidence'}} for row in findings)


@dataclass(frozen=True)
class Finding:
    entity_type: str
    start: int
    end: int
    score: float = 1.0
    recognizer: str = 'local_context_pattern'


# Context is required: plain four-digit numbers, altitude and flight counts are safe.
PATTERNS = {
    'AUTH_SECRET': r'\b(?:password|passphrase|passwd|PIN|one[- ]time (?:code|password)|OTP|API[ _-]?key|access[ _-]?token|auth(?:entication)?[ _-]?(?:secret|token)|secret[ _-]?key)\s*["\']?\s*(?:is\b|was\b|[:=])\s*["\']?[^\s,;"\'}]{3,}',
    'CONTEXTUAL_PIN': r'\bPIN\s*(?:(?:is|[:=])\s*)?\d{4,8}\b',
    'AUTH_SECRET_BLOCK': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_\-]{12,}|\bBearer\s+[A-Za-z0-9_.\-]{12,}',
    'FINANCIAL_DETAIL': r'\b(?:bank account|account number|card number|credit card|debit card|IBAN|routing number|sort code|CVV|CVC)\s*["\']?\s*(?:is\b|[:=])\s*["\']?(?:\d[\d .-]{2,}|[A-Z]{2}\d{2}[A-Z0-9 .-]{8,})',
    # Street markers + house numbers; bounded local supplements, not a language model.
    'PRIVATE_ADDRESS': (
        r"\b\d{1,5}\s+(?:[^\W\d_]+(?:[.'-][^\W\d_]+)*\s+){1,4}(?:street|road|avenue|lane|drive|close|way|boulevard|st\.?|rd\.?)\b"
        r"|\b(?:[^\W\d_]+(?:[.'-][^\W\d_]+)*\s+){1,4}(?:street|road|avenue|lane|drive|boulevard|st\.?|rd\.?)\s*,?\s*\d{1,5}\b"
        r"|\b\d{1,5}\s+(?:calle|rua|via|οδός|οδος)\s+(?:[^\W\d_]+[ .'-]*){1,4}\b"
        r"|\b(?:calle|carrer|avenida|avda\.?|paseo|rua|travessa|estrada|praça|praca|via|viale|piazza|corso|vicolo|οδός|οδος|λεωφόρος|λεωφορος)"
        r"\s+(?:[^\W\d_]+[ .'-]*){1,5},?\s*\d{1,5}\b"
        r"|\b[Α-Ωα-ωΆ-ώ]+(?:ίων|ιων|ους|ού|ου|ας|ης)\s+\d{1,4}\b"
        r"|\b(?:my|home|private) address\s*(?:is|[:=])\s*[^\n.;]+"
    ),
    'PRIVATE_ADDRESS_UNIT': r"\b(?:apartment|apt\.?|flat|unit|piso|puerta|andar|interno|διαμέρισμα)\s*[:#-]?\s*\d{1,4}[a-z]?\b",
    'PRIVATE_ADDRESS_POSTCODE': r"\b(?:postcode|postal code|código postal|codigo postal|codice postale|código-postal|ταχυδρομικός κώδικας|τκ|cap)\s*[:=]?\s*\d{3,5}(?:[ -]\d{2,4})?\b",

    'IDENTIFIABLE_MEDICAL': r'\b(?:patient (?:ID|number|name)|medical record (?:ID|number)|NHS number|diagnosed patient)\s*(?:is\b|[:=])\s*[^\n.;]+',
    'CONTACT_PHONE': r'\b(?:call|phone|telephone|mobile|tel)\s*(?:me\s*)?(?:at\s*)?(?:(?:is|[:=])\s*)?\+?\d(?:[ ().-]*\d){9,14}\b',
    'CONTACT_EMAIL': r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',
}
BLOCK = {'CONTEXTUAL_PIN', 'AUTH_SECRET', 'AUTH_SECRET_BLOCK', 'FINANCIAL_DETAIL', 'CREDIT_CARD',
         'IBAN_CODE', 'US_BANK_NUMBER', 'CRYPTO', 'IDENTIFIABLE_MEDICAL'}
ENTITIES = ['PERSON', 'EMAIL_ADDRESS', 'PHONE_NUMBER', 'CREDIT_CARD', 'IBAN_CODE', 'US_BANK_NUMBER', 'CRYPTO']


def contextual_findings(text):
    found=[]
    for kind,pattern in PATTERNS.items():
        for m in re.finditer(pattern,text,re.I):
            end=m.end()
            if kind=='PRIVATE_ADDRESS':
                # Mask adjacent unit/postcode details only after a detected street
                # address. Bare years/flight counts elsewhere remain untouched.
                tail=re.match(r"(?:\s*,?\s*(?:(?:apartment|apt\.?|flat|unit|piso|puerta|andar|interno|διαμέρισμα)\s*[:#-]?\s*\d{1,4}[a-z]?|\d{4,5}(?:[- ]\d{2,3})?)){0,3}",text[end:],re.I)
                if tail:end+=tail.end()
            found.append(Finding(kind,m.start(),end))
    return found


@lru_cache(maxsize=1)
def detector():
    """Require locally installed English NLP; never auto-download at runtime."""
    try:
        import spacy
        from importlib.metadata import version
        if version('presidio-analyzer') != '2.2.360' or version('spacy') != '3.8.7' or version('en-core-web-sm') != '3.8.0':
            raise RuntimeError('Privacy resource version mismatch')
        from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        if not spacy.util.is_package('en_core_web_sm'):
            raise RuntimeError('NLP package missing')
        engine = NlpEngineProvider(nlp_configuration={'nlp_engine_name':'spacy',
            'models':[{'lang_code':'en', 'model_name':'en_core_web_sm'}]}).create_engine()
        analyzer = AnalyzerEngine(nlp_engine=engine, supported_languages=['en'])
        for kind, pattern in PATTERNS.items():
            analyzer.registry.add_recognizer(PatternRecognizer(supported_entity=kind,
                patterns=[Pattern(name=kind, regex=pattern, score=0.9)], supported_language='en'))
        return analyzer
    except Exception:
        raise PrivacyError(UNAVAILABLE, unavailable=True) from None


def screen(text):
    if not isinstance(text, str): raise PrivacyError('Use a plain text answer.')
    try:
        # Presidio is required even when the contextual layer finds nothing.
        presidio = detector().analyze(text=text, language='en', entities=ENTITIES + list(PATTERNS), score_threshold=0.55)
        found = [Finding(x.entity_type,x.start,x.end,float(getattr(x,'score',0.0)),
            str((getattr(x,'recognition_metadata',None) or {}).get('recognizer_name') or 'Presidio')) for x in presidio]
        found = list(found) + contextual_findings(text)
    except PrivacyError: raise
    except Exception: raise PrivacyError(UNAVAILABLE, unavailable=True) from None
    from .settings import CONCERNS
    thematic_labels = {v['label'].casefold() for v in CONCERNS.values()}
    # Presidio mislabels the transport noun in common phrases such as “van
    # trips” as a PERSON. Keep the exemption local to that exact noun/context;
    # names and other surrounding text remain screened normally.
    def benign_person(f):
        if f.entity_type!='PERSON':return False
        context=text[max(0,f.start-32):min(len(text),f.end+16)]
        return bool(re.search(r'\b(?:replace|avoid|reduce|substitute)\s+(?:the\s+)?van\s+(?:trips?|journeys?)\b',context,re.I))
    found = [f for f in found if 0 <= f.start < f.end <= len(text)
        and not (f.entity_type == 'PERSON' and (text[f.start:f.end].strip().casefold() in thematic_labels
            or re.fullmatch(r'(?:R|B)\d+_\d+(?:\.p\d+)?', text[f.start:f.end].strip())
            or re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',text[f.start:f.end].strip(' \t\r\n.'),re.I)) or benign_person(f))]
    if any(f.entity_type in BLOCK for f in found):
        raise PrivacyError('Remove credentials, financial details or identifiable medical details and resubmit using general descriptions.', entity_types=[f.entity_type for f in found], findings=[{'entity_type':f.entity_type,'recognizer':f.recognizer,'confidence':round(float(f.score),3)} for f in found])
    if found:
        # Merge overlapping findings. No raw-to-masked map survives this call.
        spans = []
        for f in sorted(found, key=lambda f:(f.start, -f.end)):
            if spans and f.start <= spans[-1][1]: spans[-1] = (spans[-1][0], max(spans[-1][1], f.end))
            else: spans.append((f.start, f.end))
        cleaned = text
        for start, end in reversed(spans): cleaned = cleaned[:start] + '[private detail removed]' + cleaned[end:]
        # Do not offer a preview unless it passes screening itself.
        try:
            require_clean(cleaned)
        except PrivacyError:
            raise PrivacyError('Remove names, private addresses and contact details, then resubmit using general descriptions.') from None
        raise PrivacyError('Private details were detected. Confirm the cleaned version or write a general description.', preview=cleaned, entity_types=[f.entity_type for f in found], findings=[{'entity_type':f.entity_type,'recognizer':f.recognizer,'confidence':round(float(f.score),3)} for f in found])
    return text


def require_clean(text):
    return screen(text)


@lru_cache(maxsize=1)
def reviewed_bibliographic_values():
    from .settings import ROOT
    registry = json.loads((ROOT/'references/source-register.json').read_text())
    from .settings import CONCERNS
    from .readiness_grounding import SourceExtraction, SourceReview
    values = [str(row[key]) for row in registry['sources']
        for key in ('document','local_path','sha256') if key in row]
    values += registry.get('privacy_reviewed_citation_locations', [])
    values += registry.get('privacy_reviewed_presentation_labels', [])
    values += [section for row in registry['sources'] for section in row.get('reviewed_sections', [])]
    # These version strings are fixed bibliographic metadata for the curated
    # local corpus, not respondent prose; whitelist the exact registered values.
    try:
        corpus=json.loads((ROOT/'configs/readiness_corpus.json').read_text())
        values += [row['source_version'] for row in corpus.get('passages',[]) if isinstance(row.get('source_version'),str)]
    except (OSError,ValueError,TypeError):
        pass
    values += [topic['label'] for topic in CONCERNS.values()]
    def schema_titles(node):
        if isinstance(node, dict):
            if isinstance(node.get('title'), str): values.append(node['title'])
            for child in node.values(): schema_titles(child)
        elif isinstance(node, list):
            for child in node: schema_titles(child)
    from .baseline import BaselineExtraction, BaselineReview, CanonicalExtraction, CanonicalReview
    for model in (SourceExtraction, SourceReview, BaselineExtraction, BaselineReview, CanonicalExtraction, CanonicalReview): schema_titles(model.model_json_schema())
    # Only exact controlled display values are reviewed metadata; custom city,
    # function and answer strings still pass through the mandatory detector.
    from .settings import config
    from .llm_client import BACKEND
    values += [BACKEND, 'iam-baseline-1.0.0','iam-baseline-2.0.0','iam-baseline-2.1.0','iam-baseline-2.2.0','iam-baseline-2.3.0','iam-baseline-2.3.1','baseline-handoff-1.0.0'] + config('baseline')['sources']
    for bank in ('perspectives','stakeholders','cities','familiarity','dimensions','sectors'):
        values += list(config('baseline').get(bank,{}).values())
    taxonomy=config('baseline').get('stakeholder_taxonomy',{})
    for row in taxonomy.get('categories',[]):
        values += [row['canonical_wording'],row['source_section']]
    if taxonomy:values.append(taxonomy['source_reference'])
    # Exact application-curated workbook locators are bibliographic metadata.
    # The detector misclassifies cell coordinates as PERSON; respondent text
    # and arbitrary values in source/locator fields are still screened.
    if (ROOT/'configs/conversation.json').is_file():
        conversation=config('conversation')
        values += list(conversation['source_locators'].values())
        values += [q['source_locator'] for q in conversation['scenario_questions']]
        values += [conversation['schema_version'],conversation['version'],conversation['planner_version']]
        values += conversation.get('scoring_source_locators',[])
        # The real detector flags the fixed GA scenario identifiers as PERSON.
        # These exact application identifiers cannot contain respondent text.
        from .conversation_sources import GRANT_SCENARIO_IDS,GRANT_ROUTE_LABELS
        values += list(GRANT_SCENARIO_IDS)+[i+'_facts' for i in GRANT_SCENARIO_IDS]
        values += list(GRANT_ROUTE_LABELS)
        values += ['eval/conversation_meeting_cases_v2.json']
        values += ['p.5; hypothetical changes pp.8–9','C/D/H/I8,15,16; relevant comments']
        values += [f'SRA IAM indicators!D/H/I{row}' for row in (3,4,6,8,10,14,15,16)]
        values += [f'SRA IAM indicators!{col}{row}' for row in (3,4,6,8,10,14,15,16) for col in 'DHI']
    values += [row['cells'] for row in config('readiness_levels')['crl']]
    return frozenset(values)


def require_safe_data(value):
    """Batch strings through the local NLP engine; no content-result cache."""
    strings = []
    def collect(item,path='root'):
        if hasattr(item, 'model_dump'): item = item.model_dump()
        if isinstance(item, str):
            # Model envelopes carry JSON as a string. Screen its semantic fields,
            # not punctuation/field labels as if they were citizen prose.
            if item.lstrip().startswith(('{','[')):
                try: decoded = json.loads(item)
                except (ValueError, RecursionError): decoded = None
                if isinstance(decoded, (dict, list)):
                    collect(decoded,path)
                    return
            # Source/code SHA-256 values and the Git commit in application-generated
            # provenance map are opaque integrity metadata. NLP models can
            # misread long hex strings as names; only this exact structural
            # location and encoding is exempt. User/model text and hashes in
            # every other field are still screened.
            generated_digest = (
                ((path.startswith('root.provenance.file_sha256.')
                  or path == 'root.provenance.code_snapshot_sha256')
                 and re.fullmatch(r'[a-f0-9]{64}', item) is not None)
                or (path == 'root.provenance.code_commit'
                    and re.fullmatch(r'[a-f0-9]{40}', item) is not None)
            )
            # Generated scoring claim IDs (C1, C2, ...) are references, not names.
            # The real detector flags C3. Exempt only this bounded ID syntax in
            # reference fields; text, quotations and arbitrary field values stay screened.
            generated_claim_reference=(re.fullmatch(r'C[1-9]\d{0,2}',item) is not None and (
                path.endswith('.claim_id') or
                re.search(r'\.(?:criteria\[\d+\]|judgement)\.evidence_ids\[\d+\]$',path) is not None))
            # NLP can tag a substring of a generated UUID as PERSON, making
            # otherwise identical model calls fail randomly at audit retention.
            generated_request_id=(path.endswith('.request_id') and
                re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',item) is not None)
            # Public controller/transport session IDs can suffer the same
            # substring PERSON false positive. Only known generated record
            # locations are metadata; UUIDs in answers or nested user JSON
            # still go through the detector. These IDs are not owner credentials.
            session_id_path = path in {
                'root.id', 'root.session_id', 'root.baseline.session_id', 'root.scenario.session_id',
                'root.handoff.baseline_session_id', 'root.baseline.handoff.baseline_session_id',
                'root.baseline_handoff.baseline_session_id',
            } or re.fullmatch(r'root\.superseded_scenarios\[\d+\]\.session\.session_id', path) is not None
            generated_session_id = session_id_path and re.fullmatch(
                r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}', item) is not None
            # The pinned vLLM envelope also has an opaque public completion ID.
            # Its hexadecimal suffix sometimes triggers PERSON; it carries no
            # respondent prose or ownership credential.
            generated_completion_id = path == 'root.id' and re.fullmatch(r'chatcmpl-[0-9a-f]{32}', item) is not None
            # V4's controller-resolved cell addresses (e.g. G63) are fixed source
            # coordinates. The installed NLP model tags G63 as PERSON. Exempt
            # only the bounded coordinate syntax in actual source-reference fields;
            # quotations, explanations, arbitrary source values and respondent prose
            # remain screened. Membership is validated against the pinned bank.
            readiness_cell_reference = (
                (path.endswith('.source.cell') or path.endswith('.criterion_source.cell') or path.endswith('.review_source.status_cell')
                 or path.endswith('.review_source.comment_cell'))
                and re.fullmatch(r'[A-I](?:[2-9]|[1-9][0-9]|1[0-2][0-9]|13[0-6])', item) is not None
            )
            readiness_review_reference = (path.endswith('.review_row_id') and re.fullmatch(
                r'indicator-(?:0[1-9]|1[0-5])-level-[1-9]', item) is not None)
            if item not in reviewed_bibliographic_values() and not generated_digest and not generated_claim_reference and not generated_request_id and not generated_session_id and not generated_completion_id and not readiness_cell_reference and not readiness_review_reference:
                strings.append((item,path))
        elif isinstance(item, dict):
            for key, val in item.items():
                # JSON schemas are generated only from trusted application
                # models; their short structural labels are not respondent
                # content. Dynamic evidence-ID enums contain only controller
                # IDs. Screen the system/user payloads and all records instead.
                if key=='schema': continue
                # Standard JSON-schema vocabulary is structure, not a person's name.
                generated_source_path = (
                    path == 'root.provenance.file_sha256'
                    and re.fullmatch(r'(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+', str(key)) is not None
                )
                if (not generated_source_path
                    and not re.fullmatch(r'[a-z][a-z0-9_]*', str(key))
                    and key not in {'$defs','$ref','properties','required','type','title','description','items','enum','anyOf','allOf','oneOf','additionalProperties','default','minLength','maxLength','minimum','maximum','minItems','maxItems'}):
                    strings.append((str(key),path+'.<key>'))
                if isinstance(val, (str, int)) and re.search(r'password|pin|token|secret|iban|card.number|account.number', str(key), re.I):
                    strings.append((str(key) + ': ' + str(val),path+'.'+str(key)))
                collect(val,path+'.'+str(key))
        elif isinstance(item, (list, tuple)):
            for i,val in enumerate(item): collect(val,path+f'[{i}]')
    collect(value)
    for text,path in strings:
        try: require_clean(text)
        except PrivacyError as exc:
            # An output/export/request preview cannot replace an audited structure.
            findings=[{'field_path':path,**row} for row in exc.findings]
            raise PrivacyError(UNAVAILABLE if exc.code == 'privacy_unavailable' else
                'Sensitive content was withheld. Use a new session with general descriptions; no unsafe output or download is available.',
                unavailable=exc.code == 'privacy_unavailable', entity_types=exc.entity_types, findings=findings) from None
    return value


def safe_message(exc):
    """Untrusted exception bodies never become a privacy diagnostic."""
    if isinstance(exc, PrivacyError): return str(exc)
    try: require_clean(str(exc)); return str(exc)
    except PrivacyError: return 'This step could not be completed safely. No unsafe details are displayed.'


def check_contract(session):
    if vars(session).get('privacy_contract') != VERSION:
        raise PrivacyError('This older session predates local privacy screening. Start a new session using synthetic, general descriptions. Existing files are not deleted.')


def guarded(*fields):
    """Before controller mutations, model calls, text drafts, checkpoints or audits."""
    def decorate(fn):
        signature = inspect.signature(fn)
        @wraps(fn)
        def wrapped(self, *args, **kwargs):
            check_contract(self)
            bound = signature.bind(self, *args, **kwargs)
            for field in fields:
                if field in bound.arguments:
                    if isinstance(bound.arguments[field], str): require_clean(bound.arguments[field])
                    else: require_safe_data(bound.arguments[field])
            return fn(self, *args, **kwargs)
        wrapped._privacy_fields = fields
        return wrapped
    return decorate


def screened_export(value, session=None):
    if session is not None: check_contract(session)
    require_safe_data(value)
    return value


def export_guard(fn):
    @wraps(fn)
    def wrapped(self, *args, **kwargs):
        check_contract(self)
        result = fn(self, *args, **kwargs)
        if isinstance(result, dict): result['privacy_screening_enabled'] = screening_enabled()
        return screened_export(result)
    return wrapped


def safe_diagnostics(value):
    """Retain screened metadata only; never retain rejected diagnostic content."""
    try:
        require_safe_data(value)
        return value
    except PrivacyError:
        return {"details_withheld": True, "reason": "privacy_screening"}
