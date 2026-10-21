"""Authored OOXML fixtures only; no private source statements in this suite."""
from copy import deepcopy
from pathlib import Path
import runpy
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest

MODULE = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/import-readiness-scales.py'))
import_bank = MODULE['import_bank']
validate_bank = MODULE['validate_bank']
NS = MODULE['NS']['m']
RNS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PNS = 'http://schemas.openxmlformats.org/package/2006/relationships'


def fixture_workbook(path, storage='shared', merged=False, change=None):
    """Generate the minimum full structural fixture, with shuffled part names/order."""
    criteria_headers = ('No.', 'SRA IAM indicator', 'Definition – what the indicator assesses',
                        'TRL assessment criterion (Technical profile)',
                        'ORL assessment criterion (Organisational profile)',
                        'CRL assessment criterion (Citizen profile)')
    scale_headers = ('No.', 'SRA IAM indicator', 'What the indicator assesses', 'Level',
                     'TRL – Technical profile', 'ORL – Organisational profile',
                     'CRL – Citizen profile', 'Validation status', 'Comments')
    generic_headers = ('Level', 'Technology Readiness Level (TRL)', 'Organisational Readiness Level (ORL)',
                       'Citizen Readiness Level (CRL)', 'Societal Readiness Level (SRL)')
    criteria = {f'{col}1': text for col, text in zip('ABCDEF', criteria_headers)}
    scales = {f'{col}1': text for col, text in zip('ABCDEFGHI', scale_headers)}
    generic = {f'{col}1': text for col, text in zip('ABCDE', generic_headers)}
    merges = []
    for n in range(1, 16):
        r = n + 1
        criteria.update({f'A{r}': n, f'B{r}': f'Indicator {n}', f'C{r}': f'Definition {n}'})
        for col, profile in zip('DEF', MODULE['PROFILES']):
            criteria[f'{col}{r}'] = f'{profile} criterion {n}'
        start = 2 + (n - 1) * 9
        if merged:
            merges.extend(f'{col}{start}:{col}{start + 8}' for col in 'ABC')
        for level in range(1, 10):
            row = start + level - 1
            if not merged or level == 1:
                scales.update({f'A{row}': n, f'B{row}': f'Indicator {n}'})
            if level == 1:
                scales[f'C{row}'] = f'Definition {n}'
            scales.update({f'D{row}': level, f'H{row}': 'To review', f'I{row}': ''})
            for col, scale in zip('EFG', ('TRL', 'ORL', 'CRL')):
                scales[f'{col}{row}'] = f'  Synthetic {n}/{scale}/{level}: punctuation — ’.\nSecond line.  '
    for level in range(1, 10):
        generic[f'A{level + 1}'] = level
        for col, scale in zip('BCDE', ('TRL', 'ORL', 'CRL', 'SRL')):
            generic[f'{col}{level + 1}'] = f'Synthetic generic {scale} {level}'
    if change:
        change(scales, criteria, generic)
    # Neither worksheet positions nor relationship IDs encode their meanings.
    sheets = [
        ('TRL, ORL, CRL,  SRL scales', 'generic', generic, []),
        ("Indicators' assessment criteria", 'criteria', criteria, []),
        ('Read me', 'notice', {'A1': 'Synthetic fixture. Draft for validation by the consortium (Task 3.2).'}, []),
        ('Scales per indicator', 'anchors', scales, merges),
    ]
    strings = []
    workbook = ET.Element(f'{{{NS}}}workbook')
    sheet_list = ET.SubElement(workbook, f'{{{NS}}}sheets')
    rels = ET.Element(f'{{{PNS}}}Relationships')
    with ZipFile(path, 'w') as archive:
        for name, slug, cells, merged_ranges in sheets:
            ET.SubElement(sheet_list, f'{{{NS}}}sheet', {'name': name, f'{{{RNS}}}id': slug})
            target = '/xl/worksheets/generic.xml' if slug == 'generic' else f'worksheets/{slug}.xml'
            ET.SubElement(rels, f'{{{PNS}}}Relationship', Id=slug, Target=target, Type=RNS + '/worksheet')
            root = ET.Element(f'{{{NS}}}worksheet')
            data = ET.SubElement(root, f'{{{NS}}}sheetData')
            rows = {}
            for ref, text in cells.items():
                row = MODULE['coordinate'](ref)[1]
                if row not in rows:
                    rows[row] = ET.SubElement(data, f'{{{NS}}}row', r=str(row))
                cell = ET.SubElement(rows[row], f'{{{NS}}}c', r=ref)
                if isinstance(text, int):
                    ET.SubElement(cell, f'{{{NS}}}v').text = str(text)
                elif storage == 'inline':
                    cell.set('t', 'inlineStr')
                    ET.SubElement(ET.SubElement(cell, f'{{{NS}}}is'), f'{{{NS}}}t').text = text
                else:
                    cell.set('t', 's')
                    ET.SubElement(cell, f'{{{NS}}}v').text = str(len(strings))
                    strings.append(text)
            if merged_ranges:
                merge_list = ET.SubElement(root, f'{{{NS}}}mergeCells')
                for ref in merged_ranges:
                    ET.SubElement(merge_list, f'{{{NS}}}mergeCell', ref=ref)
            archive.writestr(f'xl/worksheets/{slug}.xml', ET.tostring(root))
        if storage != 'inline':
            ET.SubElement(rels, f'{{{PNS}}}Relationship', Id='strings', Target='words.xml', Type=RNS + '/sharedStrings')
            shared = ET.Element(f'{{{NS}}}sst')
            for text in strings:
                item = ET.SubElement(shared, f'{{{NS}}}si')
                if storage == 'rich':
                    for half in (text[:len(text)//2], text[len(text)//2:]):
                        ET.SubElement(ET.SubElement(item, f'{{{NS}}}r'), f'{{{NS}}}t').text = half
                    ET.SubElement(ET.SubElement(item, f'{{{NS}}}rPh'), f'{{{NS}}}t').text = 'phonetic-not-source-text'
                else:
                    ET.SubElement(item, f'{{{NS}}}t').text = text
            archive.writestr('xl/words.xml', ET.tostring(shared))
        archive.writestr('xl/workbook.xml', ET.tostring(workbook))
        archive.writestr('xl/_rels/workbook.xml.rels', ET.tostring(rels))
    return path


@pytest.mark.parametrize('storage,merged', [('shared', False), ('inline', True), ('rich', True)])
def test_lossless_mapping_relationships_and_shared_review_rows(tmp_path, capsys, storage, merged):
    path = fixture_workbook(tmp_path / 'synthetic.xlsx', storage, merged)
    bank = import_bank(path)
    assert MODULE['counts'](bank) == {
        'indicators': 15, 'statements': 405,
        'statements_per_profile': {'technical': 135, 'organisational': 135, 'citizen': 135},
        'levels_per_indicator_profile': [9], 'assessment_criteria': 45,
        'generic_levels': {'TRL': 9, 'ORL': 9, 'CRL': 9, 'SRL': 9},
        'shared_row_review_statuses': {'To review': 135}, 'nonempty_row_comments': 0}
    assert bank == import_bank(path)
    assert bank['indicators'][6]['assessment_criteria']['citizen']['source']['cell'] == 'F8'
    rows = [r for r in bank['statements'] if r['indicator_id'] == 'indicator-07' and r['profile'] == 'citizen']
    assert [r['source']['cell'] for r in rows] == [f'G{r}' for r in range(56, 65)]
    for row in rows:
        assert row['scale'] == 'CRL'
        assert row['statement'] == f"  Synthetic 7/CRL/{row['level']}: punctuation — ’.\nSecond line.  "
    assert len({s['review_row_id'] for s in bank['statements']}) == 135
    assert all('status' not in s for s in bank['statements'])
    MODULE['inspect_bank'](bank, 'Indicator 7', 'citizen')
    printed = capsys.readouterr().out
    assert 'G56' in printed and 'G64' in printed and rows[-1]['statement'] in printed
    assert 'technical assessment criterion' in printed and 'organisational assessment criterion' in printed


@pytest.mark.parametrize('cell,area', [('G56', 0), ('F8', 1), ('E10', 2), ('H56', 0)])
def test_rejects_missing_statement_criterion_generic_or_status(tmp_path, cell, area):
    path = fixture_workbook(tmp_path / 'missing.xlsx', change=lambda *tables: tables[area].pop(cell))
    with pytest.raises(ValueError, match='Required cell is empty'):
        import_bank(path)


def test_rejects_incompatible_profile_columns_and_conflicting_definitions(tmp_path):
    for cell, text, error in [('G1', 'Different profile', 'Incompatible header'),
                              ('C56', 'Different definition', 'Conflicting indicator definition')]:
        path = fixture_workbook(tmp_path / 'incompatible.xlsx', change=lambda scales, *_: scales.update({cell: text}))
        with pytest.raises(ValueError, match=error):
            import_bank(path)


def test_rejects_duplicate_or_incomplete_levels_and_indicators(tmp_path):
    bank = import_bank(fixture_workbook(tmp_path / 'complete.xlsx'))
    duplicate = deepcopy(bank)
    duplicate['statements'][1] = deepcopy(duplicate['statements'][0])
    with pytest.raises(ValueError, match='Duplicate indicator/profile/level'):
        validate_bank(duplicate)
    bank['generic_scales']['SRL'][-1]['level'] = 1
    with pytest.raises(ValueError, match='Incomplete or duplicate generic SRL'):
        validate_bank(bank)
    for cell, value in [('D57', 1), ('A16', 14)]:
        area = 0 if cell.startswith('D') else 1
        path = fixture_workbook(tmp_path / 'duplicate.xlsx', change=lambda *tables: tables[area].update({cell: value}))
        with pytest.raises(ValueError):
            import_bank(path)


def test_rejects_incomplete_statement_matrix(tmp_path):
    bank = import_bank(fixture_workbook(tmp_path / 'complete.xlsx'))
    bank['statements'].pop()
    with pytest.raises(ValueError, match='Expected 405 statements'):
        validate_bank(bank)
