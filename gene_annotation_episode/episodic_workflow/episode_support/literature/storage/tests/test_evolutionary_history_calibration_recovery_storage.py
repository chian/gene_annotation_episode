"""The calibration-recovery repository on the custody-scoped store: a sheet saved from a recovery table of a source,
read back, projected and listed, through the real runner."""
from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

REPOSITORY = 'literature_calibration_recovery_storage:LiteratureCalibrationRecoveryRepository'
REQUESTED = 'requested_calibration_recovery_components'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
TEXT = ('<article><p>Illustrative standard in buffer, optical reporter, no-reaction blank. Nominal stock amount. SD; '
        'enzyme activity spike; incompatible statement.</p><table-wrap><table><thead><tr><th>Prepared</th>'
        '<th>Measured (nmol)</th><th>Recovery (%)</th></tr></thead><tbody><tr><td>10</td><td>9.8 ± 0.2</td>'
        '<td>98</td></tr></tbody></table></table-wrap></article>')


def witness(reference, token):
    start = TEXT.index(token)
    return {'source_ref': reference, 'representation': 'original', 'start': len(TEXT[:start].encode()),
            'end': len(TEXT[:start + len(token)].encode()), 'quote': token}


def number_in(reference, token, container):
    return {'witness': witness(reference, container), 'number_start': container.index(token),
            'number_end': container.index(token) + len(token)}


def interpretation(reference, value, quote=None):
    return {'value': value, 'witnesses': [] if quote is None else [witness(reference, quote)]}


def selection(reference):
    return {'source_ref': reference, 'source_kind': 'synthetic_fixture',
            'experiment': witness(reference, 'Illustrative standard'), 'analyte': None,
            'matrix': witness(reference, 'buffer'), 'endpoint': witness(reference, 'optical reporter'),
            'blank_treatment': witness(reference, 'no-reaction blank'),
            'expected_quantity_basis': witness(reference, 'Nominal stock amount'),
            'control_kind': interpretation(reference, 'reporter_standard', 'Illustrative standard'),
            'applicability': interpretation(reference, 'unknown'),
            'nominal': number_in(reference, '10', '<td>10</td>'),
            'measured': number_in(reference, '9.8', '<td>9.8 ± 0.2</td>'),
            'measured_spread': number_in(reference, '0.2', '<td>9.8 ± 0.2</td>'),
            'shared_unit': witness(reference, 'nmol'), 'spread_kind': interpretation(reference, 'SD', 'SD'),
            'reported_recovery': number_in(reference, '98', '<td>98</td>'),
            'reported_recovery_unit': {'value': 'percent', 'witness': witness(reference, '%')}}


def test_a_calibration_recovery_sheet_is_saved_read_back_projected_and_listed(world):
    saved_source, artifact = source(world, TEXT)
    components = ['recovery', 'signed_difference', 'percent_bias', 'measured_sd']
    assignment = {REQUESTED: components, 'source_ref': saved_source}
    populated, held, saved, cells, owned = run(world, 'recovery', [
        call(REPOSITORY, 'populate', selection(saved_source), scope=world['scope'], assignment=assignment),
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET], components=components),
        read(REPOSITORY, 'owned_sheet_refs', {})], held=[saved_source, artifact])
    sheet = populated['result']['sheet_ref']
    assert held == owned == [sheet] and saved['input_source_ref'] == saved_source
    by_name = {row['component']: row for row in cells}
    assert list(by_name) == components
    assert by_name['signed_difference']['value'] == -0.2 and by_name['percent_bias']['value'] == -2
