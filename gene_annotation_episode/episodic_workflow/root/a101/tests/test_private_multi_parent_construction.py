"""Actual root and scientific child families coexist without role-only dispatch."""
from functools import partial
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest

AXIS = __package__.rsplit('.tests', 1)[0]
ROOT = Path(__file__).resolve().parents[1]


def module(name):
    return import_module(AXIS + '.' + name)


@pytest.fixture(scope='module')
def full_workflow(tmp_path_factory):
    directory = tmp_path_factory.mktemp('actual-two-parent-families')
    with module('state').Store(directory / 'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        tools = module('tools').ToolRegistry(store)
        library = module('sequence_homology_evidence_library').SequenceHomologyEvidenceLibrary.freeze(
            directory / 'scientific-process-library', source=ROOT.parents[3] / 'research/slotted_process_library/publications/2026-10-24-001')
        tool_library = module('scientific_tool_library').ScientificToolLibrary.freeze(
            directory / 'scientific-tool-library', catalog=tools.catalog())
        factories = [partial(module('sequence_homology_evidence.episode').SequenceHomologyEvidenceEpisode,
            library=library, tool_library=tool_library,
            child_roles=('sequence_homology_evidence', 'literature', 'launch', 'monitor', 'results'))]
        execution_homes = ['execution_job_submission',
            'execution_job_submission.api_job_execution', 'execution_result_acquisition']
        if AXIS.endswith('a101'):
            execution_homes += ['execution_job_submission.local_job_execution',
                               'execution_job_submission.hpc_job_execution']
        literature = 'published_evidence_assessment'
        strategy = literature + '.evidence_search_strategy_improvement'
        search = strategy + '.source_relevance_assessment'
        page = search + '.source_evidence_examination'
        literature_homes = [literature, strategy, search, page,
            page + '.table_evidence_extraction', page + '.source_coverage_improvement',
            page + '.passage_evidence_extraction']
        for parent in ('', 'sequence_homology_evidence.'):
            for home in execution_homes:
                factories.append(partial(module(parent + home + '.episode').ExecutionEpisode,
                    store=store, directory=directory, run_id='actual-two-parent-families',
                    resources={'original-api': {'kind': 'api', 'service': 'bvbrc_appservice',
                        'execution_contract': 'bvbrc_appservice_execution_v1',
                        'endpoints': {'AppService': 'https://construction.invalid/app',
                                      'Workspace': 'https://construction.invalid/workspace'},
                        'scientific_adapters': []}},
                    initial_information={'original-api': {'recorded_inventory': 'original-caller-snapshot'}},
                    tool_registry=tools, handoff_unit=1, acquired_record_unit=1,
                    log_window_bytes=128, log_roles=('stdout', 'stderr')))
            factories.append(module(parent + 'execution_progress_assessment.episode').MonitorEpisode)
            factories.extend(module(parent + home + '.episode').LiteratureEpisode for home in literature_homes)
        def unselected(*args, **kwargs):
            raise AssertionError('Construction and planning do not select an action or provider')
        workflow = module('runtime').Workflow(store, tools, SimpleNamespace(complete=unselected),
            directory, 'actual-two-parent-families', unselected, unselected,
            episode_binding_factories=tuple(factories),
            annotation_child_roles=('sequence_homology_evidence', 'literature', 'launch', 'monitor', 'results'))
        yield store, workflow
        assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0] == 0
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0
        assert store.db.execute('SELECT COUNT(*) FROM runtime_model_calls').fetchone()[0] == 0


def test_actual_constructor_keeps_both_parent_families(full_workflow):
    _, workflow = full_workflow
    registry = workflow.episode_bindings
    root = (('annotation', 'original-root'),)
    science = root + (('sequence_homology_evidence', 'original-science'),)
    for role in ('literature', 'launch', 'monitor', 'results'):
        root_child = registry.for_child(root, role)
        scientific_child = registry.for_child(science, role)
        assert root_child is not scientific_child
        assert scientific_child.binding_path == 'sequence_homology_evidence/' + root_child.binding_path
        with pytest.raises(LookupError, match='episode_role_requires_parent'):
            registry.for_role(role)
        with pytest.raises(LookupError, match='episode_role_requires_parent'):
            registry.for_context_role(role)
        assert registry.for_context_role(role, path=root) is root_child
        assert registry.for_context_role(role, path=science) is scientific_child


@pytest.mark.parametrize('path', [
    (('annotation', 'root'),),
    (('annotation', 'root'), ('sequence_homology_evidence', 'science')),
    (('annotation', 'root'), ('launch', 'launch'), ('launch_api', 'native')),
    (('annotation', 'root'), ('sequence_homology_evidence', 'science'), ('launch', 'launch'), ('launch_api', 'native')),
    (('annotation', 'root'), ('sequence_homology_evidence', 'science'), ('results', 'results')),
    (('annotation', 'root'), ('sequence_homology_evidence', 'science'), ('monitor', 'monitor')),
    (('annotation', 'root'), ('sequence_homology_evidence', 'science'), ('literature', 'literature')),
])
def test_actual_two_parent_resource_context_uses_saved_lineage(full_workflow, path):
    store, workflow = full_workflow
    source = SimpleNamespace(path=path, scope=store.validate_scope())
    parent = path[:2] if len(path) > 1 and path[1][0] == 'sequence_homology_evidence' else path[:1]
    registry = workflow.episode_bindings
    assert registry.for_context_role('launch', path=path) is registry.for_child(parent, 'launch')
    context = workflow.resource_context(source)
    assert context['version'] == 'episode_resource_context_v1'
    assert context['local']


def test_ambiguous_direct_provider_cannot_fall_back_to_root(full_workflow):
    from copy import copy
    _, workflow = full_workflow
    original = workflow.episode_bindings
    root = (('annotation', 'root'),)
    science = root + (('sequence_homology_evidence', 'science'),)
    duplicate = copy(original.for_child(science, 'launch'))
    duplicate.binding_path += '_ambiguous_second_provider'
    registry = module('episode_bindings').EpisodeBindingRegistry(
        (*original._bindings, duplicate))
    assert registry.for_child(root, 'launch') is original.for_child(root, 'launch')
    with pytest.raises(LookupError, match='episode_child_not_bound:sequence_homology_evidence:launch'):
        registry.for_context_role('launch', path=science)
