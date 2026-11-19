"""The measurement-validation repository on the custody-scoped store: a sheet saved from a precision statement of a
source, read back, projected and listed, through the real runner."""
from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

REPOSITORY = 'literature_measurement_validation_storage:LiteratureMeasurementValidationRepository'
REQUESTED = 'requested_measurement_validation_components'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
TEXT = 'The assay showed a coefficient of variation of 4.5 % across replicates.'
CONTEXT_FIELDS = ('experiment', 'analyte', 'matrix', 'method', 'endpoint', 'repetition', 'mean_definition',
                  'nominal_uncertainty')


def witness(reference, token):
    start = TEXT.index(token)
    return {'source_ref': reference, 'representation': 'original', 'start': start, 'end': start + len(token),
            'quote': token}


def unknown():
    return {'value': 'unknown', 'witnesses': []}


def selection(reference):
    precision = {'number': {'witness': witness(reference, '4.5'), 'number_start': 0, 'number_end': 3},
                 'quantity_label': witness(reference, 'coefficient of variation'),
                 'unit': {'value': 'percent', 'witness': witness(reference, '%')},
                 'basis': unknown(), 'mean_precision_population': unknown(),
                 'cv_denominator': unknown(), 'recovery_context': unknown(), 'validation_relation': unknown()}
    return {'source_ref': reference, 'source_kind': 'synthetic_fixture',
            'context': dict.fromkeys(CONTEXT_FIELDS), 'recovery': None, 'relative_bias': None,
            'precision': [precision], 'zprime': []}


def test_a_measurement_validation_sheet_is_saved_read_back_projected_and_listed(world):
    saved_source, artifact = source(world, TEXT)
    components = ['reported_cv']
    assignment = {REQUESTED: components, 'source_ref': saved_source}
    populated, held, saved, cells, owned = run(world, 'validation', [
        call(REPOSITORY, 'populate', selection(saved_source), scope=world['scope'], assignment=assignment),
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET]),
        read(REPOSITORY, 'owned_sheet_refs', {})], held=[saved_source, artifact])
    sheet = populated['result']['sheet_ref']
    assert held == owned == [sheet] and saved['input_source_ref'] == saved_source
    assert cells == populated['result']['cells'] and {row['sheet_ref'] for row in cells} == {sheet}
