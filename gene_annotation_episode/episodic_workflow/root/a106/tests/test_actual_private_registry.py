"""Real offline constructors and complete scientific-family hook composition."""
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest

AXIS = __package__.rsplit('.tests', 1)[0]
ROOT = Path(__file__).resolve().parents[1]


def module(name):
    return import_module(AXIS + '.' + name)


@pytest.fixture(scope='module')
def constructed(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp('actual-private-registry')
    with module('state').Store(tmp_path / 'store') as store:
        journal = module('episode_journal').Journal(store, 'construction-original')
        tools = module('tools').ToolRegistry(store)
        host = SimpleNamespace(store=store, tools=tools, run_id='construction-original', journal=journal, directory=tmp_path)
        services = module('episode_services').WorkflowServices(host)
        library = module('perturbation_evidence_library').PerturbationEvidenceLibrary.freeze(
            tmp_path / 'scientific-process-library', source=ROOT.parents[3] / 'research/slotted_process_library/publications/2026-10-24-001')
        tool_library = module('scientific_tool_library').ScientificToolLibrary.freeze(
            tmp_path / 'scientific-tool-library', catalog=tools.catalog())
        scientific = module('perturbation_evidence.episode')
        execution = scientific.create_execution_bindings(services, store=store,
            directory=tmp_path, run_id=host.run_id,
            resources={'original-api': {'kind': 'api', 'service': 'bvbrc_appservice',
                'execution_contract': 'bvbrc_appservice_execution_v1',
                'endpoints': {'AppService': 'https://construction.invalid/app',
                              'Workspace': 'https://construction.invalid/workspace'},
                'scientific_adapters': []}},
            initial_information={'original-api': {'recorded_inventory': 'original-caller-snapshot'}}, tool_registry=tools, handoff_unit=1,
            acquired_record_unit=1, log_window_bytes=128, log_roles=('stdout', 'stderr'))
        monitor = module('perturbation_evidence.execution_progress_assessment.episode').MonitorEpisode(services)
        literature = module('perturbation_evidence.published_evidence_assessment.episode').create_binding_tree(services)
        head = scientific.PerturbationEvidenceEpisode(services, library=library, tool_library=tool_library,
            child_roles=('perturbation_evidence', 'literature', 'launch', 'monitor', 'results'))
        bindings = (head, *execution, monitor, *literature)
        registry = module('episode_bindings').EpisodeBindingRegistry(bindings)
        host.episode_bindings = registry
        host.perturbation_evidence_binding = head
        yield store, host, registry, bindings, literature


def context(role, path, *, episode_id='original-owner'):
    return module('episode_bindings').BindingContext(
        run_id='construction-original', episode_id=episode_id, role=role,
        path=path, scope={}, assignment={}, request={}, received_record_refs=())


def test_actual_services_and_all_scientific_family_constructors(constructed):
    store, host, registry, bindings, literature = constructed
    assert len(bindings) == (14 if AXIS.endswith('a101') else 12)
    assert len(registry.as_record()) == len(bindings)
    assert registry.for_path((('perturbation_evidence', 'original'),)) is bindings[0]
    for binding in literature:
        assert binding.services is bindings[0].services
        assert binding.assignment_schema(binding.roles[0])['type'] == 'object'
    assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0] == 0
    assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0


def test_whole_registry_preserves_typed_external_source_schema_ownership(constructed):
    _, _, registry, _, literature = constructed
    path = (('perturbation_evidence', 'original'),)
    actual = registry.received_report_sources('perturbation_evidence', path=path)
    expected = {} if AXIS.endswith('a101') else literature[0].received_report_sources('perturbation_evidence')
    assert all(actual[key] == value for key, value in expected.items())


def test_whole_registry_current_literature_report_uses_original_owner(constructed):
    store, _, registry, _, literature = constructed
    path = (('perturbation_evidence', 'original'), ('literature', 'original-literature'))
    owner = context('literature', path)
    actual = registry.current_report_facts(owner)
    expected = literature[0].current_report_facts(owner)
    assert all(actual[key] == value for key, value in expected.items())
    assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0


def test_native_child_checks_parent_launch_form_without_claiming_launch_role(constructed):
    _, _, _, bindings, _ = constructed
    for binding in bindings:
        if binding.roles[0] != 'launch_api':
            continue
        with pytest.raises(ValueError, match='unknown_execution_episode_role'):
            binding.assignment_schema('launch')
        with pytest.raises(ValueError, match='invalid_execution_launch_assignment'):
            binding._launch({})


@pytest.mark.parametrize('role', (
    'annotation', 'perturbation_evidence', 'launch', 'launch_api', 'results',
    'monitor', 'literature', 'literature_strategy', 'literature_search', 'literature_page',
    'literature_targeted', 'literature_table', 'literature_ordered',
))
def test_nonempty_initial_context_keeps_original_execution_provider(constructed, role):
    """Actual constructors, sibling consumers, and original nonempty caller data."""
    store, _, registry, bindings, _ = constructed
    provider = next(binding for binding in bindings
                    if binding.binding_path == 'perturbation_evidence/execution_job_submission')
    if role == 'annotation':
        path = (('annotation', 'original-parent'),)
    else:
        binding = registry.for_role(role)
        pieces = binding.binding_path.split('/')
        path = tuple((registry.for_binding_path('/'.join(pieces[:index + 1])).roles[0],
                      'original-' + str(index)) for index in range(len(pieces)))
    owner = context(role, path)
    expected = provider.initial_decision_context(owner)
    assert expected['execution_initial_information'] == {
        'original-api': {'recorded_inventory': 'original-caller-snapshot'}}
    assert expected['execution_resource_capabilities']
    actual = registry.initial_decision_context(owner)
    assert all(actual[key] == value for key, value in expected.items())
    assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0] == 0
    assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0
