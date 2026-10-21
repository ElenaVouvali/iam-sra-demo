#!/usr/bin/env python3
"""Import FN v4 source text for inspection only; never an assessment policy."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import posixpath
import re
import sys
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / 'references/private/IAM-CC_SRA_IAM_indicators_TRL_ORL_CRL_scales_v4.xlsx'
BANK = ROOT / 'references/private/readiness-scales-v4.json'
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL_ID = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
sys.path.insert(0, str(ROOT/'src'))
from iam_sra.readiness_bank import PROFILES, validate_bank


def normalise(text):
    """Normalise lookup keys only, never imported wording."""
    return ' '.join(text.split()).casefold()


def coordinate(cell):
    match = re.fullmatch(r'([A-Z]+)([1-9][0-9]*)', cell)
    if not match:
        raise ValueError(f'Invalid workbook cell reference: {cell}')
    column = 0
    for letter in match[1]:
        column = column * 26 + ord(letter) - ord('A') + 1
    return column, int(match[2])


def string_text(element):
    # Both plain and rich text; exclude phonetic annotations and formatting.
    return ''.join(t.text or '' for t in element.findall('m:t', NS) +
                   element.findall('m:r/m:t', NS))


class Sheet:
    def __init__(self, name, root, strings):
        self.name = name
        self.cells = {}
        self.merges = []
        for cell in root.findall('m:sheetData/m:row/m:c', NS):
            ref = cell.attrib['r']
            if ref in self.cells:
                raise ValueError(f'Duplicate cell: {name}!{ref}')
            if cell.find('m:f', NS) is not None:
                raise ValueError(f'Formula cell is not supported in this reference bank: {name}!{ref}')
            kind = cell.get('t')
            value = cell.find('m:v', NS)
            text = value.text or '' if value is not None else ''
            if kind == 's':
                try:
                    index = int(text)
                    if not 0 <= index < len(strings):
                        raise ValueError('Shared string index is out of range.')
                    text = strings[index]
                except (ValueError, IndexError):
                    raise ValueError(f'Invalid shared string: {name}!{ref}') from None
            elif kind == 'inlineStr':
                inline = cell.find('m:is', NS)
                text = string_text(inline) if inline is not None else ''
            elif kind not in (None, 'n', 'str'):
                raise ValueError(f'Unsupported cell storage {kind!r}: {name}!{ref}')
            self.cells[ref] = text
        for merge in root.findall('m:mergeCells/m:mergeCell', NS):
            start, end = merge.attrib['ref'].split(':')
            self.merges.append((*coordinate(start), *coordinate(end), start))

    def read(self, ref):
        column, row = coordinate(ref)
        anchor = ref
        for left, top, right, bottom, start in self.merges:
            if left <= column <= right and top <= row <= bottom:
                anchor = start
                break
        return self.cells.get(anchor, ''), {'sheet': self.name, 'cell': anchor}

    def required(self, ref):
        text, source = self.read(ref)
        if not text.strip():
            raise ValueError(f'Required cell is empty: {self.name}!{ref}')
        return text, source

    def rows(self):
        return sorted({coordinate(ref)[1] for ref, text in self.cells.items()
                       if text.strip() and coordinate(ref)[1] > 1})

    def headers(self, labels):
        for column, expected in labels.items():
            actual, _ = self.read(column + '1')
            if normalise(actual) != normalise(expected):
                raise ValueError(f'Incompatible header {self.name}!{column}1: expected {expected!r}, got {actual!r}')


def read_workbook(path):
    with ZipFile(path) as archive:
        relationships = {r.attrib['Id']: r for r in
                         ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}

        def part(rel):
            if rel.get('TargetMode') == 'External':
                raise ValueError('External workbook relationships are not supported.')
            target = rel.attrib['Target']
            return (target.lstrip('/') if target.startswith('/') else
                    posixpath.normpath(posixpath.join('xl', target)))

        shared = next((r for r in relationships.values()
                       if r.get('Type', '').endswith('/sharedStrings')), None)
        strings = ([string_text(si) for si in ET.fromstring(archive.read(part(shared)))]
                   if shared is not None else [])
        sheets = {}
        for sheet in ET.fromstring(archive.read('xl/workbook.xml')).findall('m:sheets/m:sheet', NS):
            name = sheet.attrib['name']
            key = normalise(name)
            if key in sheets:
                raise ValueError(f'Duplicate worksheet name: {name}')
            rel = relationships[sheet.attrib[REL_ID]]
            sheets[key] = Sheet(name, ET.fromstring(archive.read(part(rel))), strings)
        return sheets


def number(sheet, ref):
    text, _ = sheet.required(ref)
    if not re.fullmatch(r'[1-9][0-9]*', text):
        raise ValueError(f'Expected positive integer: {sheet.name}!{ref} = {text!r}')
    return int(text)



def import_bank(path):
    sheets = read_workbook(path)

    def sheet(name):
        if normalise(name) not in sheets:
            raise ValueError(f'Missing required worksheet: {name}')
        return sheets[normalise(name)]

    readme = sheet('Read me')
    scales = sheet('Scales per indicator')
    criteria = sheet("Indicators' assessment criteria")
    generic = sheet('TRL, ORL, CRL, SRL scales')
    notes = [{'text': text, 'source': {'sheet': readme.name, 'cell': ref}}
             for ref, text in readme.cells.items() if text.strip()]
    notice = ' '.join(n['text'] for n in notes)
    if 'Draft for validation by the consortium' not in notice or 'Task 3.2' not in notice:
        raise ValueError('Read me does not identify the expected Task 3.2 consortium-validation draft.')
    scales.headers(dict(zip('ABCDEFGHI', ('No.', 'SRA IAM indicator', 'What the indicator assesses', 'Level',
        'TRL – Technical profile', 'ORL – Organisational profile', 'CRL – Citizen profile', 'Validation status', 'Comments'))))
    criteria.headers(dict(zip('ABCDEF', ('No.', 'SRA IAM indicator', 'Definition – what the indicator assesses',
        'TRL assessment criterion (Technical profile)', 'ORL assessment criterion (Organisational profile)',
        'CRL assessment criterion (Citizen profile)'))))
    generic.headers(dict(zip('ABCDE', ('Level', 'Technology Readiness Level (TRL)',
        'Organisational Readiness Level (ORL)', 'Citizen Readiness Level (CRL)', 'Societal Readiness Level (SRL)'))))
    indicators = []
    for row in criteria.rows():
        n = number(criteria, f'A{row}')
        name, name_source = criteria.required(f'B{row}')
        definition, definition_source = criteria.required(f'C{row}')
        indicator = {'id': f'indicator-{n:02d}', 'number': n, 'name': name, 'definition': definition,
                     'source': {'number': criteria.read(f'A{row}')[1], 'name': name_source,
                                'definition': definition_source}, 'assessment_criteria': {}}
        for column, profile in zip('DEF', PROFILES):
            text, source = criteria.required(f'{column}{row}')
            indicator['assessment_criteria'][profile] = {'text': text, 'source': source}
        indicators.append(indicator)
    by_number = {i['number']: i for i in indicators}
    statements, review_rows = [], []
    for row in scales.rows():
        n = number(scales, f'A{row}')
        level = number(scales, f'D{row}')
        indicator = by_number.get(n)
        if indicator is None or scales.required(f'B{row}')[0] != indicator['name']:
            raise ValueError(f'Indicator identity mismatch: {scales.name}!A{row}:B{row}')
        definition = scales.read(f'C{row}')[0]
        if definition.strip() and definition != indicator['definition']:
            raise ValueError(f'Conflicting indicator definition: {scales.name}!C{row}')
        row_id = f"{indicator['id']}-level-{level}"
        status, status_source = scales.required(f'H{row}')
        comment, comment_source = scales.read(f'I{row}')
        review_rows.append({'id': row_id, 'indicator_id': indicator['id'], 'level': level,
                            'status': status, 'comment': comment,
                            'source': {'sheet': scales.name, 'row': row,
                                       'status_cell': status_source['cell'], 'comment_cell': comment_source['cell']}})
        for column, (profile, scale) in zip('EFG', PROFILES.items()):
            text, source = scales.required(f'{column}{row}')
            statements.append({'id': f"{indicator['id']}-{scale.lower()}-{level}",
                               'indicator_id': indicator['id'], 'profile': profile, 'scale': scale,
                               'level': level, 'statement': text, 'source': source, 'review_row_id': row_id})
    generic_scales = {scale: [] for scale in ('TRL', 'ORL', 'CRL', 'SRL')}
    for row in generic.rows():
        level = number(generic, f'A{row}')
        for column, scale in zip('BCDE', generic_scales):
            text, source = generic.required(f'{column}{row}')
            generic_scales[scale].append({'level': level, 'description': text, 'source': source})
    bank = {'schema_version': 'readiness-scale-bank-1.0.0', 'bank_version': 'fn-v4-1.0.0',
            'status': 'draft_for_consortium_validation_task_3_2', 'use': 'reference_only_not_scoring_policy',
            'source': {'document': path.name, 'sha256': sha256(path.read_bytes()).hexdigest()},
            'read_me': notes, 'profiles': PROFILES, 'indicators': sorted(indicators, key=lambda i: i['number']),
            'review_rows': review_rows, 'statements': statements, 'generic_scales': generic_scales}
    validate_bank(bank)
    return bank


def counts(bank):
    return {'indicators': len(bank['indicators']), 'statements': len(bank['statements']),
            'statements_per_profile': dict(Counter(s['profile'] for s in bank['statements'])),
            'levels_per_indicator_profile': sorted(set(Counter(
                (s['indicator_id'], s['profile']) for s in bank['statements']).values())),
            'assessment_criteria': sum(len(i['assessment_criteria']) for i in bank['indicators']),
            'generic_levels': {s: len(rows) for s, rows in bank['generic_scales'].items()},
            'shared_row_review_statuses': dict(Counter(r['status'] for r in bank['review_rows'])),
            'nonempty_row_comments': sum(bool(r['comment'].strip()) for r in bank['review_rows'])}


def inspect_bank(bank, indicator, profile):
    print(json.dumps({k: bank[k] for k in ('schema_version', 'bank_version', 'source', 'status', 'use')}, indent=2))
    print(json.dumps(counts(bank), indent=2))
    chosen = next((i for i in bank['indicators'] if normalise(indicator) in
                   {normalise(i['name']), i['id'], str(i['number'])}), None)
    if chosen is None:
        raise ValueError(f'Unknown indicator: {indicator}. Use its source name, number, or indicator-NN ID.')

    def show(label, text, source):
        print(f"\n{label} [{source['sheet']}!{source['cell']}]\n{text}")

    print(f"\n{chosen['id']}: {chosen['name']}")
    show('Definition', chosen['definition'], chosen['source']['definition'])
    for role, criterion in chosen['assessment_criteria'].items():
        show(f'{role} assessment criterion', criterion['text'], criterion['source'])
    reviews = {r['id']: r for r in bank['review_rows']}
    for record in sorted((s for s in bank['statements'] if s['indicator_id'] == chosen['id'] and
                          s['profile'] == profile), key=lambda s: s['level']):
        show(f"{record['scale']} {record['level']}", record['statement'], record['source'])
        review = reviews[record['review_row_id']]
        print(f"Shared row review [{review['source']['sheet']}!{review['source']['status_cell']}/"
              f"{review['source']['comment_cell']}]: {review['status']}; comment: {review['comment']!r}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build', help='Import and validate the private v4 workbook.')
    build.add_argument('--workbook', type=Path, default=WORKBOOK)
    build.add_argument('--output', type=Path, default=BANK)
    inspect = commands.add_parser('inspect', help='Print exact text from an already imported bank.')
    inspect.add_argument('--bank', type=Path, default=BANK)
    inspect.add_argument('--indicator', default='Noise')
    inspect.add_argument('--profile', choices=PROFILES, default='citizen')
    args = parser.parse_args()
    try:
        if args.command == 'build':
            bank = import_bank(args.workbook)
            # Source text must stay in the repository's existing ignored private area.
            if not args.output.resolve().is_relative_to((ROOT / 'references/private').resolve()):
                raise ValueError('Generated source text must be stored under references/private/.')
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(json.dumps({'output': str(args.output), 'source': bank['source'], 'status': bank['status'], **counts(bank)}, indent=2))
        else:
            inspect_bank(json.loads(args.bank.read_text(encoding='utf-8')), args.indicator, args.profile)
    except (OSError, ValueError, KeyError, BadZipFile, ET.ParseError) as exc:
        parser.exit(1, f'Readiness-scale import/inspection failed: {exc}\n')


if __name__ == '__main__':
    main()
