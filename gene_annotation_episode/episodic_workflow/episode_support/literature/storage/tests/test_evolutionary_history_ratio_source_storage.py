"""The relative-signal source repository on the custody-scoped store: population from a JATS paragraph that reports
a percent of the wild-type level, the saved sheet read back and its cells projected."""
from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

REPOSITORY = 'literature_ratio_source_storage:LiteratureRatioSourceRepository'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
JATS = ('<article><body><sec id="s1"><p>SyntheticProtein 60% (V) of WT levels.</p></sec></body></article>')
FIELDS = ('subject', 'variant', 'reference', 'organism', 'genotype', 'construct_variant', 'construct_reference',
          'preparation_variant', 'preparation_reference', 'experiment', 'condition', 'endpoint', 'normalization',
          'signal_kind', 'reference_role', 'arrangement', 'signal_use')


def unknown():
    return {'status': 'unknown', 'value': None, 'witnesses': []}


def selection(reference):
    paragraph = {'representation_id': 'p1', 'kind': 'jats_percent',
                 'selection': {'source_ref': reference, 'section_id': 's1', 'paragraph_index': 0,
                               'expected_subject': 'SyntheticProtein', 'variant': 'V',
                               'reference_literal': 'WT levels'},
                 'comparison_relation': {'value': 'unknown', 'witnesses': []},
                 'physical_measurement': unknown(), 'reference_measurement': unknown()}
    return {'version': 'relative_signal_source_selection_v2', 'source_ref': reference,
            'comparison': {field: unknown() for field in FIELDS}, 'representations': [paragraph]}


def test_a_relative_signal_sheet_is_saved_read_back_and_projected(world):
    reference, artifact = source(world, JATS, 'application/xml')
    populated, listed, saved, cells = run(world, 'ratio_source', [
        call(REPOSITORY, 'populate', selection(reference), scope=world['scope']),
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET], components=['reported_ratio'])], held=[reference, artifact])
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and listed == [sheet]
    assert saved['input_source_ref'] == reference
    assert [(row['sheet_ref'], row['component']) for row in cells] == [(sheet, 'reported_ratio')]
    assert cells[0]['value'] == populated['result']['cells']['reported_ratio']['value']
