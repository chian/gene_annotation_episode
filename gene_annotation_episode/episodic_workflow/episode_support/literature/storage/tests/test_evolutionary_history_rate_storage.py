"""The rate sheet repository on the custody-scoped store: population from a retained table, the saved sheet read
back, its cells projected, and the dependency tables of the sheet updates, through the real runner."""
from .evolutionary_history_world import call, function, read, run, source, world  # noqa: F401

HEADER = ('subject', 'experiment', 'arm', 'condition', 'endpoint', 'normalization', 'value', 'unit',
          'uncertainty_kind', 'uncertainty_magnitude', 'count', 'sampling_basis', 'origin')
ROWS = (('GeneX', 'assay1', 'reference', 'wild type', 'rate', 'per mg', '10', 'umol/min', 'sd', '1', '3',
         'biological_preparations', 'reported'),
        ('GeneX', 'assay1', 'test', 'mutant', 'rate', 'per mg', '4', 'umol/min', 'sd', '1', '3',
         'biological_preparations', 'reported'))
TABLE = '\n'.join('\t'.join(row) for row in (HEADER, *ROWS)) + '\n'
ARGUMENTS = {'source_representation': 'original', 'table_kind': 'primary_table', 'delimiter': '\t',
             'subject': 'GeneX', 'experiment': 'assay1', 'reference_arm': 'reference', 'test_arm': 'test',
             'reference_condition': 'wild type', 'test_condition': 'mutant', 'dependence': 'unknown',
             'observation_model': 'none'}
REPOSITORY = 'literature_rate_storage:LiteratureRateRepository'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}


def test_a_rate_sheet_is_saved_read_back_and_projected(world):
    table, artifact = source(world, TABLE, 'text/tab-separated-values')
    arguments = {**ARGUMENTS, 'source_ref': table}
    populated, held, saved, cells = run(world, 'rate', [
        call(REPOSITORY, 'populate', arguments, scope=world['scope']),
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET], components=['reference_rate', 'rate_difference'])], held=[table, artifact])
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and held == [sheet]
    assert populated['result']['cells']['reference_rate']['value'] == 10.0
    assert populated['result']['cells']['rate_difference']['value'] == 6.0
    assert saved['input_source_ref'] == table
    assert [(row['component'], row['value']) for row in cells] == [('reference_rate', 10.0), ('rate_difference', 6.0)]
    assert {row['sheet_ref'] for row in cells} == {sheet}


def test_the_saved_sheet_is_registered_as_the_current_version_of_its_family(world):
    table, artifact = source(world, TABLE, 'text/tab-separated-values')
    populated, current = run(world, 'rate_updates', [
        call(REPOSITORY, 'populate', {**ARGUMENTS, 'source_ref': table}, scope=world['scope']),
        function('literature_sheet_updates', 'current_sheet_refs')], held=[table, artifact])
    assert current == [populated['result']['sheet_ref']]
