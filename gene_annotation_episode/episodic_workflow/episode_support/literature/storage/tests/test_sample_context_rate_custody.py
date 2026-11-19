"""The rate sheet repository of the sample-context family through the real runner: a sheet is saved from a retained
table, read back, projected, registered as the current version of its family, and its cells are rows another
Episode can be given."""
from .literature_world import run, step, world  # noqa: F401

HEADER = ('subject', 'experiment', 'arm', 'condition', 'endpoint', 'normalization', 'value', 'unit',
          'uncertainty_kind', 'uncertainty_magnitude', 'count', 'sampling_basis', 'origin')
ROWS = (('GeneX', 'assay1', 'reference', 'wild type', 'rate', 'per mg', '10', 'umol/min', 'sd', '1', '3',
         'biological_preparations', 'reported'),
        ('GeneX', 'assay1', 'test', 'mutant', 'rate', 'per mg', '4', 'umol/min', 'sd', '1', '3',
         'biological_preparations', 'reported'))
TABLE = '\n'.join('\t'.join(row) for row in (HEADER, *ROWS)) + '\n'
POPULATION = {'source_representation': 'original', 'table_kind': 'primary_table', 'delimiter': '\t',
              'subject': 'GeneX', 'experiment': 'assay1', 'reference_arm': 'reference', 'test_arm': 'test',
              'reference_condition': 'wild type', 'test_condition': 'mutant', 'dependence': 'unknown',
              'observation_model': 'none'}
COMPONENTS = ['reference_rate', 'rate_difference']


def retained_table(world):
    """The source record of the table, as an earlier acquisition left it, and the problem it is read for."""
    store = world['store']
    target, = store.create_problem(raw_sequence='MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ', molecule='protein')['subject_refs']
    artifact = store.artifact(TABLE, 'text/tab-separated-values')
    source = store.put('source', {'provider': 'test', 'accession': None, 'uri': None, 'artifact_ref': artifact,
                                  'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None},
                       origin='external')['id']
    return {'scope': {'subject_refs': [target]}, 'source': source, 'held': [target, artifact, source]}


def test_a_rate_sheet_is_saved_read_back_projected_and_registered(world):
    fixture = retained_table(world)
    common = dict(scope=fixture['scope'], requested=[])
    _, units = run(world, 'rate', [
        step('rate_populate', population={**POPULATION, 'source_ref': fixture['source']}, **common),
        step('rate_look', components=COMPONENTS, **common)], fixture['held'])
    populated, looked = units[0]['outcome']['outcome'], units[1]['outcome']
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed'
    assert populated['result']['cells']['reference_rate']['value'] == 10.0
    assert populated['result']['cells']['rate_difference']['value'] == 6.0
    # The sheet and the rows of its operation and cells are what the unit produced; the Episode owns the sheet.
    assert sheet in units[0]['produced'] and sum(ref.startswith('row_') for ref in units[0]['produced']) == 1 + 10
    assert looked['owned'] == [sheet] and looked['saved'] == [fixture['source']]
    assert [(row['component'], row['value']) for row in looked['cells']] == [('reference_rate', 10.0), ('rate_difference', 6.0)]
    assert looked['facts'] == looked['cells']
    assert len(looked['cell_rows']) == 10 and looked['received'] == [] and looked['source_view'] == [sheet]
    # A rate sheet is not an A108 sheet: the dependency updates do not register it.
    assert looked['registered'] == []


def test_another_episode_given_a_cell_row_holds_that_cell_and_does_not_own_the_sheet(world):
    fixture = retained_table(world)
    common = dict(scope=fixture['scope'], requested=[])
    _, units = run(world, 'rate_owner', [
        step('rate_populate', population={**POPULATION, 'source_ref': fixture['source']}, **common),
        step('rate_look', components=COMPONENTS, **common)], fixture['held'])
    sheet = units[0]['outcome']['outcome']['result']['sheet_ref']
    cell_rows = units[1]['outcome']['cell_rows']
    given = [ref for ref in cell_rows[:1]]
    _, received = run(world, 'rate_receiver', [
        step('rate_foreign', sheet_ref=sheet, components=['reference_rate'], **common)], given)
    seen = received[0]['outcome']
    assert seen['owns'] is False
    assert [(cell['sheet_ref'], cell['component']) for cell in seen['received']] == [(sheet, 'reference_rate')]
    assert seen['facts'] == seen['received']
    assert seen['facts'][0]['value'] == 10.0
