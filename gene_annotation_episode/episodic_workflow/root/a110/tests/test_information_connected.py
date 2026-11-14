"""Actual own-axis recipients/readers; no model, native command or network.

The old callback asset is captured before application. Empty scientific readers
are covered here; nonempty API/RNA custody is a separate required test module.
"""
import ast
import asyncio
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources, commission, recorded_queue

AXIS = 'a110'
PREFIX = 'gene_annotation_episode.episodic_workflow.root.' + AXIS + '.'
PARENTS = ('', 'scientific_process', 'hpc_work_planning',
    'hpc_work_planning/hpc_allocation_execution', 'scientific_process/hpc_work_planning',
    'scientific_process/hpc_work_planning/hpc_allocation_execution')


def module(name):
    return importlib.import_module(PREFIX + name.replace('/', '.'))


def original_initial(owner, context):
    """Exact pre-change callback; no old application implementation is imported."""
    asset = Path(__file__).parent / 'fixtures/initial_information_original/initial_decision_context.py'
    tree = ast.parse(asset.read_text())
    node, = [value for value in tree.body if isinstance(value, ast.FunctionDef)]
    assert node.name == 'initial_decision_context'
    namespace = {'deepcopy': deepcopy}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(asset), 'exec'), namespace)
    return namespace[node.name](owner, context)


class InformationCase:
    def __init__(self, directory, *, partial=False, received_resources=None, clients=None, connect=True):
        self.directory = directory
        self.store = module('state').Store(directory / 'store')
        subject, = self.store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        self.scope = {'subject_refs': [subject]}
        self.run_id = AXIS + '-original-information'
        self.journal = module('episode_journal').Journal(self.store, self.run_id)
        self.services = SimpleNamespace(annotation_task_required=lambda: False)
        self.tools = module('tools').ToolRegistry(self.store, **({} if clients is None else {'clients': clients}))
        self.resources = deepcopy(received_resources or resources())
        initial = {key: {'configured_by': 'actual_original_global_factory',
            'retained_inventory': {'resource': key, 'nested': [1, False, None]}} for key in self.resources}
        self.factory = module('execution_service_setup').ExecutionServiceFactory(
            self.resources, initial, 3., 2., 1., log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        self.definition = module('communication').plain(self.factory.as_record())
        library = SimpleNamespace(as_record=lambda: {}, headers=lambda: [])
        science = module('scientific_process/episode').ScientificProcessEpisode(self.services,
            library=library, tool_library=library,
            child_roles=('scientific_process', 'hpc', 'launch', 'results', 'monitor', 'literature'))
        self.bindings, self.execution, self.parents, self.contexts = [science], {}, {}, []
        self.hpc_plans, self.hpc_initialization = {}, []
        self.root = self.context((('annotation', 'root'),), {})
        scientific = self.context(self.root.path + (('scientific_process', 'science'),),
            {'proposed_annotation_ref': 'hypothesis_fixture',
                'selection': {'evidence_axis': {'option_id': AXIS.upper()}}})
        self.parents.update({'': self.root, 'scientific_process': scientific})
        for home in ('hpc_work_planning', 'scientific_process/hpc_work_planning'):
            parent = scientific if home.startswith('scientific_process/') else self.root
            planner = self.context(parent.path + (('hpc', 'planner'),), {'commission_id': 'commission'})
            allocation = self.context(planner.path + (('hpc_execution', 'allocation'),),
                {'commission_id': 'commission', 'owner_episode_id': planner.episode_id})
            self.parents.update({home: planner, home + '/hpc_allocation_execution': allocation})
            for suffix in ('', '/hpc_allocation_execution', '/hpc_resource_prediction'):
                binding = module(home + suffix + '/episode').HPCEpisode(self.services,
                    store=self.store, run_id=self.run_id, directory=directory / 'workflow',
                    resources=resources(), commissions={'commission': commission()})
                self.bindings.append(binding)
                if suffix != '/hpc_resource_prediction':
                    context = self.parents[home + suffix]
                    binding.initialize(context)
                    ledger = binding.state(context)
                    queue_ref = ledger.put('queue', {'snapshot': recorded_queue(module('hpc_queue'))})
                    outcome = asyncio.run(binding.execute(context, 'hpc.plan',
                        {'candidate_id': ledger.commission['candidates'][0]['id'],
                         'model_ref': 'reference_model', 'queue_ref': queue_ref},
                        'information-fixture-plan:' + home + suffix))
                    assert outcome['status'] == 'completed', outcome
                    plan = ledger.read(outcome['result']['plan_ref'])
                    self.hpc_plans[home + suffix] = plan
                    self.hpc_initialization.append({'binding_path': binding.binding_path,
                        'context': context.as_record(), 'owner': ledger.read('owner'),
                        'plan_ref': outcome['result']['plan_ref'], 'plan': plan,
                        'outcome': outcome, 'native_or_provider_operations': 0})
            self.contexts.append(self.context(planner.path + (('hpc_prediction', 'prediction'),),
                {'commission_id': 'commission', 'owner_episode_id': planner.episode_id}))
        for parent_home in PARENTS[2:] if partial else PARENTS:
            prefix = parent_home + '/' if parent_home else ''
            homes = [prefix + 'execution_job_submission',
                *([prefix + 'execution_job_submission/api_job_execution'] if AXIS == 'a107' else []),
                prefix + 'execution_job_submission/local_job_execution',
                prefix + 'execution_job_submission/hpc_job_execution', prefix + 'execution_result_acquisition']
            instances = [module(home + '/episode').ExecutionEpisode(self.services,
                store=self.store, run_id=self.run_id, directory=directory / 'workflow', tool_registry=self.tools,
                **{key: self.definition[key] for key in ('resources', 'initial_information',
                    'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles')}) for home in homes]
            self.execution[parent_home] = {owner.roles[0]: owner for owner in instances}
            self.bindings.extend(instances)
            self.bindings.append(module(prefix + 'execution_progress_assessment/episode').MonitorEpisode(self.services))
            parent = self.parents[parent_home]
            plan = self.hpc_plans.get(parent_home)
            launch_assignment = ({'information_fixture': 'no native admission'}
                if plan is None else plan['launch_assignment'])
            native_assignment = {} if plan is None else plan['practical_assignment']
            launch = self.context(parent.path + (('launch', 'launch'),), launch_assignment)
            self.contexts.extend((launch, self.context(launch.path + (('launch_hpc', 'native'),), native_assignment),
                self.context(parent.path + (('results', 'results'),), {'version': 'execution_results_assignment_v1',
                    'handoff_ref': 'no-native-observation', 'selector': {}})))
            monitor = self.context(parent.path + (('monitor', 'monitor'),),
                {'target_handle': 'no-native-observation', 'requested_fields': ['execution_status']})
            self.contexts.extend((monitor, self.context(monitor.path + (('monitor', 'dependency'),),
                module('communication').plain(monitor.assignment))))
        assert len(self.hpc_plans) == len(self.hpc_initialization) == 4
        (directory / 'hpc-initialization.json').write_text(json.dumps(self.hpc_initialization, indent=2) + '\n')
        self.contexts[0:0] = list(self.parents.values())
        self.registry = module('episode_bindings').EpisodeBindingRegistry(self.bindings)
        expected = (31 if partial else 43) if AXIS == 'a107' else (27 if partial else 37)
        assert len(self.bindings) == expected
        self.owner = next(iter(self.execution.values()))['launch']
        self.configuration = self.catalog = None
        if not connect:
            return
        self.configuration = module('library/execution_initial_information/information_configuration').InitialInformationConfiguration.original_global_factory(self.factory)
        self.catalog = self.configuration.construct(store=self.store, run_id=self.run_id,
            directory=directory / 'workflow', tool_registry=self.tools, services=self.services)
        annotation = module('annotation_initial_information').initial_information
        self.registry.configure_initial_information(self.catalog, annotation)

    def context(self, path, assignment):
        ident = module('method_loop/identities').EpisodeRef(self.run_id, path).episode_id
        request = {'message': {'scope': self.scope, 'episode_assignment': assignment}}
        canonical = module('execution_contracts').canonical
        self.journal.save('runtime_episodes', {'episode_id': ident, 'path': canonical(path),
            'request': canonical(request), 'initial_credit': 0, 'state': 'running'})
        return module('episode_bindings').BindingContext(self.run_id, ident, path[-1][0], path,
            self.scope, assignment, request)

    def close(self):
        self.store.close()


def private_information(case, context):
    if case.catalog is None:
        return case.owner.initial_decision_context(context)
    return case.registry._recipient_initial_information(context)


@pytest.fixture(params=[False, True], ids=['full-private-tree', 'hpc-only-private-tree'])
def case(tmp_path, request):
    value = InformationCase(tmp_path, partial=request.param)
    try:
        yield value
    finally:
        value.close()


def test_all_actual_recipient_payloads_equal_original_global_callback(case):
    before = list(case.store.db.iterdump())
    checked = []
    for context in case.contexts:
        actual = case.registry._recipient_initial_information(context)
        expected = original_initial(case.owner, context)
        assert actual == expected, context.path
        assert actual['execution_initial_information']
        checked.append({'context': context.as_record(), 'expected': expected, 'actual': actual})
    assert list(case.store.db.iterdump()) == before
    (case.directory / 'initial-information-complete-payloads.json').write_text(json.dumps(checked, indent=2) + '\n')


def test_parent_and_sibling_registry_merge_keeps_original_information(case):
    # HPC contexts now contain actual initialized-parent plan assignments.
    # The separate Launch/native commissioner applicability conflicts remain
    # recorded by the original baseline and covered by Launch connected tests.
    for context in case.contexts:
        if context.role in {'launch', 'launch_hpc'}:
            continue
        expected = original_initial(case.owner, context)
        actual = case.registry.initial_decision_context(context)
        assert all(actual[key] == value for key, value in expected.items()), context.path


def test_reader_identity_mismatch_is_rejected_without_record_changes(case):
    before = list(case.store.db.iterdump())
    with pytest.raises(ValueError, match='initial_information_receiver_identity_conflict'):
        case.registry._recipient_initial_information(replace(case.root, episode_id='unrelated'))
    assert list(case.store.db.iterdump()) == before


def test_actual_capabilities_action_retains_own_payload_after_callback_retirement(case):
    for home, family in case.execution.items():
        owner = family['launch']
        context = next(value for value in case.contexts if value.role == 'launch'
            and value.path[:-1] == case.parents[home].path)
        before = list(case.store.db.iterdump())
        returned = asyncio.run(owner.execute(context, 'execution.capabilities', {}, 'capabilities-information'))
        assert returned['status'] == 'completed'
        assert returned['result'] == original_initial(owner, context)
        invalid = asyncio.run(owner.execute(context, 'execution.capabilities', {'unrecognized': True}, 'invalid-capabilities-information'))
        assert invalid['status'] == 'invalid'
        assert list(case.store.db.iterdump()) == before


def test_factory_information_reopens_from_complete_configuration(case):
    Type = type(case.configuration)
    original = case.catalog.as_record()
    restored = Type.from_record(case.configuration.as_record())
    readers = restored.construct(store=case.store, run_id=case.run_id,
        directory=case.directory / 'workflow', tool_registry=case.tools, services=case.services)
    readers.check_saved(original)
    assert readers.original_global_information(case.root) == original_initial(case.owner, case.root)
    assert restored.as_record() == case.configuration.as_record()


def test_selected_explicit_factory_must_match_actual_execution_operands(case):
    Type = type(case.configuration)
    definition = deepcopy(case.definition)
    definition['initial_information'] = {}
    unrelated = module('execution_service_setup').ExecutionServiceFactory.from_record(definition)
    bad = Type.original_global_factory(unrelated).construct(store=case.store, run_id=case.run_id,
        directory=case.directory / 'workflow', tool_registry=case.tools, services=case.services)
    with pytest.raises(ValueError, match='initial_information_recipient_configuration_conflict'):
        case.registry.configure_initial_information(bad, module('annotation_initial_information').initial_information)


def test_current_execution_provider_is_not_needed_for_annotation_parent(case):
    assert case.root.role == 'annotation'
    # The partial case has no annotation/scientific Launch child, yet the
    # explicitly original global factory retains exactly its original payload.
    value = case.registry._recipient_initial_information(case.root)
    assert value == original_initial(case.owner, case.root)
    if '' not in case.execution:
        with pytest.raises(LookupError, match='episode_child_not_bound'):
            case.registry.for_child(case.root.path, 'launch')


def test_all_existing_literature_recipients_select_original_information(case):
    root = Path(module('state').__file__).parent
    bindings = []
    for path in sorted(root.rglob('episode.py')):
        if '/published_evidence_assessment/' not in str(path):
            continue
        home = str(path.parent.relative_to(root))
        binding = module(home + '/episode').LiteratureEpisode(case.services)
        bindings.append(binding)
    assert bindings
    expanded = module('episode_bindings').EpisodeBindingRegistry([*case.bindings, *bindings])
    expanded.configure_initial_information(case.catalog, module('annotation_initial_information').initial_information)
    by_home = {binding.binding_path: binding for binding in bindings}
    paths = {'legacy_annotation': case.root.path, 'scientific_process': case.parents['scientific_process'].path}
    for binding in sorted(bindings, key=lambda item: item.binding_path.count('/')):
        parent = paths[binding.commissioning_parent]
        path = parent + ((binding.roles[0], 'private-literature'),)
        context = case.context(path, {})
        paths[binding.binding_path] = path
        assert expanded.for_path(path) is by_home[binding.binding_path]
        assert expanded._recipient_initial_information(context) == original_initial(case.owner, context)


def test_untagged_custom_recipient_keeps_explicit_original_global_information(case):
    class Custom:
        roles, entry_roles = ('custom',), ('custom',)
        def as_record(self):
            return {'version': 'controlled_legacy_information_recipient_v1'}
        def credit_kind(self, role):
            return 'operational'
        def child_roles(self, role):
            return ()
        def unused(self, *args, **kwargs):
            raise AssertionError('custom fixture has no executed work')
        assignment_schema = permitted_common_actions = allowed_children = unused
        prepare_assignment = instructions = decision_context = catalog = unused
        execute = fact_sources = facts = resolve = validate_report = credit_view = unused
    custom = Custom()
    registry = module('episode_bindings').EpisodeBindingRegistry([*case.bindings, custom])
    registry.configure_initial_information(case.catalog, module('annotation_initial_information').initial_information)
    context = case.context(case.root.path + (('custom', 'original-caller'),), {})
    assert registry._recipient_initial_information(context) == original_initial(case.owner, context)
    custom.initial_decision_context = lambda unused: {'execution_initial_information': {'conflict': True}}
    with pytest.raises(ValueError, match='initial_binding_context_field_conflict'):
        registry.initial_decision_context(context)


def test_multifactory_unknown_custom_recipient_cannot_fall_back(case):
    Type = type(case.configuration)
    rows = [{'recipient': binding.binding_path, 'authority_id': 'explicit'} for binding in case.bindings]
    rows.append({'recipient': '@annotation', 'authority_id': 'explicit'})
    catalog = Type([('explicit', case.factory)], rows).construct(store=case.store,
        run_id=case.run_id, directory=case.directory / 'workflow', tool_registry=case.tools, services=case.services)
    with pytest.raises(ValueError, match='initial_information_recipient_provenance_missing'):
        catalog.original_global_information(case.root)
