"""The raw rate-replicate repository on the custody-scoped store: population from a retained table of sampling
units, the saved sheet read back and its requested cells projected, through the real runner."""
from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

HEADER = ('subject', 'experiment', 'arm', 'condition', 'endpoint', 'normalization', 'sampling_unit',
          'sampling_basis', 'observation_id', 'value', 'unit', 'origin')


def row(arm, condition, unit, value):
    return ('GeneX', 'assay1', arm, condition, 'rate', 'per mg', unit, 'biological_preparations',
            arm + unit, value, 'umol/min', 'reported')


ROWS = (row('reference', 'wild type', 'u1', '10'), row('reference', 'wild type', 'u2', '12'),
        row('reference', 'wild type', 'u3', '11'), row('test', 'mutant', 'v1', '4'),
        row('test', 'mutant', 'v2', '5'), row('test', 'mutant', 'v3', '3'))
TABLE = '\n'.join('\t'.join(fields) for fields in (HEADER, *ROWS)) + '\n'
GROUP = {'arm': 'reference', 'condition': 'wild type', 'endpoint': 'rate', 'normalization': 'per mg'}
ARGUMENTS = {'source_representation': 'original', 'table_kind': 'primary_table', 'delimiter': '\t',
             'subject': 'GeneX', 'experiment': 'assay1', 'reference': GROUP,
             'test': {'arm': 'test', 'condition': 'mutant', 'endpoint': 'rate', 'normalization': 'per mg'},
             'unit_model': 'iid_units', 'dependence': 'independent'}
REPOSITORY = 'literature_rate_replicate_storage:LiteratureRateReplicateRepository'
REQUESTED = 'requested_rate_replicate_components'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}


def test_a_replicate_sheet_is_saved_read_back_and_its_cells_projected(world):  # noqa: F811
    table, artifact = source(world, TABLE, 'text/tab-separated-values')
    components = ['reference_rate', 'test_rate', 'rate_difference']
    populate = call(REPOSITORY, 'populate', {**ARGUMENTS, 'source_ref': table}, scope=world['scope'],
                    assignment={REQUESTED: components})
    populate['arguments']['role'] = 'reader'
    populated, held, saved, cells = run(world, 'replicate', [populate,
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET], components=components),
    ], held=[table, artifact])
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and held == [sheet]
    assert saved['input_source_ref'] == table
    assert [(cell['component'], cell['sheet_ref']) for cell in cells] == [(name, sheet) for name in components]
    assert populated['result']['cells'] == cells
