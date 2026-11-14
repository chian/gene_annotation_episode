"""Original/current message boundaries with real task, journal and contract ports.

Private binding objects used for declaration inspection have their authentic
classes and literal metadata; their scientific constructors are not claimed.
Controlled provider methods stop construction before child execution. The
original selected function is compiled unchanged from a permanent source
oracle, with its actual defining module dictionary and package.
"""
import ast
from contextlib import ExitStack
from copy import deepcopy
import hashlib
from importlib import import_module
import json
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import patch

from .root_policy_checks import host, module, PACKAGE, SCHEMA, WorkflowProbe
from gene_annotation_episode.episodic_workflow.root.action_execution import ActionExecution
from gene_annotation_episode.episodic_workflow.root.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.report_redelivery import ReportRedelivery
from gene_annotation_episode.episodic_workflow.root.task_values import Record
from gene_annotation_episode.episodic_workflow.root.workflow_values import TypedReportContract

ORIGINAL_SHA = 'cecaa7c6ca789a88ddef28504eb18f71e428125531af9ec1397844b35a40b3a0'
EARLY = ('role_key', 'owner_key', 'cached_key', 'cached_container',
         'owner_container', 'path_container', 'registry_descriptor', 'specialist')
NOMINAL = ('improvement', 'scientific', 'terminal', 'operational',
           'hpc', 'monitor', 'literature', 'homology')
LATE = ('expanded_child', 'expanded_job', 'initial_child', 'validation_child',
        'materialized_binding', 'expanded_hpc_path')
RETURNS = ('from_child_homology_job_monitoring', 'from_child_published_evidence_assessment')


class BoundaryStop(Exception):
    pass


def oracle(name):
    path = Path(__file__).parent / 'operational_original_runtime.py'
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ORIGINAL_SHA
    tree = ast.parse(raw)
    if name == 'selected':
        owner, = [x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == 'OriginalActionExecution']
        node, = [x for x in owner.body if isinstance(x, ast.FunctionDef) and x.name == name]
    else:
        assert name == 'original_admit_return'
        node, = [x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == name]
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'),
         vars(module('action_execution')), namespace)
    return namespace[name]


def declarations(*bindings):
    registry = EpisodeBindingRegistry()
    # Explicit supplied declaration operands avoid invoking descriptor hashing
    # or unrelated scientific constructors. No registration-success claim.
    registry._bindings = list(bindings)
    registry._by_role = {}
    registry._by_path = {}
    for binding in bindings:
        registry._by_path[binding.binding_path] = binding
        for role in binding.roles:
            registry._by_role.setdefault(role, []).append(binding)
    return registry


def nominal(workflow, source, name):
    owners = {
        'scientific': ('scientific_process.episode', 'ScientificProcessEpisodes', 'scientific_process', 'to_child_scientific_process'),
        'terminal': ('local_job_execution.episode', 'LocalEpisodeBinding', 'launch_local', 'to_child_local_job_execution'),
        'operational': ('execution_job_submission.episode', 'ExecutionSubmissionBinding', 'launch', 'to_child_execution_job_submission'),
        'hpc': ('hpc_coordination.episode', 'HPCCoordinationEpisodes', 'hpc', 'to_child_hpc_coordination'),
        'monitor': ('execution_monitoring.episode', 'MonitorEpisodes', 'monitor', 'to_child_execution_monitoring'),
        'literature': ('published_evidence_assessment.episode', 'LiteratureEpisode', 'literature', 'to_child_published_evidence_assessment'),
    }
    if name == 'improvement':
        workflow.episode_bindings = declarations()
        return 'child', 'improvement', 'to_child_legacy_annotation', None
    if name == 'homology':
        family = module('library.homology_episode_family').HomologyEpisodes
        workflow.job_episodes = object.__new__(family)
        workflow.episode_bindings = declarations()
        return 'job_child', 'job_monitor', 'to_child_homology_job_monitoring', None
    owner, cls, role, endpoint = owners[name]
    binding = object.__new__(getattr(module(owner), cls))
    if name == 'terminal':
        # These are the actual instance declarations in LocalEpisodeBinding's
        # constructor. This nominal fixture supplies them without constructing
        # resources or claiming registry registration/native execution.
        binding.roles = ('launch_local',)
        binding.entry_roles = binding.roles
    workflow.episode_bindings = declarations(binding)
    return 'episode_child', role, endpoint, binding


def selection_for(source, kind, role):
    return {'kind': kind, 'role': role, 'scope': deepcopy(source.scope),
            'goal': 'Preserve the actual message', 'purpose': 'Return typed credit',
            'assignment': {}, 'initial_report': {}, 'return_form': deepcopy(SCHEMA)}


def prefix(workflow, events):
    workflow.validate_child_choice = lambda *a, **kw: events.append('validate_child_choice')
    workflow.permits_common_action = lambda *a: True
    workflow._closed_child_commission = lambda *a: None
    workflow.binding_selection_for_child = lambda *a: None
    workflow.binding_context = lambda actual: SimpleNamespace(episode_id=actual.episode_id)


def selected_pair(directory, configure):
    results = []
    for old in (True, False):
        with host(directory / str(old)) as (workflow, source), ExitStack() as stack:
            events = []
            prefix(workflow, events)
            selection, owner_calls = configure(workflow, source, events, stack, old)
            function = oracle('selected') if old else ActionExecution.selected
            try:
                function(workflow, source, selection, 0)
            except (BoundaryStop, module('action_execution').ContractError) as error:
                result = (type(error).__name__, str(error))
            else:
                raise AssertionError('controlled child boundary was not reached')
            assert workflow.journal.row('runtime_actions', source.episode_id, 0) is None
            # Normalize supplied str subclasses only after the observation;
            # comparison itself must not invoke their equality callbacks.
            results.append((result, events, json.loads(json.dumps(selection))))
            if owner_calls is not None:
                assert owner_calls == ([] if old else ['private_request'])
    assert results[0] == results[1]
    return results[0]


def paired_early(directory, scenario):
    def configure(workflow, source, events, stack, old):
        kind, role, endpoint, binding = nominal(workflow, source, 'scientific')
        def observed(label):
            events.append(label)
            raise AssertionError('callback ran before expanded form: ' + label)
        class Key(str):
            def __hash__(self): return str.__hash__(self)
            def __eq__(self, other): return observed('key_equality')
        class Cache(dict):
            def get(self, *a): return observed('cache_get')
            def __contains__(self, key): return observed('cache_contains')
            def items(self): return observed('cache_items')
        class PathList(list):
            def __getitem__(self, key):
                events.append('original_path_read')
                return super().__getitem__(key)
        if scenario == 'role_key': role = Key(role)
        elif scenario == 'owner_key':
            workflow.binding_selection_for_child = lambda *a: {'binding': {'owner': Key('controlled_owner')}}
        elif scenario == 'cached_key':
            workflow.episode_bindings._by_role = {Key('scientific_process'): [binding]}
        elif scenario == 'cached_container':
            workflow.episode_bindings._by_role = Cache(workflow.episode_bindings._by_role)
        elif scenario == 'owner_container':
            workflow.episode_bindings._owner_groups = Cache()
        elif scenario == 'path_container': source.path = PathList(source.path)
        elif scenario == 'registry_descriptor':
            stack.enter_context(patch.object(WorkflowProbe, 'episode_bindings',
                property(lambda actual: observed('registry_descriptor')), create=True))
        else:
            assert scenario == 'specialist'
            workflow.specialist = lambda actual: observed('specialist')
        def expanded(*a, **kw):
            events.append('expanded')
            raise BoundaryStop('original expanded-form failure')
        workflow.expanded_contract_form = expanded
        return selection_for(source, kind, role), None
    result, events, selection = selected_pair(directory, configure)
    assert result == ('BoundaryStop', 'original expanded-form failure')
    assert events[-1] == 'expanded'


def paired_nominal(directory, name):
    def configure(workflow, source, events, stack, old):
        kind, role, endpoint, binding = nominal(workflow, source, name)
        owner = module(endpoint)
        original_request = owner.prepare_request
        called = []
        def private(*a, **kw):
            called.append('private_request')
            return original_request(*a, **kw)
        stack.enter_context(patch.object(owner, 'prepare_request', private))
        workflow.specialist = lambda actual: (_ for _ in ()).throw(AssertionError('early specialist'))
        if name == 'homology':
            workflow.job_episodes.implementation_for_path = lambda *a, **kw: (_ for _ in ()).throw(AssertionError('early Homology custody'))
        def expanded(*a, **kw):
            events.append('expanded')
            raise BoundaryStop('selected private request reached original first callback')
        workflow.expanded_contract_form = expanded
        return selection_for(source, kind, role), called
    result, events, selection = selected_pair(directory, configure)
    assert result[0] == 'BoundaryStop' and events[-1] == 'expanded'


def paired_late(directory, scenario):
    def configure(workflow, source, events, stack, old):
        kind, role, endpoint, binding = nominal(workflow, source,
            'operational' if scenario == 'expanded_hpc_path' else 'scientific')
        selection = selection_for(source, kind, role)
        registry = workflow.episode_bindings
        registry.for_child = lambda *a, **kw: events.append('for_child') or binding
        registry.for_role = lambda *a, **kw: events.append('for_role') or binding
        binding.required_return_sources = lambda *a: events.append('required') or ()
        binding.prepare_assignment = lambda *a, **kw: events.append('ordinary_assignment') or {'ordinary': True}
        binding.prepare_invocation = lambda *a, **kw: events.append('scientific_assignment') or {
            'assignment': {'scientific': True}, 'scientific_process': {'invocation': True}}
        workflow.specialist = lambda actual: events.append('specialist') or None
        workflow.job_episodes = SimpleNamespace(assign=lambda *a, **kw: events.append('job_assignment') or {'job': True})
        workflow.resolver = lambda *a, **kw: events.append('resolver') or (lambda *a: True)
        workflow.validate_report = lambda *a, **kw: events.append('semantic_validation')
        def expanded(*a, **kw):
            events.append('expanded')
            if scenario == 'expanded_child': selection['kind'] = 'child'
            elif scenario == 'expanded_job': selection['kind'] = 'job_child'
            elif scenario == 'expanded_hpc_path': source.path = (('hpc', 'late_callback'),)
            return deepcopy(SCHEMA), None
        workflow.expanded_contract_form = expanded
        def initial(*a):
            events.append('initial')
            if scenario == 'initial_child': selection['kind'] = 'child'
            return '{}'
        workflow.child_initial_report_input = initial
        actual_validate = module('action_execution').validate_form
        def validation(*a, **kw):
            events.append('form_validation')
            value = actual_validate(*a, **kw)
            if scenario == 'validation_child': selection['kind'] = 'child'
            return value
        stack.enter_context(patch.object(module('action_execution'), 'validate_form', validation))
        def materialize(*a):
            events.append('materialize')
            if scenario == 'materialized_binding':
                registry.for_role = lambda *a, **kw: events.append('replaced_for_role') or object()
        workflow.launch_instructions = SimpleNamespace(materialize=materialize)
        def build(*a, **kw):
            events.append(('build', deepcopy(kw['episode_assignment']), deepcopy(kw['scientific_process']), deepcopy(kw['job_assignment'])))
            raise BoundaryStop('actual typed contract constructed; child work forbidden')
        workflow.build = build
        owner = module(endpoint)
        original_request, called = owner.prepare_request, []
        def private(*a, **kw):
            called.append('private_request')
            return original_request(*a, **kw)
        stack.enter_context(patch.object(owner, 'prepare_request', private))
        return selection, called
    result, events, selection = selected_pair(directory, configure)
    if scenario == 'expanded_hpc_path':
        assert result == ('ContractError', 'hpc_launch_requires_original_handoff_fact_in_return_form')
        assert 'initial' not in events
    else:
        assert result[0] == 'BoundaryStop' and events[-1][0] == 'build'
        if scenario == 'materialized_binding':
            assert 'ordinary_assignment' in events and 'scientific_assignment' not in events
        elif scenario == 'expanded_job':
            assert 'job_assignment' in events and 'for_child' not in events
        else:
            assert 'ordinary_assignment' not in events and 'scientific_assignment' not in events


def private_override(directory, placement):
    with host(directory) as (workflow, original_source), ExitStack() as stack:
        binding_type = module('execution_monitoring.episode').MonitorEpisodes
        binding = object.__new__(binding_type)
        source = object.__new__(binding_type.decision_source_type)
        source.path = (('monitor', 'declaration_only'),)
        workflow.episode_bindings = declarations(binding)
        selector = module('predefined_child_message_owners').exchange_for_child
        expected = module('execution_monitoring.to_child_execution_monitoring').prepare_request
        assert selector(workflow, source, 'monitor')[0] is expected
        called = []
        def override(*a, **kw):
            called.append('override')
            raise AssertionError('private declaration override ran early')
        if placement == 'class':
            stack.enter_context(patch.object(binding_type, 'child_message_exchange', staticmethod(override)))
        else:
            assert placement == 'instance'
            binding.child_message_exchange = override
        assert selector(workflow, source, 'monitor') is None
        assert called == []


def paired_job_assignment(directory, provider_kind):
    routes = []
    def configure(workflow, source, events, stack, old):
        kind, role, endpoint, binding = nominal(workflow, source, 'homology')
        selected = selection_for(source, kind, role)
        route = []
        routes.append(route)
        def assignment(route_name):
            def assign(*a, **kw):
                route.append(route_name)
                events.append('assignment')
                assert events[-2] == 'semantic_validation'
                return {'controlled_job_assignment': True}
            return assign
        if provider_kind == 'public_custom':
            workflow.job_episodes = SimpleNamespace(assign=assignment('public'))
        else:
            assert provider_kind == 'current_private'
            workflow.job_episodes.assign = assignment('public')
            implementation = object.__new__(module('homology_job_monitoring.episode').HomologyMonitoringEpisodes)
            implementation.assign = assignment('private')
            def current(path, *, child_role):
                assert path == source.path and child_role == role
                route.append('current_selection')
                return implementation
            workflow.job_episodes.implementation_for_path = current
        workflow.expanded_contract_form = lambda *a, **kw: events.append('expanded') or (deepcopy(SCHEMA), None)
        workflow.child_initial_report_input = lambda *a: events.append('initial') or '{}'
        workflow.resolver = lambda *a, **kw: events.append('resolver') or (lambda *a: True)
        workflow.validate_report = lambda *a, **kw: events.append('semantic_validation')
        def build(*a, **kw):
            assert kw['job_assignment'] == {'controlled_job_assignment': True}
            events.append('build')
            raise BoundaryStop('job assignment retained at original late point')
        workflow.build = build
        return selected, None
    selected_pair(directory, configure)
    assert routes[0] == ['public']
    assert routes[1] == (['public'] if provider_kind == 'public_custom' else ['current_selection', 'private'])


def paired_return(directory, endpoint):
    owner = module(endpoint)  # Import before replacing the live original global.
    outputs = []
    for old in (True, False):
        with host(directory / str(old)) as (workflow, source):
            workflow.episode_branch_lifecycle = None
            workflow.save_attempt = MethodType(ReportRedelivery.save_attempt, workflow)
            workflow.delivery_feedback = ReportRedelivery.delivery_feedback
            received, digests = [], []
            workflow.receive_form = lambda actual, form, schema, index, **kw: received.append(
                (deepcopy(form), deepcopy(schema), index, kw)) or ['controlled_received_reference']
            workflow.journal.save('runtime_actions', {'episode_id': source.episode_id,
                'decision_index': 0, 'action': '{}', 'result': None, 'credit': None})
            actual_digest = module('action_execution')._digest
            def digest(value):
                digests.append(deepcopy(value))
                return actual_digest(value)
            contract = TypedReportContract('Actual return admission', SCHEMA, lambda *a: True)
            child = SimpleNamespace(source=SimpleNamespace(episode_id='controlled_child'))
            with patch.object(module('action_execution'), '_digest', digest):
                invoke = oracle('original_admit_return') if old else owner.admit_return
                first = invoke(workflow, source, child, 0, SCHEMA, contract,
                    Record({'form': {'credit': 0.75}}), source.request)
                # Actual saved-attempt path ignores a different later result.
                second = invoke(workflow, source, child, 0, SCHEMA, contract,
                    Record({'form': {'credit': 0.125}}), source.request)
            assert first == second == ({'credit': 0.75}, ['controlled_received_reference'])
            assert len(digests) == 2 and len(received) == 2
            rows = workflow.store.db.execute('SELECT contract,form,failure FROM runtime_report_attempts WHERE run_id=?', (workflow.run_id,)).fetchall()
            assert len(rows) == 1 and json.loads(rows[0]['form']) == {'credit': 0.75}
            outputs.append((first, second, received, digests, [tuple(row) for row in rows]))
    assert outputs[0] == outputs[1]
