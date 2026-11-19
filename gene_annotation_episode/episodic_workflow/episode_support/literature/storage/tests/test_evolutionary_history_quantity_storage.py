"""The reported-quantity sheet repository on the custody-scoped store: population from a JATS paragraph, the saved
sheet read back and projected, and the transport repository's read of a saved apparent Km, through the real runner."""
from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

JATS = ('<article><body><sec id="s1"><p id="p1">GeneX showed a specific activity of 12.5 ± 1.5 umol/min/mg '
        'in the assay.</p><p id="p2">GeneX has an apparent Km = 40 ± 4 uM for ATP in the assay.</p></sec></body></article>')
QUANTITY = 'literature_quantity_storage:LiteratureQuantityRepository'
TRANSPORT = 'literature_transport_storage:LiteratureTransportRepository'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}


def arguments(table, paragraph, quantity, analyte):
    return {'source_ref': table, 'source_kind': 'primary_jats', 'section_id': 's1', 'paragraph_id': paragraph,
            'subject': 'GeneX', 'quantity': quantity, 'analyte': analyte}


def test_a_specific_activity_sheet_is_saved_read_back_and_projected(world):
    table, artifact = source(world, JATS, 'application/xml')
    populated, held, saved, cells = run(world, 'quantity', [
        call(QUANTITY, 'populate', arguments(table, 'p1', 'specific_activity', None), scope=world['scope']),
        read(QUANTITY, 'held_sheet_refs'),
        read(QUANTITY, 'read', SHEET),
        read(QUANTITY, 'project_cells', [SHEET], components=['reported_value', 'reported_spread', 'relative_reported_spread'])],
        held=[table, artifact])
    sheet = populated['result']['sheet_ref']
    assert held == [sheet] and saved['input_source_ref'] == table
    assert [(row['component'], row['value']) for row in cells] == [
        ('reported_value', 12.5), ('reported_spread', 1.5), ('relative_reported_spread', 0.12)]
    assert {row['sheet_ref'] for row in cells} == {sheet}


def test_the_transport_repository_reads_a_saved_apparent_km(world):
    table, artifact = source(world, JATS, 'application/xml')
    populated, km = run(world, 'quantity_km', [
        call(QUANTITY, 'populate', arguments(table, 'p2', 'apparent_km', 'ATP'), scope=world['scope']),
        read(TRANSPORT, '_quantity', SHEET)], held=[table, artifact])
    assert km['sheet']['extraction']['value'] == 40.0 and km['sheet']['extraction']['unit'] == 'uM'
    assert km['input_source_ref'] == table
