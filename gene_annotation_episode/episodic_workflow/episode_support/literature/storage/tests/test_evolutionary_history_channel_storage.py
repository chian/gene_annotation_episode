"""The channel repository on the custody-scoped store: a sheet saved from an electrical table of a source, read
back, projected and listed, through the real runner."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.evolutionary_history_evidence.literature_channel_calculations import QUANTITIES
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_channel_inputs import LITERAL_FIELDS

from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

REPOSITORY = 'literature_channel_storage:LiteratureChannelRepository'
REQUESTED = 'requested_channel_components'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
TOKENS = dict(current='1.8', applied_voltage='−200', reversal_voltage='53', reported_conductance='7')
UNITS = dict(current='pA', applied_voltage='mV', reversal_voltage='mV', reported_conductance='pS')
CELLS = {role: '<td>' + token + '</td>' for role, token in TOKENS.items()}
HEADERS = ''.join('<th>%s (%s)</th>' % (role, UNITS[role]) for role in QUANTITIES)
TEXT = ('<article><p>Synthetic membrane experiment. Same applicable ionic condition. Current-step magnitude; '
        'signed current; single preparation; closed-channel baseline. Spread meaning unspecified.</p><table><tr>'
        + HEADERS + '</tr><tr>' + ''.join(CELLS.values()) + '</tr></table></article>')


def witness(reference, token, start=None):
    start = TEXT.index(token) if start is None else start
    return {'source_ref': reference, 'representation': 'original', 'quote': token,
            'start': len(TEXT[:start].encode()), 'end': len(TEXT[:start + len(token)].encode())}


def interpreted(reference, value, quote=None):
    return {'value': value, 'witnesses': [] if quote is None else [witness(reference, quote)]}


def selection(reference):
    measurements, cell_start = {}, TEXT.index('</tr><tr>') + len('</tr><tr>')
    for role in QUANTITIES:
        header = '<th>%s (%s)</th>' % (role, UNITS[role])
        unit = witness(reference, UNITS[role], TEXT.index(header) + header.index(UNITS[role]))
        number_witness = witness(reference, CELLS[role], cell_start)
        cell_start += len(CELLS[role])
        measurements[role] = {
            'number': {'witness': number_witness, 'number_start': CELLS[role].index(TOKENS[role]),
                       'number_end': CELLS[role].index(TOKENS[role]) + len(TOKENS[role])},
            'unit': unit, 'context': witness(reference, 'Same applicable ionic condition'), 'spread': None,
            'spread_kind': interpreted(reference, 'unknown')}
    return {'source_ref': reference, 'source_kind': 'synthetic_fixture', 'literals': dict.fromkeys(LITERAL_FIELDS),
            'arrangement_kind': interpreted(reference, 'single_preparation', 'single preparation'),
            'current_kind': interpreted(reference, 'current_step_magnitude', 'Current-step magnitude'),
            'arrangement_relation': interpreted(reference, 'same_electrical_arrangement_supported',
                                                'Same applicable ionic condition'),
            'measurements': measurements, 'covariance_source_ref': None, 'variance_status': 'unknown',
            'variance_witnesses': []}


def test_a_channel_sheet_is_saved_read_back_projected_and_listed(world):
    saved_source, artifact = source(world, TEXT)
    components = ['current', 'reported_conductance', 'chord_conductance']
    assignment = {REQUESTED: components, 'source_ref': saved_source}
    populated, held, saved, cells, selected, available = run(world, 'channel', [
        call(REPOSITORY, 'populate', selection(saved_source), scope=world['scope'], assignment=assignment),
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET]),
        read(REPOSITORY, 'selected_sheet_refs', {}),
        read(REPOSITORY, 'available_sheet_refs', {})], held=[saved_source, artifact])
    sheet = populated['result']['sheet_ref']
    assert held == selected == available == [sheet] and saved['input_source_ref'] == saved_source
    assert [row['component'] for row in cells] == components and {row['sheet_ref'] for row in cells} == {sheet}
    by_name = {row['component']: row for row in cells}
    assert by_name['current']['value'] == 1.8 and by_name['reported_conductance']['value'] == 7
    assert cells == populated['result']['cells']
