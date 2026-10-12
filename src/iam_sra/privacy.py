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
    def __init__(self, message, *, preview=None, unavailable=False, entity_types=()):
        super().__init__(message, code='privacy_unavailable' if unavailable else 'privacy')
        self.entity_types = tuple(sorted(set(entity_types)))
        self.preview = preview  # Cleaned text only; never the original or an offset mapping.


@dataclass(frozen=True)
class Finding:
    entity_type: str
    start: int
    end: int
    score: float = 1.0


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
        found = detector().analyze(text=text, language='en', entities=ENTITIES + list(PATTERNS), score_threshold=0.55)
        found = list(found) + contextual_findings(text)
    except PrivacyError: raise
    except Exception: raise PrivacyError(UNAVAILABLE, unavailable=True) from None
    from .settings import CONCERNS
    thematic_labels = {v['label'].casefold() for v in CONCERNS.values()}
    found = [f for f in found if 0 <= f.start < f.end <= len(text)
        and not (f.entity_type == 'PERSON' and (text[f.start:f.end].strip().casefold() in thematic_labels
            or re.fullmatch(r'(?:R|B)\d+_\d+(?:\.p\d+)?', text[f.start:f.end].strip())
            or re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',text[f.start:f.end].strip(' \t\r\n.'),re.I)))]
    if any(f.entity_type in BLOCK for f in found):
        raise PrivacyError('Remove credentials, financial details or identifiable medical details and resubmit using general descriptions.', entity_types=[f.entity_type for f in found])
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
        raise PrivacyError('Private details were detected. Confirm the cleaned version or write a general description.', preview=cleaned, entity_types=[f.entity_type for f in found])
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
    values += [topic['label'] for topic in CONCERNS.values()]
    def schema_titles(node):
        if isinstance(node, dict):
            if isinstance(node.get('title'), str): values.append(node['title'])
            for child in node.values(): schema_titles(child)
        elif isinstance(node, list):
            for child in node: schema_titles(child)
    from .baseline import BaselineExtraction, BaselineReview
    for model in (SourceExtraction, SourceReview, BaselineExtraction, BaselineReview): schema_titles(model.model_json_schema())
    # Only exact controlled display values are reviewed metadata; custom city,
    # function and answer strings still pass through the mandatory detector.
    from .settings import config
    from .llm_client import BACKEND
    values += [BACKEND, 'iam-baseline-1.0.0','iam-baseline-2.0.0','baseline-handoff-1.0.0'] + config('baseline')['sources']
    for bank in ('perspectives','stakeholders','cities','familiarity','dimensions','sectors'):
        values += list(config('baseline').get(bank,{}).values())
    taxonomy=config('baseline').get('stakeholder_taxonomy',{})
    for row in taxonomy.get('categories',[]):
        values += [row['canonical_wording'],row['source_section']]
    if taxonomy:values.append(taxonomy['source_reference'])
    return frozenset(values)


def require_safe_data(value):
    """Batch strings through the local NLP engine; no content-result cache."""
    strings = []
    def collect(item):
        if hasattr(item, 'model_dump'): item = item.model_dump()
        if isinstance(item, str):
            # Model envelopes carry JSON as a string. Screen its semantic fields,
            # not punctuation/field labels as if they were citizen prose.
            if item.lstrip().startswith(('{','[')):
                try: decoded = json.loads(item)
                except (ValueError, RecursionError): decoded = None
                if isinstance(decoded, (dict, list)):
                    collect(decoded)
                    return
            if item not in reviewed_bibliographic_values(): strings.append(item)
        elif isinstance(item, dict):
            for key, val in item.items():
                # Standard JSON-schema vocabulary is structure, not a person's name.
                if not re.fullmatch(r'[a-z][a-z0-9_]*', str(key)) and key not in {'$defs','$ref','properties','required','type','title','description','items','enum','anyOf','allOf','oneOf','additionalProperties','default','minLength','maxLength','minimum','maximum','minItems','maxItems'}:
                    strings.append(str(key))
                if isinstance(val, (str, int)) and re.search(r'password|pin|token|secret|iban|card.number|account.number', str(key), re.I):
                    strings.append(str(key) + ': ' + str(val))
                collect(val)
        elif isinstance(item, (list, tuple)):
            for val in item: collect(val)
    collect(value)
    try: require_clean('\n.\n'.join(strings))
    except PrivacyError as exc:
        # An output/export/request preview cannot replace an audited structure.
        raise PrivacyError(UNAVAILABLE if exc.code == 'privacy_unavailable' else
            'Sensitive content was withheld. Use a new session with general descriptions; no unsafe output or download is available.',
            unavailable=exc.code == 'privacy_unavailable', entity_types=exc.entity_types) from None
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
