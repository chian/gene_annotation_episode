"""The assay sheet repository on the custody-scoped store: population from quoted source operands, the saved sheet
read back and its cells projected, through the real runner."""
from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

TEXT = 'The rate q was 5 uM/min in the assay.'
ASSAY = 'literature_assay_storage:LiteratureAssayRepository'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}


def arguments(table):
    start = TEXT.index('5 uM/min')
    nothing = {'value': 'unknown', 'witnesses': []}
    return {'source_ref': table, 'source_kind': 'synthetic_fixture',
            'assay': {**dict.fromkeys(('molecule', 'organism', 'genotype', 'construct', 'preparation', 'condition',
                                       'intended_variable', 'experimental_system', 'expression_host',
                                       'measured_entity', 'asserted_input', 'asserted_output')),
                      'endpoint': nothing, 'arrangement': nothing},
            'primitives': {**dict.fromkeys(('g', 'k', 'E', 'u', 'v')),
                           'q': {'witness': {'source_ref': table, 'representation': 'original',
                                             'start': start, 'end': start + len('5 uM/min')},
                                 'number_start': 0, 'number_end': 1, 'unit_start': 2, 'unit_end': 8}},
            'covariance_source_ref': None, 'distinct_residual_variance': None, 'variance_status': 'unknown',
            'observation_model': 'none', 'model_witnesses': []}


def test_an_assay_sheet_is_saved_read_back_and_projected(world):
    table, artifact = source(world, TEXT)
    populated, held, saved, cells = run(world, 'assay', [
        call(ASSAY, 'populate', arguments(table), scope=world['scope']),
        read(ASSAY, 'held_sheet_refs'),
        read(ASSAY, 'read', SHEET),
        read(ASSAY, 'project_cells', [SHEET], components=['net_rate'])], held=[table, artifact])
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and held == [sheet]
    assert saved['input_source_ref'] == table
    assert [(row['component'], row['value']) for row in cells] == [('net_rate', 5.0)]
    assert cells[0]['sheet_ref'] == sheet and cells[0]['endpoint_kind'] == 'unknown'
