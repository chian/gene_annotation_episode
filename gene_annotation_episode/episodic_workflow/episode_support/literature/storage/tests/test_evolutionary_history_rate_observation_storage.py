"""The reported rate-observation repository on the custody-scoped store: population from the cells of a retained
workbook, the saved sheet read back and its cells projected, through the real runner."""
import io
import zipfile

from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

REPOSITORY = 'literature_rate_observation_storage:LiteratureRateObservationRepository'
REQUESTED = 'requested_rate_observation_components'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
STRINGS = ('Panel A', 'GeneX', 'umol/min', 'Wild type', 'rep 1', 'rep 2', 'Mutant', 'rep 3', 'rep 4')
CELLS = {'A1': 'Panel A', 'B1': 'GeneX', 'C1': 'umol/min', 'A2': 'Wild type', 'A3': 'rep 1', 'B3': 10,
         'A4': 'rep 2', 'B4': 12, 'A5': 'Mutant', 'A6': 'rep 3', 'B6': 4, 'A7': 'rep 4', 'B7': 5}


def workbook():
    """The bytes of a one-sheet workbook with the cells of CELLS (strings shared, numbers plain)."""
    rows = {}
    for address, value in CELLS.items():
        rows.setdefault(int(address[1:]), []).append(
            f'<c r="{address}" t="s"><v>{STRINGS.index(value)}</v></c>' if isinstance(value, str)
            else f'<c r="{address}"><v>{value}</v></c>')
    sheet = ('<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             '<sheetData>' + ''.join(f'<row r="{number}">{"".join(cells)}</row>' for number, cells in sorted(rows.items()))
             + '</sheetData></worksheet>')
    strings = ('<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
               f'count="{len(STRINGS)}" uniqueCount="{len(STRINGS)}">' + ''.join(f'<si><t>{text}</t></si>' for text in STRINGS) + '</sst>')
    main = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    parts = {
        '[Content_Types].xml': '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>',
        '_rels/.rels': '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{main}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': f'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            f'xmlns:r="{main}"><sheets><sheet name="Data" sheetId="1" r:id="rId1"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{main}/worksheet" Target="worksheets/sheet1.xml"/>'
            f'<Relationship Id="rId2" Type="{main}/sharedStrings" Target="sharedStrings.xml"/></Relationships>',
        'xl/worksheets/sheet1.xml': sheet, 'xl/sharedStrings.xml': strings}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, text in parts.items():
            archive.writestr(name, text)
    return buffer.getvalue()


def label(cell):
    return {'cell': cell, 'expected_text': CELLS[cell]}


def arguments(source_ref):
    return {'source_ref': source_ref, 'source_kind': 'synthetic_fixture', 'worksheet': 'Data',
            'panel': label('A1'), 'subject': label('B1'), 'native_unit': label('C1'),
            'groups': [{'label': label('A2'), 'observations': [{'label': label('A3'), 'value_cell': 'B3'},
                                                                 {'label': label('A4'), 'value_cell': 'B4'}]},
                       {'label': label('A5'), 'observations': [{'label': label('A6'), 'value_cell': 'B6'},
                                                                 {'label': label('A7'), 'value_cell': 'B7'}]}],
            'reference_group': 'Wild type', 'test_group': 'Mutant'}


def test_an_observation_sheet_is_saved_read_back_and_its_cells_projected(world):  # noqa: F811
    table, artifact = source(world, workbook(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    populate = call(REPOSITORY, 'populate', arguments(table), scope=world['scope'])
    populate['arguments']['role'] = 'reader'
    populate['arguments']['assignment'] = {REQUESTED: ['reference_rate', 'test_rate']}
    populated, held, saved, cells = run(world, 'observation', [populate,
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET], components=['reference_rate', 'test_rate'])], held=[table, artifact])
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and held == [sheet]
    assert saved['input_source_ref'] == table
    assert [(cell['component'], cell['sheet_ref']) for cell in cells] == [('reference_rate', sheet), ('test_rate', sheet)]
    assert populated['result']['cells'] == cells
