"""Real selected/admission/build traces against authenticated original methods.

Store, Journal, registry, child admission, form compilation, frozen instruction
validation, EpisodeGoal/Request/identity and receipt inheritance remain real.
The declared observation stop runs the real child source constructor, then
halts before scientific initialization/credit. Reconstruction stops immediately
after the real saved-request comparison. These are boundary checks, not completed
scientific workflows. The separate retained tests keep the real missing-credit
failure. The original runtime text is a required authenticated test fixture.
"""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest

from .. import runtime
from ..communication import plain
from ..episode_journal import Journal, WorkflowError
from ..episode_receipts import EpisodeReceipts
from ..launch_instructions import LaunchInstructions
from .test_source_investigation_family import EDGES, HOMES, assignment, case, family

ORIGINAL_SHA = '0bec5b330670ae9b47f48180654ddb5e5f5e2bde041302b7d653181b048e489f'
SCENARIOS = ('valid', 'malformed_assignment', 'invalid_initial', 'invalid_pin',
    'missing_goal', 'saved_same', 'saved_changed')
BUILD_CASES = ('full_message', 'malformed_declaration', 'invalid_pin', 'declaration_without_contract')


@pytest.fixture(scope='module')
def original_methods():
    raw = (Path(__file__).parent / 'fixtures/source_request_assembly/runtime_original.py.txt').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ORIGINAL_SHA
    tree = ast.parse(raw)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Workflow')
    methods = [deepcopy(n) for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in {'selected', 'build'}]
    assert {n.name for n in methods} == {'selected', 'build'}
    namespace = dict(vars(runtime))
    exec(compile(ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[])),
        '<authenticated-original-A103-selected-build>', 'exec'), namespace)
    return SimpleNamespace(**{n.name: namespace[n.name] for n in methods})


@pytest.fixture(scope='module')
def instructions(family):
    # Original own-axis documents; no native execution or network.
    return LaunchInstructions.freeze(family.root / 'request-instructions')


class ConstructionObserved(Exception): pass
class ReconstructionObserved(Exception): pass


def host(family, parent_home, role, label, instructions):
    parent, context = case(family, parent_home, label)
    workflow = object.__new__(runtime.Workflow)
    workflow.run_id = context.run_id
    workflow.context = SimpleNamespace(require_run_id=lambda: context.run_id)
    workflow.grains = {name: SimpleNamespace(name=name) for name in
        {'annotation', 'scientific_process', *(own_role for _, own_role in HOMES)}}
    workflow.store = family.store
    workflow.journal = Journal(family.store, context.run_id)
    workflow.episode_bindings = family.registry
    workflow.receipts = EpisodeReceipts(family.store, context.run_id)
    workflow.receipts.bind(context.episode_id)
    workflow.receipts.receive(context.episode_id, [family.source['id']], kind='initial')
    # Explicit empty caller capability metadata, as in the original source
    # family fixture. Every actual allowed_children callback still executes.
    workflow.services = SimpleNamespace(capabilities=lambda: {})
    workflow.annotation_child_roles = None
    workflow.execution_binding = None
    workflow.inprocess_replay = None
    workflow.scientific_process_binding = None
    workflow.job_episodes = None
    workflow.native_timing_information = None
    workflow.native_event_information = None
    workflow.project_annotation_score = None
    workflow.resource_estimator = None
    workflow.inprocess_completion_order = None
    workflow.root_action_boundary = None
    workflow.project_credit = object()
    workflow.decision_protocol = None
    workflow.episode_branch_lifecycle = runtime.EPISODE_BRANCH_LIFECYCLE
    workflow.launch_instructions = instructions
    goal = runtime.EpisodeGoal.root(objective='Inspect this retained source', result_contract={'role': context.role})
    request = runtime.EpisodeRequest(goal, runtime.Record({'scope': plain(context.scope),
        'initial_report': {}, 'episode_assignment': plain(context.assignment)}))
    source = runtime.DecisionSource(workflow, context.path, request, plain(context.scope))
    selection = {'kind': 'episode_child', 'role': role, 'scope': plain(context.scope),
        'goal': 'Examine the original source', 'purpose': 'Return its qualified finding',
        'assignment': assignment(role, family.source), 'initial_report_json': '{"qualification":"unresolved"}',
        'schema_json': json.dumps({'type': 'object', 'properties': {'qualification': {
            'type': 'string', 'enum': ['unresolved', 'source-supported']}},
            'required': ['qualification'], 'additionalProperties': False})}
    return workflow, source, parent, selection


def observe(family, parent_home, child_home, role, scenario, methods, instructions, monkeypatch, label):
    workflow, source, parent, selection = host(family, parent_home, role, label, instructions)
    child = family.bindings[child_home]
    target_type = getattr(child, 'decision_source_type', runtime.DecisionSource)
    if scenario == 'malformed_assignment': selection['assignment']['unexpected'] = True
    if scenario == 'invalid_initial': selection['initial_report_json'] = '{'
    if scenario == 'invalid_pin': selection['assignment']['launch_instructions'] = {'invalid': 'original pin'}
    if scenario == 'missing_goal': del selection['goal']
    trace, captured = [], {}
    admitted_original = child.prepare_assignment
    allowed_original = parent.allowed_children
    pins_original = instructions.materialize
    receipt_original = workflow.receipts.bind
    constructor_original = target_type.__init__
    specialist_original = workflow.specialist
    selected_object = selection['assignment']
    def allowed(*args, **kwargs):
        trace.append('allowed_children'); return allowed_original(*args, **kwargs)
    def admit(context, received_role, selected, scope, operation_key):
        trace.append('child_admission')
        assert selected is selected_object
        assert received_role == role and plain(scope) == selection['scope']
        assert operation_key == workflow.run_id + ':' + source.episode_id + ':0'
        result = admitted_original(context, received_role, selected, scope, operation_key)
        captured['admitted'] = plain(result)
        return result
    def pins(selected):
        trace.append('materialize'); return pins_original(selected)
    def inherited(episode_id, parent_id=None):
        trace.append('inheritance')
        assert workflow.store.db.in_transaction
        result = receipt_original(episode_id, parent_id)
        captured['inheritance'] = plain(result)
        return result
    def constructed(self, *args, **kwargs):
        constructor_original(self, *args, **kwargs)
        if self.path[:-1] != source.path: return
        trace.append('constructed')
        assert workflow.store.db.in_transaction
        row = workflow.journal.row('runtime_actions', source.episode_id, 0)
        assert json.loads(row['action']) == selection and row['result'] is None
        captured.update(request=plain(self.request.as_record()), identity=self.episode_id,
            path=plain(self.path), known=sorted(workflow.receipts.known(self.episode_id)))
        assert family.source['id'] in captured['known']
        if scenario not in {'saved_same', 'saved_changed'}: raise ConstructionObserved()
    def specialist(value):
        if value.path[:-1] == source.path:
            trace.append('saved_request_compared')
            raise ReconstructionObserved()
        return specialist_original(value)
    workflow.build = MethodType(methods.build, workflow)
    with monkeypatch.context() as patch:
        patch.setattr(parent, 'allowed_children', allowed)
        patch.setattr(child, 'prepare_assignment', admit)
        patch.setattr(instructions, 'materialize', pins)
        patch.setattr(workflow.receipts, 'bind', inherited)
        patch.setattr(target_type, '__init__', constructed)
        patch.setattr(workflow, 'specialist', specialist)
        try:
            methods.selected(workflow, source, selection, 0)
        except (ConstructionObserved, ReconstructionObserved, WorkflowError, ValueError, TypeError, KeyError) as error:
            outcome = {'type': type(error).__module__ + '.' + type(error).__qualname__, 'message': str(error)}
        else:
            raise AssertionError('boundary unexpectedly returned a scientific workflow')
    # The deliberate stop/error rolls back the real parent commission and the
    # receipt prefix made inside it. No fabricated saved child is published.
    assert workflow.journal.row('runtime_actions', source.episode_id, 0) is None
    if 'identity' in captured:
        assert workflow.store.db.execute('SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
            (workflow.run_id, captured['identity'])).fetchone() is None
    return {'trace': trace, 'captured': captured, 'outcome': outcome}, workflow


def save_request(workflow, observation, *, changed):
    value = deepcopy(observation['captured']['request'])
    if changed: value['message']['initial_report'] = {'original_saved_difference': True}
    workflow.journal.save('runtime_episodes', {'episode_id': observation['captured']['identity'],
        'path': runtime._json(observation['captured']['path']), 'request': runtime._json(value),
        'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})


@pytest.mark.parametrize('parent_home,child_home,role', EDGES)
@pytest.mark.parametrize('scenario', SCENARIOS)
def test_original_and_current_selected_request_trace(family, original_methods, instructions, monkeypatch,
        parent_home, child_home, role, scenario):
    # Same actual parent path/run/selection gives exact comparable immutable
    # identities, not normalized/fabricated equality across different requests.
    label = 'assembly-' + scenario + '-' + parent_home.replace('/', '_') + '-' + role
    current_methods = SimpleNamespace(selected=runtime.Workflow.selected, build=runtime.Workflow.build)
    if scenario in {'saved_same', 'saved_changed'}:
        initial, workflow = observe(family, parent_home, child_home, role, 'valid',
            original_methods, instructions, monkeypatch, label)
        save_request(workflow, initial, changed=scenario == 'saved_changed')
    original, _ = observe(family, parent_home, child_home, role, scenario,
        original_methods, instructions, monkeypatch, label)
    current, _ = observe(family, parent_home, child_home, role, scenario,
        current_methods, instructions, monkeypatch, label)
    assert current == original
    expected_admission = 0 if scenario in {'invalid_initial', 'invalid_pin'} else 1
    assert current['trace'].count('child_admission') == expected_admission
    if scenario == 'valid':
        assert current['trace'] == ['allowed_children', 'materialize', 'child_admission',
            'materialize', 'inheritance', 'constructed']
        assert current['outcome']['type'].endswith('.ConstructionObserved')
    elif scenario == 'saved_same':
        assert current['trace'][-1] == 'saved_request_compared'
        assert current['outcome']['type'].endswith('.ReconstructionObserved')
    elif scenario == 'saved_changed':
        assert current['outcome'] == {'type': WorkflowError.__module__ + '.' + WorkflowError.__qualname__,
            'message': 'reconstructed immutable assignment differs'}
    else:
        assert 'constructed' not in current['trace']


@pytest.mark.parametrize('parent_home,child_home,role', EDGES)
def test_connected_named_endpoint_owns_original_request_assembly(family, parent_home, child_home, role):
    parent = family.bindings[parent_home]
    assert not hasattr(parent, 'prepare_child_request')
    method = parent.child_request_assembler(role)
    assert method.__self__ is parent
    assert method.__module__ == type(parent).__module__.removesuffix('.episode') + '.to_child_' + child_home.rsplit('/', 1)[-1]
    assert method.__name__ == '_assemble_' + child_home.rsplit('/', 1)[-1] + '_request'
    assert parent.child_request_assembler('not_declared') is None


@pytest.mark.parametrize('parent_home,child_home,role', EDGES)
@pytest.mark.parametrize('assembly_mode', ('absent', 'returns_none'))
def test_nonparticipant_build_override_keeps_original_keywords(family, instructions, monkeypatch,
        parent_home, child_home, role, assembly_mode):
    workflow, source, parent, selection = host(family, parent_home, role,
        'no-assembler-' + assembly_mode + '-' + parent_home.replace('/', '_') + '-' + role, instructions)
    calls = []
    dispatches = []
    # A nonparticipating parent can still advertise all its original methods;
    # this explicit proxy removes only the newly optional assembly capability.
    class ParentWithoutAssembly:
        def __getattr__(self, name):
            if name in {'child_request_assembler', 'prepare_child_request'}: raise AttributeError(name)
            return getattr(parent, name)
    class ParentDecliningAssembly(ParentWithoutAssembly):
        def child_request_assembler(self, selected_role):
            dispatches.append(selected_role)
            return None
    proxy = ParentWithoutAssembly() if assembly_mode == 'absent' else ParentDecliningAssembly()
    original_specialist = workflow.specialist
    workflow.specialist = lambda value: proxy if value is source else original_specialist(value)
    def original_build_signature(name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None,
            initial=None, job_assignment=None, episode_assignment=None, scientific_process=None,
            report_contract_declaration=None):
        calls.append((name, key, goal_text, plain(scope), plain(episode_assignment)))
        raise ConstructionObserved()
    workflow.build = original_build_signature
    with pytest.raises(ConstructionObserved): runtime.Workflow.selected(workflow, source, selection, 0)
    assert calls == [(role, 'child_0', selection['goal'], selection['scope'], selection['assignment'])]
    # Before the optional interface exists the original runtime never asks
    # for an assembler. Once installed, a declared decline is evaluated once.
    has_interface = 'request_assembler' in runtime.Workflow.build.__code__.co_varnames
    assert dispatches == ([role] if assembly_mode == 'returns_none' and has_interface else [])
    assert workflow.journal.row('runtime_actions', source.episode_id, 0) is None


@pytest.mark.parametrize('parent_home,child_home,role', EDGES)
@pytest.mark.parametrize('variant', BUILD_CASES)
def test_full_build_prelude_matches_original(family, original_methods, instructions, monkeypatch,
        parent_home, child_home, role, variant):
    from ..inprocess_replay import VERSION as COMPLETION_ORDER
    workflow, source, parent, selection = host(family, parent_home, role,
        'prelude-' + variant + '-' + parent_home.replace('/', '_') + '-' + role, instructions)
    workflow.inprocess_completion_order = COMPLETION_ORDER
    child = family.bindings[child_home]
    selected_type = getattr(child, 'decision_source_type', runtime.DecisionSource)
    original_constructor = selected_type.__init__
    schema = json.loads(selection['schema_json'])
    contract = runtime.TypedReportContract(selection['purpose'], schema, lambda *_: True)
    operands = dict(parent=source.request.goal, parent_path=source.path, contract=contract,
        initial={'qualification': 'unresolved'}, episode_assignment=selection['assignment'],
        job_assignment={'original_message_fixture': ['job', 3]},
        scientific_process={'original_message_fixture': ['process', None]})
    # These two opaque fields test the actual message assembler only. The
    # original later role/assignment checks are deliberately beyond the stop.
    if variant in {'malformed_declaration', 'declaration_without_contract'}:
        operands['report_contract_declaration'] = {'submitted_schema_json': '{}'}
    if variant == 'declaration_without_contract': operands['contract'] = None
    if variant == 'invalid_pin':
        operands['episode_assignment'] = {**selection['assignment'], 'launch_instructions': {'invalid': 'pin'}}
    observations = []
    for route in ('original', 'current_fallback', 'private_if_declared'):
        captured = {}
        def capture(self, *args, **kwargs):
            original_constructor(self, *args, **kwargs)
            captured.update(request=plain(self.request.as_record()), path=plain(self.path),
                identity=self.episode_id, known=sorted(workflow.receipts.known(self.episode_id)),
                goal_type=type(self.request.goal), request_type=type(self.request), message_type=type(self.request.message))
            raise ConstructionObserved()
        with monkeypatch.context() as patch:
            patch.setattr(selected_type, '__init__', capture)
            try:
                with workflow.store.transaction():
                    if route == 'private_if_declared' and hasattr(parent, 'child_request_assembler'):
                        runtime.Workflow.build(workflow, role, 'child_0', selection['goal'], selection['scope'],
                            **operands, request_assembler=parent.child_request_assembler(role))
                    elif route != 'original':
                        runtime.Workflow.build(workflow, role, 'child_0', selection['goal'], selection['scope'], **operands)
                    else:
                        original_methods.build(workflow, role, 'child_0', selection['goal'], selection['scope'], **operands)
            except (ConstructionObserved, AttributeError, ValueError, TypeError, KeyError) as error:
                captured['exception'] = (type(error), str(error))
            else:
                raise AssertionError('prelude boundary unexpectedly entered scientific work')
        observations.append(captured)
    assert observations[0] == observations[1] == observations[2]
    if variant == 'full_message':
        assert observations[1]['exception'][0] is ConstructionObserved
        assert observations[1]['goal_type'] is runtime.EpisodeGoal
        assert observations[1]['request_type'] is runtime.EpisodeRequest
        assert observations[1]['message_type'] is runtime.Record
        message = observations[1]['request']['message']
        assert message['job_assignment'] == operands['job_assignment']
        assert message['scientific_process'] == operands['scientific_process']
        assert message['inprocess_completion_order'] == {'version': COMPLETION_ORDER}
        assert family.source['id'] in observations[1]['known']
    else:
        assert 'request' not in observations[1]
        if variant == 'declaration_without_contract':
            # Original child-goal construction precedes the later declaration
            # guard and dereferences this absent contract first.
            assert observations[1]['exception'] == (AttributeError, "'NoneType' object has no attribute 'schema'")
