"""Private v0.2 question configuration, cross-checked against the pinned FN bank."""
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from .readiness_bank import PROFILES

VERSION = '2026-10-21-v0.2'
SCHEMA = 'iam-sra-provisional-questionnaire-0.2.0'


def validate_questionnaire(value, bank):
    if value.get('questionnaire_version') != VERSION or value.get('schema_version') != SCHEMA:
        raise ValueError('Incompatible questionnaire version.')
    source = next((s for s in value['source_register'] if s['id'] == 'v4'), {})
    if source.get('sha256') != bank['source']['sha256']:
        raise ValueError('Questionnaire v4 identity differs from the registered FN bank.')
    indicators = {i['id']: i for i in bank['indicators']}
    statements = {s['id']: s for s in bank['statements']}
    expected = {(key, profile) for key in indicators for profile in PROFILES}
    modules = value['modules']
    if len(modules) != 45 or {(m['indicator_id'], m['profile']) for m in modules} != expected:
        raise ValueError('Expected exactly 45 distinct indicator/profile modules.')
    probes = {p['id']: p for p in value['shared_probes']}
    if len(probes) != 42 or len(value['shared_probes']) != 42:
        raise ValueError('Expected 42 distinct shared probes.')
    source_ids = {s['id'] for s in value['source_register']}
    for probe in probes.values():
        if (probe['profile'] not in PROFILES or not probe['text'].strip() or not probe['ask_when'].strip()
                or probe['origin'] not in {'extracted_verbatim','adapted','newly_drafted'}
                or any(r['source_id'] not in source_ids for r in probe['source_refs'])):
            raise ValueError('Invalid shared-probe profile, wording, routing or provenance.')
    seen, question_count, likert_count = set(), 0, 0
    for module in modules:
        indicator = indicators[module['indicator_id']]
        profile = module['profile']
        if module['id'] != module['indicator_id'] + '-' + PROFILES[profile].lower():
            raise ValueError('Module ID differs from its indicator/profile.')
        if (module['scale'] != PROFILES[profile] or module['indicator_name'] != indicator['name']
                or module['definition'] != indicator['definition']
                or module['assessment_criterion'] != indicator['assessment_criteria'][profile]['text']):
            raise ValueError('Questionnaire definition/criterion/profile differs from the FN bank.')
        for field, original in [('definition_source', indicator.get('source',{}).get('definition')),
                                ('criterion_source',indicator['assessment_criteria'][profile]['source'])]:
            if module[field]['source_id']!='v4' or (original and module[field]['locator'] != original['sheet']+'!'+original['cell']):
                raise ValueError('Definition or criterion source cell differs from the FN bank.')
        anchors = module['anchors']
        if len(anchors) != 9 or {a['level'] for a in anchors} != set(range(1, 10)):
            raise ValueError('Each module must contain nine distinct source statements.')
        for anchor in anchors:
            original = statements.get(anchor['id'], {})
            locator = original.get('source', {})
            if (original.get('indicator_id') != module['indicator_id'] or original.get('profile') != profile
                    or original.get('level') != anchor['level'] or original.get('statement') != anchor['statement']
                    or anchor['source_ref']['locator'] != locator.get('sheet', '') + '!' + locator.get('cell', '')
                    or anchor['review_row_ref'] != original.get('review_row_id')):
                raise ValueError('Questionnaire statement text, ID or locator differs from the FN bank.')
            if anchor['source_ref']['source_id']!='v4':
                raise ValueError('Exact statements must reference the FN v4 source.')
        order = module['question_order']
        if len(set(order)) != len(order) or set(order) != {q['id'] for q in module['questions']}:
            raise ValueError('Question order must contain each module question once.')
        for probe_id in module['shared_probe_ids']:
            if probe_id not in probes or probes[probe_id]['profile'] != profile:
                raise ValueError('Unknown or wrong-profile shared probe.')
        for question in module['questions'] + module['optional_likert_items']:
            if question['id'] in seen or not question['text'].strip():
                raise ValueError('Duplicate or empty questionnaire item.')
            seen.add(question['id'])
            if question.get('profile',profile)!=profile or question.get('indicator_id',module['indicator_id'])!=module['indicator_id']:
                raise ValueError('Question belongs to another module/profile.')
            if question.get('origin') not in {'extracted_verbatim', 'adapted', 'newly_drafted'}:
                raise ValueError('Missing wording provenance.')
            if any(r['source_id'] not in source_ids for r in question['source_refs']):
                raise ValueError('Unknown question source reference.')
        if profile != 'citizen' and module['optional_likert_items']:
            raise ValueError('The draft supplies Likert items for citizens only.')
        question_count += len(module['questions'])
        likert_count += len(module['optional_likert_items'])
    if question_count != 150 or likert_count != 15:
        raise ValueError('Expected 150 module questions and 15 optional citizen Likert items.')
    rows = {r['id']: r for r in bank['review_rows']}
    if len(value['source_review_rows']) != 135 or {r['id'] for r in value['source_review_rows']} != set(rows):
        raise ValueError('Incomplete shared source review rows.')
    for row in value['source_review_rows']:
        if (row['status'], row['comment']) != (rows[row['id']]['status'], rows[row['id']]['comment']):
            raise ValueError('Questionnaire review status differs from the shared source row.')


@lru_cache(maxsize=1)
def _load():
    from .settings import ROOT
    from .readiness_bank import load_bank
    path = ROOT/'references/private/questionnaire-v0.2/IAM_SRA2_questionnaire_v0.2.json'
    raw = path.read_bytes()
    value = json.loads(raw)
    register = json.loads((ROOT/'references/source-register.json').read_text())['questionnaire_v02']
    if sha256(raw).hexdigest() != register['json_sha256']:
        raise ValueError('Questionnaire bytes differ from the registered package. Review the input, not its hash.')
    validate_questionnaire(value, load_bank())
    value['_identity'] = {'document': path.name, 'sha256': register['json_sha256'],
        'package_sha256': register['package_sha256'], 'questionnaire_version': VERSION,
        'schema_version': SCHEMA, 'status': value['status'],
        'source_discrepancies': register['source_discrepancies']}
    return value


def load_questionnaire():
    try:
        return deepcopy(_load())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError('Indicator assessment needs the registered private IAM_SRA2_questionnaire_v0.2.json. '
                         'Extract IAM_SRA2_questionnaire_v0.2.zip under references/private/questionnaire-v0.2/ and restart the review API/UI.') from exc


def module_for(value, indicator_id, profile):
    return next(m for m in value['modules'] if m['indicator_id'] == indicator_id and m['profile'] == profile)
