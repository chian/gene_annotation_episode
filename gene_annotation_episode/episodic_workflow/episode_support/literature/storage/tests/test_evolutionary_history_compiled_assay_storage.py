"""The compiled-assay repository on the custody-scoped store: population of a compilation that selects no
numerical component (every interpretation unknown), the saved sheet read back and its cells projected, through the
real runner."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_assay_inputs import ASSAY_LITERAL_FIELDS
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_compiled_assay_inputs import LINKS, ROLES, STAGES
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_compiled_assay_storage import COMPONENTS, REQUESTED

from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

REPOSITORY = 'literature_compiled_assay_storage:LiteratureCompiledAssayRepository'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
UNKNOWN = {'value': 'unknown', 'witnesses': []}


def arguments(reference):
    return {'source_ref': reference, 'source_kind': 'synthetic_fixture',
            'assay': {**dict.fromkeys(ASSAY_LITERAL_FIELDS), 'endpoint': UNKNOWN, 'arrangement': UNKNOWN},
            'operands': dict.fromkeys(ROLES), 'relationships': {role: UNKNOWN for role in LINKS},
            'correction_stages': {name: UNKNOWN for name in STAGES}, 'covariance_source_ref': None,
            'distinct_residual_variance': None, 'residual_relationship': UNKNOWN, 'variance_status': 'unknown',
            'observation_model': 'none', 'model_witnesses': []}


def test_a_compiled_sheet_is_saved_read_back_and_its_cells_projected(world):  # noqa: F811
    reference, artifact = source(world, 'A synthetic compiled assay page.', 'text/plain')
    requested = list(COMPONENTS)[:3]
    populate = call(REPOSITORY, 'populate', arguments(reference), scope=world['scope'],
                    assignment={REQUESTED: requested})
    populate['arguments']['role'] = 'reader'
    populated, held, saved, cells = run(world, 'compiled', [populate,
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET], components=requested)], held=[reference, artifact])
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and held == [sheet]
    assert saved['input_source_ref'] == reference
    assert [cell['component'] for cell in cells] == requested
    assert {cell['sheet_ref'] for cell in cells} == {sheet}
