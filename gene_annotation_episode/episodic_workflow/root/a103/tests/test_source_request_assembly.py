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


