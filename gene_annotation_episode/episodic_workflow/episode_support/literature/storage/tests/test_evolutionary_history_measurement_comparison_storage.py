"""The measurement-comparison repository on the custody-scoped store: population from a retained synthetic source,
the saved sheet read back and its requested cells projected, through the real runner."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_measurement_comparison_components_258 import source_fixture
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_measurement_comparison_storage import MEASUREMENT_COMPARISON_REQUEST_SCHEMA, POPULATION, REQUESTED

from .evolutionary_history_world import call, read, run, source, world  # noqa: F401
from .test_evolutionary_history_endpoint_signal_storage import bound

REPOSITORY = 'literature_measurement_comparison_storage:LiteratureMeasurementComparisonRepository'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}


def nothing_selected(schema):
    """The value of a return-context schema that selects no window: every array empty."""
    if schema['type'] == 'array':
        return []
    return {name: nothing_selected(item) for name, item in schema['properties'].items()}


def test_a_measurement_comparison_sheet_is_saved_read_back_and_its_cells_projected(world):  # noqa: F811
    selection, sources, _ = source_fixture()
    (placeholder, _), = sources
    content = sources[placeholder, 'original']['content']
    reference, artifact = source(world, content.decode(), 'text/html')
    assert artifact == sources[placeholder, 'original']['artifact_ref']
    selection = bound(selection, {placeholder: reference})
    requested = selection['requested_cells']
    arguments = {'version': POPULATION, 'selection': selection,
                 **{name: nothing_selected(MEASUREMENT_COMPARISON_REQUEST_SCHEMA['properties'][name])
                    for name in ('return_context', 'return_assertion_context')}}
    populate = call(REPOSITORY, 'populate', arguments, scope=world['scope'], assignment={REQUESTED: requested})
    populate['arguments']['role'] = 'reader'
    populated, held, saved, cells = run(world, 'comparison', [populate,
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET], components=requested)], held=[reference, artifact])
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and held == [sheet]
    assert saved['input_source_ref'] == reference
    assert [cell['component'] for cell in cells] == requested
    assert {cell['sheet_ref'] for cell in cells} == {sheet}
