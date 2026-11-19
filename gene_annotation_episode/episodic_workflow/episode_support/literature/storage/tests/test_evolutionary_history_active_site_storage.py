"""The active-site repository on the custody-scoped store: a sheet saved from selected spans of a source, read
back and projected, through the real runner."""
from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

REPOSITORY = 'literature_active_site_storage:LiteratureActiveSiteRepository'
TEXT = 'The protein was used at 2 mg/mL in the titration.'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
FIELDS = ('subject', 'organism', 'construct', 'preparation', 'assay', 'condition', 'endpoint', 'measurement_identity')
INTERPRETATIONS = ('molecular_basis', 'amount_linkage', 'active_estimate_meaning', 'titrant_concentration_basis',
                   'titrant_to_site_stoichiometry', 'site_stoichiometry', 'normalization_stage')


def span(source_ref, piece):
    start = TEXT.index(piece)
    return {'source_ref': source_ref, 'representation': 'original', 'start': start, 'end': start + len(piece),
            'quote': piece}


def selection(source_ref):
    unknown = {'value': 'unknown', 'witnesses': []}
    quantity = {**dict.fromkeys(FIELDS), 'measurement': {
        'number': {'witness': span(source_ref, '2'), 'number_start': 0, 'number_end': 1},
        'unit': span(source_ref, 'mg/mL')},
        'qualification': {'value': 'reported_point', 'witnesses': [span(source_ref, '2 mg/mL')]},
        'reported_uncertainty': {'kind': {'value': 'unreported', 'witnesses': []}, 'measurement': None,
                                 'sampling_basis': unknown, 'statement': None}}
    return {'source_ref': source_ref, 'source_kind': 'synthetic_fixture', 'experiment': None, 'intended_change': None,
            'other_changes': [], 'interpretations': {name: unknown for name in INTERPRETATIONS},
            'quantities': {'protein_mass_concentration': quantity, 'assumed_molecular_weight': None,
                           'active_site_concentration': None, 'reported_active_fraction': None}}


def test_an_active_site_sheet_is_saved_read_back_and_projected(world):
    saved_source, artifact = source(world, TEXT)
    populated, held, saved, cells = run(world, 'active_site', [
        call(REPOSITORY, 'populate', selection(saved_source), scope=world['scope']),
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET])], held=[saved_source, artifact])
    sheet = populated['result']['sheet_ref']
    assert held == [sheet] and saved['input_source_ref'] == saved_source
    assert cells == populated['result']['cells'] and {row['sheet_ref'] for row in cells} == {sheet}
