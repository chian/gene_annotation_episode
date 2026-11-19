"""The ion-discrimination repository on the custody-scoped store: a sheet saved from a reported ratio of a source,
read back, projected and listed, through the real runner."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_ion_discrimination_inputs import (
    ion_discrimination_population_schema)

from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

REPOSITORY = 'literature_ion_discrimination_storage:LiteratureIonDiscriminationRepository'
REQUESTED = 'requested_ion_discrimination_components'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
TEXT = 'The channel preferred potassium over sodium with a ratio of 12.5 in the assay.'
DEFINITIONS = ion_discrimination_population_schema()['$defs']


def witness(reference, token):
    start = TEXT.index(token)
    return {'source_ref': reference, 'representation': 'original', 'start': start, 'end': start + len(token),
            'quote': token}


def unknown():
    return {'value': 'unknown', 'witnesses': []}


def selection(reference):
    arm = dict.fromkeys(DEFINITIONS['Context']['properties']['preferred']['properties'])
    context = {'preferred': dict(arm), 'alternative': dict(arm), 'preferred_ion': witness(reference, 'potassium'),
               'alternative_ion': witness(reference, 'sodium'), 'intended_change': None, 'assertion': None}
    quantity = {'number': {'witness': witness(reference, '12.5'), 'number_start': 0, 'number_end': 4}, 'unit': None,
                **{name: unknown() for name in DEFINITIONS['SourceQuantity']['properties']
                   if name not in ('number', 'unit')}}
    return {'version': 'a105_ion_discrimination_selection_v1', 'source_ref': reference,
            'source_kind': 'synthetic_fixture', 'context': context,
            'relationships': {name: unknown() for name in DEFINITIONS['Relationships']['properties']},
            'nonintended_differences': [], 'route': 'reported_ratio', 'reported_ratio': quantity}


def test_an_ion_discrimination_sheet_is_saved_read_back_projected_and_listed(world):
    saved_source, artifact = source(world, TEXT)
    assignment = {REQUESTED: ['activity_ratio'], 'source_ref': saved_source}
    populated, held, saved, cells, owned = run(world, 'ion', [
        call(REPOSITORY, 'populate', selection(saved_source), scope=world['scope'], assignment=assignment),
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET]),
        read(REPOSITORY, 'owned_sheet_refs', {})], held=[saved_source, artifact])
    sheet = populated['result']['sheet_ref']
    assert held == owned == [sheet] and saved['input_source_ref'] == saved_source
    assert [row['component'] for row in cells] == ['activity_ratio'] and cells[0]['sheet_ref'] == sheet
