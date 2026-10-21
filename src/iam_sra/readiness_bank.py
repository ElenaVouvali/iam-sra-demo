"""Validated FN reference-bank loading, shared by import and assisted assessment."""
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path

PROFILES = {'technical': 'TRL', 'organisational': 'ORL', 'citizen': 'CRL'}


def validate_bank(bank):
    indicators = bank['indicators']
    if len(indicators) != 15 or {i['number'] for i in indicators} != set(range(1, 16)):
        raise ValueError('Expected exactly 15 distinct indicators numbered 1–15.')
    ids = {i['id'] for i in indicators}
    if len(ids) != 15:
        raise ValueError('Duplicate indicator IDs.')
    for indicator in indicators:
        if not indicator['name'].strip() or not indicator['definition'].strip():
            raise ValueError('Incomplete indicator definition.')
        if set(indicator['assessment_criteria']) != set(PROFILES) or any(
                not c['text'].strip() for c in indicator['assessment_criteria'].values()):
            raise ValueError('Expected complete assessment criteria for all three profiles.')
    expected = {(i, p, level) for i in ids for p in PROFILES for level in range(1, 10)}
    seen = set()
    rows = {r['id']: r for r in bank['review_rows']}
    if len(rows) != len(bank['review_rows']):
        raise ValueError('Duplicate shared source review-row IDs.')
    if len(rows) != 135:
        raise ValueError('Expected 135 distinct shared source review rows.')
    for record in bank['statements']:
        key = (record['indicator_id'], record['profile'], record['level'])
        if key in seen:
            raise ValueError(f'Duplicate indicator/profile/level: {key}')
        seen.add(key)
        if record['scale'] != PROFILES.get(record['profile']) or not record['statement'].strip():
            raise ValueError(f'Incomplete or incompatible statement: {key}')
        row = rows.get(record['review_row_id'])
        if row is None or (row['indicator_id'], row['level']) != (key[0], key[2]):
            raise ValueError(f'Invalid shared review-row reference: {key}')
    if seen != expected or len(bank['statements']) != 405:
        raise ValueError('Expected 405 statements: nine distinct levels for each indicator/profile.')
    if set(bank['generic_scales']) != {'TRL', 'ORL', 'CRL', 'SRL'}:
        raise ValueError('Expected all four generic scales.')
    for scale, descriptions in bank['generic_scales'].items():
        if len(descriptions) != 9 or {r['level'] for r in descriptions} != set(range(1, 10)) or any(
                not r['description'].strip() for r in descriptions):
            raise ValueError(f'Incomplete or duplicate generic {scale} levels.')



@lru_cache(maxsize=4)
def _load(path):
    raw = Path(path).read_bytes()
    bank = json.loads(raw)
    if bank.get('schema_version') != 'readiness-scale-bank-1.0.0' or bank.get('bank_version') != 'fn-v4-1.0.0':
        raise ValueError('Incompatible readiness bank. Rebuild with scripts/import-readiness-scales.py build.')
    validate_bank(bank)
    from .settings import ROOT
    register = json.loads((ROOT/'references/source-register.json').read_text())
    sources = register['sources']
    expected = register['readiness_scale_reference_import']['generated_bank'].get('sha256')
    if not expected or sha256(raw).hexdigest() != expected:
        raise ValueError('Bank bytes do not match the reviewed source register. Rebuild and review the bank before use.')
    if not any(s['document'] == bank['source']['document'] and s['sha256'] == bank['source']['sha256'] for s in sources):
        raise ValueError('The bank source does not match the source register; review and rebuild it.')
    return bank, sha256(raw).hexdigest()


def load_bank(path=None):
    """Load once per process. Sessions retain a private snapshot; updates need restart."""
    from .settings import ROOT
    path = path or ROOT/'references/private/readiness-scales-v4.json'
    try:
        bank, digest = _load(str(Path(path).resolve()))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError('Indicator assessment needs a valid private readiness-scales-v4.json. Run scripts/import-readiness-scales.py build and restart the UI/API.') from exc
    value = deepcopy(bank)
    value['bank_sha256'] = digest
    return value
