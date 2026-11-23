"""The binding parameter repository on the custody-scoped store: population from a retained primary table, the
saved sheet read back, and its cells projected, through the real runner."""
import json

from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

REPOSITORY = 'literature_binding_storage:LiteratureBindingRepository'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}


def table():
    def row(ligand, expression, index):
        return {'subject': 'GeneX', 'state': 'apo', 'experiment': 'competition', 'ligand': ligand,
                'expression': expression, 'locator': {'row_index': index, 'column': 'IC50'}}
    return json.dumps({'version': 'binding_parameter_table', 'table_id': 'table 1', 'parameter_kind': 'ic50',
                       'unit': 'nM', 'uncertainty_basis': 'fit_to_averaged_curve', 'minimum_experiment_count': 3,
                       'rows': [row('ligand A', '40 ± 4', 0), row('ligand B', '120', 1)]})


def arguments(source_ref):
    return {'source_ref': source_ref, 'representation': 'primary_table', 'subject': 'GeneX', 'state': 'apo',
            'experiment': 'competition', 'reference_ligand': 'ligand A', 'test_ligand': 'ligand B',
            'parameter_kind': 'ic50', 'design': 'unknown', 'protein_arrangement': 'unknown',
            'interpretation_witnesses': []}


def test_a_binding_sheet_is_saved_read_back_and_projected(world):
    reference, artifact = source(world, table(), 'application/json')
    populated, held, saved, cells = run(world, 'binding', [
        call(REPOSITORY, 'populate', arguments(reference), scope=world['scope']),
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET], components=['reference_parameter', 'native_parameter_ratio'])],
        held=[reference, artifact])
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and held == [sheet]
    assert saved['input_source_ref'] == reference
    assert [(row['component'], row['value']) for row in cells] == [('reference_parameter', 40.0),
                                                                    ('native_parameter_ratio', 3.0)]
    assert {row['sheet_ref'] for row in cells} == {sheet}
    assert populated['result']['cells']['reference_parameter']['value'] == 40.0
