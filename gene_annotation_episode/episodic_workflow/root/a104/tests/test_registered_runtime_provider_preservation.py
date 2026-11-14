"""Finite A104 provider preservation, with actual constructors where required.

The source identity check covers all selected definitions. Behavioral probes
exercise original provider lookup timing, error order, and the three actual
Homology input regressions. Other probes use explicit engineering callback
ports; none executes a native job/model or an earlier accepted test cohort.
"""
from __future__ import annotations
import ast
import asyncio
import builtins
from copy import deepcopy
import hashlib
import importlib
import inspect
import json
from pathlib import Path
from types import FunctionType, SimpleNamespace

import pytest

from .a104_parent_directional_checks import genuine_host, ROUTES, SCHEMA, INITIAL
from .test_a104_implicit_parent_protocol import own, forbidden

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a104'
FIXTURE = Path(__file__).parent / 'fixtures/source_request_assembly/a104_registered_provider_preservation.json.txt'
FIXTURE_SHA = '83130a45c6ecd1296b2443e0040b448e2b49a7336be52e786759acf47bacce87'
FAMILIES = ('api', 'homology', 'launch_hpc', 'launch_non_hpc', 'literature', 'monitor',
            'native_hpc', 'native_local', 'planning_allocation', 'prediction',
            'results_hpc', 'results_non_hpc', 'scientific')

def bundle():
    raw = FIXTURE.read_bytes(); assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA
    return json.loads(raw)

def current(row):
    module = importlib.import_module(row['module'])
    owner = module if row['owner'] is None else vars(module)[row['owner']]
    return vars(owner)[row['member']]

def source_node(row, function):
    source = inspect.getsource(function)
    tree = ast.parse(source if row['owner'] is None else 'class _PreservedOwner:\n' + source)
    node, = tree.body if row['owner'] is None else tree.body[0].body
    assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == row['member']
    return node

def oracle(row, mode):
    namespace_owner = own('runtime_prompt' if row['namespace'].endswith('runtime_prompt') else 'runtime')
    if mode == 'candidate': return current(row)
    namespace = vars(namespace_owner) if mode == 'original' else {
        '__builtins__': vars(builtins), '__name__': row['module'], '__package__': row['module'].rsplit('.', 1)[0],
        **{alias: vars(namespace_owner)[name] for alias, name in row['static_provider_imports'].items()}}
    code = row['original_code'] if mode == 'original' else row['installed_code']
    scratch = dict(namespace)
    exec(compile(code, str(FIXTURE), 'exec'), scratch)
    function = scratch[row['member']]
    restored = FunctionType(function.__code__, namespace, function.__name__, function.__defaults__)
    restored.__kwdefaults__ = function.__kwdefaults__
    return restored

class ProviderFailure(Exception): pass
class EarlyProviderRead(Exception): pass

@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    monkeypatch.setattr('subprocess.Popen', forbidden)
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', forbidden)

def test_all_selected_definitions_and_retained_private_APIs():
    packet = bundle()
    assert len(packet['members']) == 1133 and len(packet['retained']) == 326
    for row in packet['members']:
        function = current(row); module = importlib.import_module(row['module'])
        node = source_node(row, function)
        assert hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest() == row['after_AST_sha256']
        assert function.__globals__ is vars(importlib.import_module(row['namespace']))
        assert function.__module__ == row['module'] and function.__qualname__ == row['qualified_name']
        assert function.__code__.co_filename == module.__file__ and function.__closure__ is None
    for row in packet['retained']:
        function = current(row); module = importlib.import_module(row['module'])
        node = source_node(row, function)
        assert hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest() == row['AST_sha256']
        assert function.__globals__ is vars(module)
    assert packet['registered_home_count'] == 60 and packet['source_count'] == 543

def finish_observation(row, mode, route, failure, monkeypatch):
    runtime = own('runtime'); events = []
    def frozen(*args, **kwargs): raise EarlyProviderRead('captured provider read')
    def late_record(value):
        events.append(('Record', value))
        if failure: raise ProviderFailure('late record failure')
        return {'record': value}
    def serialize(value): events.append(('_json', value)); return repr(value)
    def form(values, schema, facts):
        events.append(('form', values, schema, facts)); runtime._json = serialize
        return {'qualification': 'unresolved'}
    def saved(*args):
        events.append(('row', args))
        runtime.json = SimpleNamespace(loads=lambda value: events.append(('loads', value)) or {'qualification': 'unresolved'})
        return {'form': 'saved engineering form'} if route == 'saved' else None
    def facts(source, completion_record):
        events.append(('facts', completion_record)); runtime.form_with_facts = form
        return {'qualified': 'unresolved'}
    async def release(episode_id):
        events.append(('release_enter', episode_id)); await asyncio.sleep(0)
        runtime.Record = late_record; events.append(('release_done', episode_id))
    workflow = SimpleNamespace(source_credit_view=lambda source: {'credit': .25}, pending_handles=lambda source: ['pending'],
        episode_bindings=SimpleNamespace(current_report_facts=lambda context: {'qualification': 'unresolved'}),
        binding_context=lambda source: source, release=release, facts=facts,
        journal=SimpleNamespace(row=saved, save=lambda *args: events.append(('save', args))))
    source = SimpleNamespace(workflow=workflow, episode_id='original-provider-boundary', report_values={'qualification': 'unresolved'},
        request=SimpleNamespace(report_contract=None if route == 'uncontracted' else SimpleNamespace(schema=SCHEMA)))
    with monkeypatch.context() as patch:
        for name in ('Record', '_json', 'form_with_facts'): patch.setattr(runtime, name, frozen)
        patch.setattr(runtime, 'json', SimpleNamespace(loads=frozen))
        function = oracle(row, mode)
        try: result = ('returned', asyncio.run(function(source, {'completion': 'existing engineering input'})))
        except (ProviderFailure, EarlyProviderRead) as error: result = (type(error).__name__, str(error))
    return result, events

@pytest.mark.parametrize('family', FAMILIES)
def test_original_late_return_provider_for_each_extraction_family(family, monkeypatch):
    row = bundle()['finish'][family]
    original = finish_observation(row, 'original', 'uncontracted', False, monkeypatch)
    assert finish_observation(row, 'candidate', 'uncontracted', False, monkeypatch) == original
    assert finish_observation(row, 'installed', 'uncontracted', False, monkeypatch)[0][0] == 'EarlyProviderRead'
    assert original[1][-2][0] == 'release_done' and original[1][-1][0] == 'Record'

@pytest.mark.parametrize('route,failure', (('saved', False), ('fresh', False), ('uncontracted', True)), ids=('saved', 'fresh', 'late_failure'))
def test_saved_fresh_and_failed_return_provider_order(route, failure, monkeypatch):
    row = bundle()['finish']['scientific']
    original = finish_observation(row, 'original', route, failure, monkeypatch)
    assert finish_observation(row, 'candidate', route, failure, monkeypatch) == original
    assert finish_observation(row, 'installed', route, failure, monkeypatch)[0][0] == 'EarlyProviderRead'
    assert original[0][0] == ('ProviderFailure' if failure else 'returned')

@pytest.mark.parametrize('family', ('scientific', 'homology'))
@pytest.mark.parametrize('failure', (False, True), ids=('returned', 'provider_failure'))
def test_constructor_reads_schema_after_original_message_callback(family, failure, monkeypatch):
    runtime = own('runtime'); row = bundle()['constructor'][family]
    def exercise(mode):
        events = []
        def schema(value):
            events.append(('schema', value))
            if failure: raise ProviderFailure('late schema failure')
            return {'original': value}
        def message():
            events.append('message'); runtime.interpretation_schema = schema
            return {'initial_report': {'qualification': 'unresolved'}}
        role = 'scientific_process' if family == 'scientific' else 'job_monitor'
        workflow = SimpleNamespace(context='context', grains={role: 'grain'})
        request = SimpleNamespace(message=SimpleNamespace(as_record=message), report_contract=SimpleNamespace(schema=SCHEMA))
        source = SimpleNamespace()
        with monkeypatch.context() as patch:
            patch.setattr(runtime, 'Episode', SimpleNamespace(identity=lambda *args, **kwargs: events.append(('identity', args, kwargs)) or SimpleNamespace(episode_id='source')))
            patch.setattr(runtime, 'interpretation_schema', lambda _: (_ for _ in ()).throw(EarlyProviderRead('early schema')))
            function = oracle(row, mode)
            try: result = function(source, workflow, ((role, 'constructor-boundary'),), request, 'scope')
            except (ProviderFailure, EarlyProviderRead) as error: result = (type(error).__name__, str(error))
        state = dict(vars(source)); state.pop('workflow'); state.pop('request')
        return result, state, events
    expected = exercise('original')
    assert exercise('candidate') == expected
    assert exercise('installed')[0][0] == 'EarlyProviderRead'

@pytest.mark.parametrize('family,failure', (('scientific', False), ('api', False), ('homology', False), ('scientific', True)), ids=('scientific', 'api', 'homology', 'specialist_failure'))
def test_private_composer_preserves_original_late_prompt_providers(family, failure, monkeypatch):
    prompt = own('runtime_prompt'); row = bundle()['prompt'][family]
    actual_protocol, actual_instructions = prompt.DECISION_EXCHANGE_PROTOCOL, prompt.INSTRUCTIONS
    def exercise(mode):
        events = []
        def specialize(context):
            events.append('specialist_instructions')
            if failure: raise ProviderFailure('original specialist failure')
            return 'private instructions'
        binding = SimpleNamespace(instructions=specialize, replaces_default_instructions=False)
        def permits(source, action):
            events.append(('permits', action))
            return False
        class Knowledge:
            @property
            def instructions(self):
                events.append('knowledge_instructions')
                prompt.DECISION_EXCHANGE_PROTOCOL = actual_protocol
                return '\nUnresolved engineering knowledge input.'
        role = {'scientific': 'scientific_process', 'api': 'launch_api', 'homology': 'job_monitor'}[family]
        source = SimpleNamespace(path=((role, 'prompt-boundary'),), workflow=SimpleNamespace(
            is_job_source=lambda source: family == 'homology', job_episodes=SimpleNamespace(instructions=lambda role: actual_instructions),
            specialist=lambda source: None if family == 'homology' else binding, binding_context=lambda source: source,
            permits_common_action=permits, native_event_information=None, decision_protocol=actual_protocol, knowledge=Knowledge()))
        with monkeypatch.context() as patch:
            patch.setattr(prompt, 'DECISION_EXCHANGE_PROTOCOL', 'unselected earlier engineering operand')
            function = oracle(row, mode)
            try: result = ('returned', function(source, {'tool_knowledge': {}}))
            except ProviderFailure as error: result = (type(error).__name__, str(error))
        return result, events
    original = exercise('original'); assert exercise('candidate') == original
    installed = exercise('installed')
    if failure: assert installed == original and original[1] == ['specialist_instructions']
    else:
        assert 'Use request_context exchanges for your own attempt metadata' in original[0][1]
        assert 'Use request_context exchanges for your own attempt metadata' not in installed[0][1] and installed != original
        assert 'knowledge_instructions' in original[1]

@pytest.mark.parametrize('home', ('homology_job_submission', 'homology_job_monitoring', 'homology_result_acquisition'))
def test_genuine_homology_inputs_original_installed_and_corrected(home, tmp_path, monkeypatch):
    runtime = own('runtime'); row = bundle()['homology_inputs'][home]
    route, = [r for r in ROUTES if r[0] == home]
    with genuine_host(tmp_path, route) as (workflow, parent, binding):
        contract = runtime.TypedReportContract('Retain the existing unresolved qualification', SCHEMA, lambda *_: True)
        request = runtime.EpisodeRequest(runtime.EpisodeGoal.child(parent.request.goal,
            objective='Inspect original input providers without acquiring work', result_contract=SCHEMA),
            runtime.Record({'scope': parent.scope, 'initial_report': INITIAL, 'job_assignment': {}}), contract)
        path = parent.path + ((route[2], 'provider-input-boundary'),)
        source = binding.decision_source_type(workflow, path, request, parent.scope)
        assert type(source) is binding.decision_source_type
        assert source.episode_id == runtime.Episode.identity(workflow.context, workflow.grains[route[2]],
            'provider-input-boundary', parent_path=parent.path).episode_id
        assert workflow.specialist(source) is None and workflow.is_job_source(source)
        permitted = workflow.available_child_roles(source)
        original_parent = importlib.import_module(PACKAGE + '.tests.test_a104_implicit_parent_protocol')
        assert route[2] not in workflow.grain_names and route[2] not in workflow.episode_bindings.roles
        assert workflow.declared_child_roles(route[2], path=path) == permitted == ()
        assert original_parent.original_function('Workflow', 'declared_child_roles')(workflow, route[2], path=path) == ()
        assert original_parent.original_function('Workflow', 'available_child_roles')(workflow, source) == ()
        initial = {'current_credit': {}, 'pending_work': workflow.pending_work(parent)}
        with monkeypatch.context() as patch:
            child_option_calls = []
            def no_child_options(*args, **kwargs):
                child_option_calls.append((args, kwargs))
                raise AssertionError('A declared childless Homology task cannot request child options')
            patch.setattr(runtime, 'child_option_information', no_child_options)
            patch.setattr(workflow, 'resource_context', lambda source: None)
            patch.setattr(workflow, 'shared_information_context', lambda source: None)
            patch.setattr(workflow.launch_instructions, 'context', lambda: {})
            patch.setattr(workflow.launch_instructions, 'materialize', lambda value: None)
            patch.setattr(workflow, 'native_estimation_context', lambda source, context: None)
            patch.setattr(workflow, 'waiting_support', lambda source, context: {'original_control_port': 'unknown'})
            patch.setattr(own('episode_work_report'), 'completed_action_reports', lambda *args, **kwargs: [])
            assert workflow.execution_expectations is None and workflow.resource_estimator is None
            original = oracle(row, 'original')(source, deepcopy(initial), 0, None)
            assert oracle(row, 'candidate')(source, deepcopy(initial), 0, None) == original
            assert 'child_options' not in original and child_option_calls == []
            assert original['completed_action_reports'] == []
            installed = oracle(row, 'installed')
            assert 'Mapping' not in installed.__globals__ and 'child_option_information' not in installed.__globals__
            # Mapping is actually read on this permitted childless path. The
            # child-option provider remains a source-namespace identity fact;
            # no unsupported child edge is supplied to exercise that branch.
            with pytest.raises(NameError, match='Mapping'):
                installed(source, deepcopy(initial), 0, None)
            assert child_option_calls == []
        assert not workflow.store.db.execute('SELECT 1 FROM runtime_actions').fetchone()

def test_callee_is_read_before_argument_callback_and_later_callees_are_live(monkeypatch):
    runtime = own('runtime'); row = bundle()['exchange_schema']
    def exercise(mode):
        events = []
        def old_object(value): events.append('old_object'); return {'old': value}
        def new_object(value): events.append('new_object'); return {'new': value}
        def lookup(*args): events.append('lookup'); runtime._object = new_object; return {'lookup': 'contract'}
        with monkeypatch.context() as patch:
            patch.setattr(runtime, '_object', old_object); patch.setattr(runtime, 'composition_lookup_schema', lookup)
            result = oracle(row, mode)(SimpleNamespace(workflow=object()), {'properties': {'selection': {'type': 'object'}}})
        return result, events
    expected = exercise('original'); assert exercise('candidate') == expected
    assert expected[1] == ['lookup', 'old_object', 'new_object', 'old_object']
    assert exercise('installed') != expected
