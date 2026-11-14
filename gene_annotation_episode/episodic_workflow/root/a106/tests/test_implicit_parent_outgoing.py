"""Actual A106 parent request preparation and selected dispatch, before acquisition.

The original full-family fixture constructs real bindings and freezes its real
Scientific libraries. Original and private parent functions use the same real
Store, schemas, initial forms and child assignment/invocation validators.
Only the Results retained-target read and Monitor target-in-scope lookup are
explicit controlled external-record ports. No target is claimed to have run.
Selected construction is rolled back after the actual child/unit is built or
the original missing credit/retained-record contract rejects construction;
neither a child nor a provider is acquired and no science is executed.
"""
import ast
from copy import deepcopy
from functools import partial
import inspect
import json
from types import FunctionType, SimpleNamespace

import pytest

from .test_implicit_annotation_parent import (
    ROUTES, module, root, original_member, original_function, predecessor_source,
    no_external,
)
from .test_private_multi_parent_construction import full_workflow, ROOT, AXIS
from .private_analysis_exchange_fixtures import api_assignment, launch_assignment, results_assignment


def original_preparer():
    selected = original_member('Workflow', 'selected')
    branches = [node for node in ast.walk(selected) if isinstance(node, ast.If)
                and ast.unparse(node.test) == 'child_exchange is not None'
                and node.orelse and isinstance(node.orelse[0], ast.Assign)
                and ast.unparse(node.orelse[0]) == 'episode_assignment = None']
    branch, = branches
    function = ast.parse('def prepare_request(self, source, selection, index, scope, role): pass').body[0]
    function.body = deepcopy(branch.orelse)
    function.body.append(ast.parse('return schema, report_declaration, initial, episode_assignment, scientific_process, assignment').body[0])
    namespace = dict(vars(module('runtime')))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
                 '<authenticated-original-A106-request-body>', 'exec'), namespace)
    value = namespace['prepare_request']
    return FunctionType(value.__code__, vars(module('runtime')), value.__name__)


def configure(full_workflow, monkeypatch, role, request=None):
    if role == 'scientific_process':
        assert request is not None
        full_workflow = request.getfixturevalue('scientific_request_workflow')
    store, workflow = full_workflow
    monkeypatch.setattr(workflow, 'project_credit', lambda *_args, **_kwargs: 0.0)
    numerical = module('numerical')
    monkeypatch.setattr(workflow, 'controller_factory', lambda _path, initial, **_kwargs:
        numerical.YieldController('a106_parent_outgoing', initial, 0.5,
            numerical.YieldParameters(uncertainty_alpha=0.05)))
    source = root(workflow, 'outgoing_' + role).source
    child = workflow.episode_bindings.for_child(source.path, role)
    assert child.binding_path == ROUTES[role]
    scope = store.validate_scope(source.scope, parent_scope=source.scope)
    ports = []
    if role == 'launch':
        assignment = launch_assignment()
    elif role == 'results':
        handle = 'original-retained-parent-boundary'
        assignment = results_assignment(handle)
        def target(reference, received_scope, **kwargs):
            assert reference == handle and module('communication').plain(received_scope) == scope and not kwargs
            ports.append(('retained_target', reference))
            return {'assignment': api_assignment(), 'scope': deepcopy(scope), 'resource_id': 'original-api'}
        monkeypatch.setattr(child.job_progress_provider.targets, 'read_target', target)
    elif role == 'monitor':
        handle = 'original-monitor-parent-boundary'
        assignment = {'version': 'monitor_assignment_v1', 'target_handle': handle,
            'requested_fields': ['execution_status'], 'known_progress_refs': [],
            'permitted_committed_record_types': []}
        original = child.services.reference_in_scope
        def target_scope(reference, received_scope, namespace):
            if reference == handle and namespace == 'execution_handle':
                assert received_scope == scope
                ports.append(('target_scope', reference))
                return True
            return original(reference, received_scope, namespace)
        monkeypatch.setattr(child.services, 'reference_in_scope', target_scope)
    elif role == 'literature':
        assert child.private_yield_binding is False
        assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': []}
    else:
        assert role == 'scientific_process'
        assignment = {'selection': {'version': 'scientific_process_selection_v3',
            'evidence_axis': child.library.reference('A106'), 'thought_pattern': child.library.reference('P01'),
            'child_tool_info': []}, 'evidence_refs': [], 'constraints': {},
            'context': {'evidence_task': {'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings',
                'evidence_axis': 'A106', 'credit_unit': 2.5}}}
        # This is the actual configured descriptor, not a replacement record.
        assert inspect.ismethod(child.as_record) and child.as_record.__self__ is child
        assert child.as_record()['configuration']
    context = workflow.binding_context(source)
    required = getattr(child, 'required_return_sources', lambda *_args: ())(context, role)
    facts = child.fact_sources(role)
    properties = {'ready': {'type': 'boolean', 'description': 'Engineering request preparation only.'}}
    for name in required:
        properties[name] = deepcopy(facts[name]['report_schema'])
        assert properties[name]['x-source'] == name
    schema = {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}
    selection = {'kind': 'episode_child', 'role': role, 'scope': deepcopy(scope),
        'goal': 'Preserve the original prepared request', 'purpose': 'Return only the requested qualified facts',
        'assignment': assignment, 'schema_json': json.dumps(schema), 'initial_report_json': '{"ready":true}'}
    return store, workflow, source, child, selection, scope, ports


@pytest.mark.parametrize('role', list(ROUTES))
def test_actual_five_outgoing_preparers_match_original(full_workflow, monkeypatch, role, request):
    store, workflow, source, child, selection, scope, ports = configure(full_workflow, monkeypatch, role, request)
    endpoint = module('to_child_' + ROUTES[role]).prepare_request
    exchange = module('child_message_owners').exchange_for_child(workflow, source, role)
    assert exchange[0] is endpoint
    before = deepcopy(selection)
    outcomes = []
    for function, parent in ((original_preparer(), predecessor_source(workflow, source)), (endpoint, source)):
        ports.clear()
        value = function(workflow, parent, deepcopy(selection), 21, scope, role)
        outcomes.append((module('communication').plain(value), list(ports)))
        assert len(value) == 6 and value[3] is not None and value[5] is None
        assert (value[4] is not None) == (role == 'scientific_process')
    assert outcomes[0] == outcomes[1]
    assert selection == before
    assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0


def selected_observation(full_workflow, monkeypatch, role, expected, request=None):
    store, workflow, source, child, selection, scope, ports = configure(full_workflow, monkeypatch, role, request)
    rt = module('runtime')
    endpoint_module = module('to_child_' + ROUTES[role])
    actual_preparer = endpoint_module.prepare_request
    actual_build = workflow.build
    observations = []
    class RollbackConstruction(Exception): pass
    for original in (True, False):
        calls, build_entries, built = [], [], []
        def traced_prepare(*args):
            calls.append((args[3], args[5]))
            return actual_preparer(*args)
        def traced_build(*args, **kwargs):
            build_entries.append((args, kwargs))
            value = actual_build(*args, **kwargs)
            built.append(value)
            return value
        ports.clear()
        with monkeypatch.context() as patch:
            patch.setattr(endpoint_module, 'prepare_request', traced_prepare)
            patch.setattr(workflow, 'build', traced_build)
            parent = predecessor_source(workflow, source) if original else source
            function = original_function('Workflow', 'selected') if original else rt.Workflow.selected
            with pytest.raises(RollbackConstruction):
                with store.transaction():
                    if expected is not None:
                        with pytest.raises(expected[0]) as rejected:
                            function(workflow, parent, deepcopy(selection), 22)
                        assert str(rejected.value) == expected[1]
                        assert built == []
                        observations.append(('original_rejection', type(rejected.value),
                            str(rejected.value), getattr(rejected.value, 'diagnostic', None), list(ports)))
                    else:
                        unit = function(workflow, parent, deepcopy(selection), 22)
                        assert type(unit) is rt.TimedChildUnit
                        assert len(built) == 1
                        constructed = built[0].source
                        assert constructed.path == source.path + ((role, 'child_22'),)
                        assert workflow.episode_bindings.for_path(constructed.path) is child
                        assert type(constructed) is child.decision_source_type
                        observations.append(('constructed', constructed.request.as_record(),
                            type(constructed), list(ports)))
                    assert len(build_entries) == 1
                    assert calls == ([] if original else [(22, role)])
                    raise RollbackConstruction
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0
    assert observations[0] == observations[1]


@pytest.mark.parametrize('role', ['launch'])
def test_actual_selected_constructs_through_private_request(full_workflow, monkeypatch, role, request):
    selected_observation(full_workflow, monkeypatch, role, None, request)


@pytest.mark.parametrize('role', ['monitor', 'results', 'literature'])
def test_minimal_fixture_retains_original_construction_rejection(full_workflow, monkeypatch, role):
    # These deliberately minimal fixtures do not manufacture a monitor credit
    # binding, retained native handoff, or commissioned Literature source claim.
    # The supported roles and their real request validators remain unchanged.
    expected = {
        'monitor': (ValueError, 'explicit_role_credit_binding_required:monitor'),
        'results': (module('domain').ContractError, 'unknown_reference'),
        'literature': (ValueError, 'numerical_credit_requires_episode_receipts'),
    }[role]
    selected_observation(full_workflow, monkeypatch, role, expected)


def test_default_catalogue_retains_missing_a106_instruction(full_workflow):
    _, workflow = full_workflow
    library = workflow.scientific_process_binding.library
    assert library.reference('P01')['slot'] == 'thought_pattern'
    with pytest.raises(ValueError, match='^scientific_process_option_unknown$'):
        library.reference('A106')


def test_annotation_scientific_missing_receipts_matches_original(full_workflow, monkeypatch, request):
    # Genuine invocation preparation is reachable without receipts; constructing
    # its nested scientific task still requires the original receipt contract.
    selected_observation(full_workflow, monkeypatch, 'scientific_process',
        (ValueError, 'numerical_credit_requires_episode_receipts'), request)


def test_receipt_enabled_annotation_hook_rejection_matches_original(scientific_publication_workflow):
    store, workflow = scientific_publication_workflow
    rt = module('runtime')
    assert workflow.receipts is not None and workflow.initial_known_record_refs == ()
    observed = []
    for function in (original_function('Workflow', 'build'), rt.Workflow.build):
        store.db.execute('SAVEPOINT original_receipt_hook_boundary')
        try:
            with pytest.raises(ValueError, match='^unknown_execution_episode_role$') as error:
                function(workflow, 'annotation', 'receipt-hook', 'Preserve the original receipt scope',
                    store.validate_scope())
            observed.append((type(error.value), error.value.args))
            assert store.db.execute('SELECT COUNT(*) FROM runtime_episodes').fetchone()[0] == 0
            assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0
        finally:
            store.db.execute('ROLLBACK TO original_receipt_hook_boundary')
            store.db.execute('RELEASE original_receipt_hook_boundary')
    assert observed[0] == observed[1]


# Exact original full-family constructor fixture, with its source parameter
# set to the retained instruction publication and explicit original options.
# The default catalogue remains a separate negative control; no source evidence
# is promoted to a scientific finding or new credit.
def _publication_workflow(tmp_path_factory, *, root_role, receipts, tool_info=False):
    directory = tmp_path_factory.mktemp('actual-two-parent-families')
    with module('state').Store(directory / 'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        tools = module('tools').ToolRegistry(store)
        library = module('scientific_process_library').ScientificProcessLibrary.freeze(
            directory / 'scientific-process-library', source=ROOT.parents[3] / 'research/slotted_process_library/publications/2026-10-24-001')
        tool_library = module('scientific_tool_library').ScientificToolLibrary.freeze(
            directory / 'scientific-tool-library', catalog=tools.catalog(), tool_info=tool_info)
        factories = [partial(module('scientific_process.episode').ScientificProcessEpisode,
            library=library, tool_library=tool_library,
            child_roles=('scientific_process', 'literature', 'launch', 'monitor', 'results'))]
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
        execution_homes += [literature + '.' + home for home in list(execution_homes)]
        for parent in ('', 'scientific_process.'):
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
            episode_binding_factories=tuple(factories), episode_record_receipts=receipts,
            initial_known_record_refs=[],
            root_role=root_role,
            annotation_child_roles=('scientific_process', 'literature', 'launch', 'monitor', 'results'))
        yield store, workflow
        assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0] == 0
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0
        assert store.db.execute('SELECT COUNT(*) FROM runtime_model_calls').fetchone()[0] == 0


@pytest.fixture(scope='module')
def scientific_publication_workflow(tmp_path_factory):
    yield from _publication_workflow(tmp_path_factory, root_role='annotation', receipts=True)


@pytest.fixture(scope='module')
def scientific_request_workflow(tmp_path_factory):
    yield from _publication_workflow(tmp_path_factory, root_role='annotation', receipts=False, tool_info=True)


@pytest.fixture(scope='module')
def scientific_standalone_workflow(tmp_path_factory):
    yield from _publication_workflow(tmp_path_factory, root_role='scientific_process', receipts=False, tool_info=True)

