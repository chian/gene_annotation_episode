"""XLSX representation checks; no model or biological conclusion is asserted."""
import zipfile

import pytest

from gene_annotation_episode.spreadsheet_tools import read_workbook


def workbook(tmp_path, *, bad_string=False, truncated=False):
    path = tmp_path/'fixture.xlsx'
    extra = ('<row r="3"><c r="A3" t="s"><v>999</v></c><c r="B3"><v>3</v></c></row>'
        if bad_string else '<row r="3"><c r="A3" t="inlineStr"><is><t>other</t></is></c></row>')
    worksheet = ('<worksheet><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>gene</t></is></c></row>'
        '<row r="2"><c r="A2" t="s"><v>0</v></c><c r="B2"><f>1+1</f><v>2</v></c>'
        '<c r="C2" s="2"><v>42344</v></c></row>' +
        ('<row r="3"><c r="A3">' if truncated else extra+'</sheetData></worksheet>'))
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('_rels/.rels', '<Relationships><Relationship Id="office" '
            'Type="http://example/officeDocument" Target="book/workbook.xml"/></Relationships>')
        archive.writestr('book/workbook.xml', '<workbook xmlns:r="http://example/relationships">'
            '<workbookPr date1904="1"/><sheets><sheet name="Evidence" sheetId="99" r:id="selected"/></sheets></workbook>')
        archive.writestr('book/_rels/workbook.xml.rels', '<Relationships>'
            '<Relationship Id="selected" Type="http://example/worksheet" Target="sheets/evidence.xml"/>'
            '<Relationship Id="strings" Type="http://example/sharedStrings" Target="shared.xml"/></Relationships>')
        archive.writestr('book/shared.xml', '<sst><si><r><t>YB</t></r><r><t>HP</t></r>'
            '<rPh><t>phonetic annotation is not visible text</t></rPh></si></sst>')
        archive.writestr('book/sheets/evidence.xml', worksheet)
    scratch = tmp_path/'scratch'
    scratch.mkdir()
    return path, scratch


def replace_part(path, name, before, after):
    with zipfile.ZipFile(path) as archive:
        parts = [(entry.filename, archive.read(entry)) for entry in archive.infolist()]
    with zipfile.ZipFile(path, 'w') as archive:
        for key, content in parts:
            archive.writestr(key, content.replace(before.encode(), after.encode()) if key == name else content)


def test_relationship_identity_formula_cache_and_original_numeric_cells(tmp_path):
    path, scratch = workbook(tmp_path)
    inventory = read_workbook(path, 'sheets', {}, scratch)
    sheet, = inventory['sheets']
    assert sheet['sheet_key'] == 'selected' and sheet['native_sheet_id'] == '99'
    assert sheet['worksheet_part'] == 'book/sheets/evidence.xml'
    result = read_workbook(path, 'rows', {'sheet_key': 'selected', 'offset': 0, 'limit': 1,
        'where': {'column': 'A', 'match': 'equals', 'value': 'ybhp', 'case_sensitive': False},
        'header_row': 1}, scratch)
    assert result['status'] == 'completed' and result['total_matches'] == 1
    assert result['date_system'] == '1904' and result['header']['row_number'] == 1
    row, = result['rows']
    cells = {cell['address']: cell for cell in row['cells']}
    assert cells['A2']['value'] == 'YBHP'
    assert cells['B2']['formula']['text'] == '1+1'
    assert cells['B2']['value'] == '2' and cells['B2']['value_is_formula_cache'] is True
    assert cells['C2']['value'] == '42344' and cells['C2']['style_index'] == '2'


@pytest.mark.parametrize('bad_string,truncated', [(True, False), (False, True)])
def test_source_errors_preserve_completed_rows_and_known_cells(tmp_path, bad_string, truncated):
    path, scratch = workbook(tmp_path, bad_string=bad_string, truncated=truncated)
    result = read_workbook(path, 'rows', {'sheet_key': 'selected', 'offset': 0, 'limit': 10}, scratch)
    assert result['status'] == 'partial' and result['complete'] is False
    assert result['total_matches'] is None
    assert result['rows'][1]['cells'][0]['value'] == 'YBHP'
    if bad_string:
        assert result['cell_error_count'] == 1
        assert result['rows'][2]['cells'][0]['error'] == 'xlsx_shared_string_reference_unresolved'
        assert result['rows'][2]['cells'][1]['value'] == '3'
    else:
        assert [row['row_number'] for row in result['rows']] == [1, 2]
        assert result['parse_failures'][0]['package_part'] == 'book/sheets/evidence.xml'


def test_ambiguous_relationship_does_not_select_a_candidate_or_hide_valid_sibling(tmp_path):
    path, scratch = workbook(tmp_path)
    replace_part(path, 'book/_rels/workbook.xml.rels', '</Relationships>',
        '<Relationship Id="selected" Type="http://example/worksheet" Target="wrong.xml"/>'
        '<Relationship Id="other" Type="http://example/worksheet" Target="sheets/evidence.xml"/></Relationships>')
    replace_part(path, 'book/workbook.xml', '</sheets>',
        '<sheet name="Other" sheetId="100" r:id="other"/></sheets>')
    inventory = read_workbook(path, 'sheets', {}, scratch)
    ambiguous, valid = inventory['sheets']
    assert ambiguous['available'] is False
    assert ambiguous['worksheet_part'] is None
    assert ambiguous['failure_code'] == 'xlsx_relationship_id_ambiguous'
    assert valid['available'] is True
    result = read_workbook(path, 'rows', {'sheet_key': 'other', 'offset': 0, 'limit': 2}, scratch)
    assert result['status'] == 'completed'
    assert result['rows'][1]['cells'][0]['value'] == 'YBHP'


def test_ambiguous_strings_preserve_numeric_and_inline_cells_without_guessing(tmp_path):
    path, scratch = workbook(tmp_path)
    replace_part(path, 'book/_rels/workbook.xml.rels', '</Relationships>',
        '<Relationship Id="otherStrings" Type="http://example/sharedStrings" Target="wrong.xml"/></Relationships>')
    result = read_workbook(path, 'rows', {'sheet_key': 'selected', 'offset': 0, 'limit': 3}, scratch)
    assert result['status'] == 'partial'
    assert result['parse_failures'] == [{'code': 'xlsx_shared_strings_relationship_ambiguous'}]
    assert result['rows'][0]['cells'][0]['value'] == 'gene'
    assert result['rows'][1]['cells'][0]['value'] is None
    assert result['rows'][1]['cells'][1]['value'] == '2'


@pytest.mark.parametrize('replacement,raw,status', [('<row>', None, 'completed'),
    ('<row r="bad">', 'bad', 'partial')])
def test_unknown_row_number_retains_prior_rows_and_actual_cell_addresses(tmp_path, replacement, raw, status):
    path, scratch = workbook(tmp_path)
    replace_part(path, 'book/sheets/evidence.xml', '<row r="3">', replacement)
    result = read_workbook(path, 'rows', {'sheet_key': 'selected', 'offset': 0, 'limit': 3}, scratch)
    assert result['status'] == status
    assert result['rows'][1]['cells'][0]['value'] == 'YBHP'
    last = result['rows'][2]
    assert last['row_number'] is None and last['row_number_raw'] == raw
    assert last['row_ordinal'] == 3 and last['cells'][0]['address'] == 'A3'
    assert last['cells'][0]['value'] == 'other'
    assert result['header'] is None
