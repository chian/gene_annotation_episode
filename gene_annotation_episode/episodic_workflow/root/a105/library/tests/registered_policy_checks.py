"""Applicable registered policy calls; no model/native action is acquired.

Bindings, registry, Workflow, Store and task construction are real. The
Scientific filled-context validation and instruction-library data are explicit
ports in this boundary fixture, not a scientific assignment/execution claim.
"""
import ast
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from functools import partial
from importlib import import_module
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
from types import FunctionType, SimpleNamespace
from unittest.mock import patch

from . import registered_provider_checks as prior

PACKAGE, AXIS, RUNTIME = prior.PACKAGE, prior.AXIS, prior.RUNTIME
from ...tests import implicit_parent_checks as HOST
from ... import runtime_prompt as PROMPT
DATA = json.loads((Path(__file__).parent / 'fixtures/registered_policy/consumers.json').read_text())


class BoundaryReached(Exception):
    pass


class JobPorts:
    """Original configurable job interface; roles never collide with these sources."""
    def __init__(self, events):
        self.events = events
        self.failure = None
    def recover_statistics(self):
        self.events.append('recover_statistics')
    @property
    def roles(self):
        self.events.append('job_roles')
        if self.failure is not None:
            raise self.failure
        return ('controlled_job',)
    def fact_sources(self, role):
        return {}
    def describe(self):
        self.events.append('job_description')
        if self.failure is not None:
            raise self.failure
        return {'controlled_job': {'description': 'Actual configured optional job port'}}


def each_family(check):
    """All15 actual owners, with one genuine Literature entry tree per graph."""
    def run(directory, mode):
        for family in ('annotation', 'scientific'):
            check(directory / family, mode, family)
    return run


@contextmanager
def connected(directory, *, family, explicit_graph=False):
    events = []
    jobs = JobPorts(events)
    assert family in ('annotation', 'scientific')
    owner = ('scientific_process.' if family == 'scientific' else '') + 'published_evidence_assessment.episode'
    children = []
    def first(services):
        children.extend(import_module(PACKAGE + '.' + owner).create_binding_tree(services))
        assert len(children) == 7
        scientific_type = import_module(PACKAGE + '.scientific_process.episode').ScientificProcessEpisode
        return scientific_type(services, library=HOST.EmptyCatalog(), tool_library=HOST.EmptyCatalog(),
            child_roles=(('scientific_process', 'literature') if family == 'scientific'
                         else ('scientific_process',)))
    factories = (first, *(lambda services, index=index: children[index] for index in range(7)))
    graph = (('scientific_process', 'literature') if family == 'annotation'
             else ('scientific_process',)) if explicit_graph else None
    root_role = 'scientific_process' if family == 'scientific' else 'annotation'
    with HOST.actual_workflow(directory, factories=factories, job_episodes=jobs,
                              workflow_class=partial(RUNTIME.Workflow, root_role=root_role),
                              annotation_child_roles=graph) as workflow:
        assert workflow.annotation_child_roles == graph
        assert workflow.episode_bindings.entry_roles.count('literature') == 1
        if family == 'annotation':
            root = HOST.root(workflow).source
            goal, initial_message, scope = root.request.goal, root.request.message.as_record(), root.scope
        else:
            # The authentic standalone-root API is used at construction. These
            # are the original build request operands, not a fabricated process.
            scope = workflow.store.validate_scope()
            goal = RUNTIME.EpisodeGoal.root(objective='Preserve the assigned unknown',
                                            result_contract={'role': root_role})
            initial_message = {'scope': scope, 'initial_report': {}}
        workflow.native_event_information = None  # A108's original prompt requires this optional port.
        sources = []
        selected = [row for row in DATA['homes'] if
                    (row['scientific'] and family == 'scientific') or
                    (not row['scientific'] and row['binding_path'].startswith('scientific_process/') == (family == 'scientific'))]
        assert len(selected) == (8 if family == 'scientific' else 7)
        for row in selected:
            binding = workflow.episode_bindings._by_path[row['binding_path']]
            assert type(binding).__module__ == row['episode_module']
            assert binding.decision_source_type.__name__ == row['task_class']
            parts = row['binding_path'].split('/')
            path = [('annotation', 'root')] if family == 'annotation' else []
            for count in range(1, len(parts) + 1):
                parent = workflow.episode_bindings._by_path['/'.join(parts[:count])]
                role, = parent.roles
                path.append((role, 'registered-' + str(count)))
            message = deepcopy(initial_message)
            if row['scientific']:
                contracts = import_module(PACKAGE + '.scientific_process.scientific_contracts')
                message['episode_assignment'] = {'selection': {
                    'version': contracts.SELECTION_VERSION, 'evidence_axis': {'slot': 'evidence_axis'}}}
                # The selected method is genuine. Its independently exercised
                # filled scientific process validator is a supplied prerequisite
                # here; no fabricated successful process record is created.
                binding.validate_context = lambda context, selected=binding: (
                    selected._role(context.role), events.append(('filled_context_port', context.role)))[0]
                binding.validate_execution_context = lambda context, selected=binding: (
                    selected._role(context.role), events.append(('execution_context_port', context.role)))[0]
                binding.library.resolve = lambda reference: {'entry_version': contracts.INSTRUCTION_VERSION}
            request = RUNTIME.EpisodeRequest(goal, RUNTIME.Record(message), None)
            source = binding.decision_source_type(workflow, tuple(path), request, scope)
            assert workflow.specialist(source) is binding
            assert source.path[-1][0] in binding.roles
            sources.append((row, binding, source))
        # Every configured specialist edge has its genuine direct counterpart,
        # including Scientific recursion; no missing route is hidden by this test.
        for row, binding, source in sources:
            for role in binding.child_roles(source.path[-1][0]):
                child = workflow.episode_bindings.for_child(source.path, role)
                assert role in child.roles
        if family == 'annotation':
            for role in ('scientific_process', 'literature'):
                assert role in workflow.episode_bindings.for_child(root.path, role).roles
            scientific = workflow.episode_bindings.for_child(root.path, 'scientific_process')
            assert scientific.child_roles('scientific_process') == ('scientific_process',)
            assert workflow.episode_bindings.for_child(
                (*root.path, ('scientific_process', 'recursive-owner')), 'scientific_process') is scientific
        yield workflow, jobs, sources, events


def outcome(call, error):
    try:
        return ('value', call())
    except Exception as caught:
        return ('error', type(caught).__module__, type(caught).__qualname__,
                caught.args, caught is error)


def original_for(row, name):
    if not row['pilot']:
        return prior.original(name)
    operand = DATA['pilot_originals'][name]
    path = Path(__file__).parent / 'fixtures/registered_policy' / operand['fixture']
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == operand['sha256']
    cls, = [n for n in ast.parse(raw).body if isinstance(n, ast.ClassDef)
            and n.name == operand['class']]
    method, = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    namespace = vars(import_module(operand['current_module']))
    temporary = dict(namespace)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[deepcopy(method)], type_ignores=[])),
                 str(path), 'exec'), temporary)
    compiled = temporary[name]
    result = FunctionType(compiled.__code__, namespace, name, compiled.__defaults__, compiled.__closure__)
    result.__kwdefaults__ = compiled.__kwdefaults__
    return result


@each_family
def check_instructions(directory, mode, family):
    with connected(directory, family=family) as (workflow, jobs, sources, events):
        for row, binding, source in sources:
            current = import_module(row['instruction_module']).instructions
            original = HOST.original_instructions()
            observations = []
            for before in (True, False):
                events.clear()
                failure = OSError('actual job roles provider unavailable')
                jobs.failure = failure if mode == 'job-error' else None
                original_text = PROMPT.INSTRUCTIONS
                actual_instructions = binding.instructions
                actual_context = workflow.binding_context
                def context(value):
                    events.append(('binding_context', value.path))
                    return actual_context(value)
                def text(value):
                    events.append('specialist_instructions')
                    result = actual_instructions(value)
                    PROMPT.REASONING_COMMIT_REQUIREMENT = 'Original namespace rebound after the actual specialist callback.'
                    PROMPT.DECISION_EXCHANGE_PROTOCOL = 'controlled-original-protocol'
                    return result
                with patch.object(PROMPT, 'INSTRUCTIONS', original_text + '\nOriginal namespace selected before invocation.'), \
                     patch.object(PROMPT, 'REASONING_COMMIT_REQUIREMENT', 'initial requirement'), \
                     patch.object(PROMPT, 'DECISION_EXCHANGE_PROTOCOL', 'initial protocol'), \
                     patch.object(binding, 'instructions', text), \
                     patch.object(workflow, 'binding_context', context):
                    workflow.decision_protocol = 'controlled-original-protocol'
                    workflow.native_event_information = object() if mode == 'native-present' else None
                    result = outcome(lambda: (original if before else current)(source, {}), failure)
                observations.append((result, deepcopy(events)))
                if mode == 'job-error':
                    assert result[0] == 'error' and result[-1]
                    assert events == ['job_roles']
                else:
                    assert result[0] == 'value' and 'Original namespace rebound' in result[1]
                    assert events[0] == 'job_roles'
                    assert 'specialist_instructions' in events
                    # Actual nominal permissions, never a fake true predicate.
                    permitted = binding.permitted_common_actions(actual_context(source))
                    assert ('wait' in permitted) == row['scientific']
                    assert ('A pending_child_' in result[1]) == row['scientific']
            jobs.failure = None
            assert observations[0] == observations[1], row


@each_family
def check_decision(directory, mode, family):
    with connected(directory, family=family) as (workflow, jobs, sources, events):
        for row, binding, source in sources:
            observations = []
            request_context = {'pending_work': None, 'visible_record_refs': [],
                'literature_completed_work': {}, '_completed_work_axis_results': {}}
            schema = {'type': 'object', 'properties': {}, 'additionalProperties': False}
            if mode == 'saved-receipt':
                workflow.journal.save('runtime_model_calls', {'episode_id': source.episode_id,
                    'call_index': 0, 'purpose': 'decision', 'request': json.dumps({
                        'context': request_context, 'schema': schema}), 'response': None})
            for before in (True, False):
                events.clear()
                source.calls = 0
                failure = OSError('configured job roles read failed before resource estimates')
                jobs.failure = failure if mode == 'resource-error' else None
                workflow.contract_information_profile = lambda source: None
                workflow.resource_context = lambda source: None
                workflow.shared_information_context = lambda source: None
                workflow.launch_instructions = SimpleNamespace(context=lambda: {}, materialize=lambda value: None)
                workflow.available_child_roles = lambda source: ()
                workflow.episode_bindings.initial_decision_context = lambda context: {}
                workflow.execution_expectations = None
                workflow.resource_estimator = SimpleNamespace(estimate=prior.forbidden,
                    estimate_context=lambda value: [])
                workflow.native_estimation_context = lambda source, context: None
                workflow.waiting_support = lambda source, context: events.append('scientific_wait_support') or {}
                workflow.freeze_literature_numerical_contracts = lambda *args: None
                workflow.decision_protocol = None
                workflow.history_preview = lambda source, **kwargs: {}
                workflow.uses_received_record_context = lambda source: False
                def known(episode_id):
                    events.append('known_received_references')
                    return ()
                def receive(episode_id, references, **kwargs):
                    events.append(('receive_decision_inputs', list(references), kwargs))
                    raise BoundaryReached('before original decision journal publication')
                workflow.receipts = SimpleNamespace(known=known, receive=receive)
                function = original_for(row, 'call') if before else type(source).call
                result = outcome(lambda: asyncio.run(function(source, deepcopy(request_context), schema)), failure)
                if mode == 'resource-error':
                    assert result[0] == 'error' and result[-1]
                    assert events[-1] == 'job_roles'
                else:
                    assert result[0] == 'error' and result[2] == 'BoundaryReached'
                    assert events[-1][0] == 'receive_decision_inputs'
                    assert events[-2] == 'job_roles'
                    if mode == 'fresh-receipt':
                        assert ('scientific_wait_support' in events) == row['scientific']
                    else:
                        assert 'scientific_wait_support' not in events
                observations.append((result, deepcopy(events)))
            jobs.failure = None
            workflow.receipts = None
            assert observations[0] == observations[1], row


def cold_instructions(directory):
    tree = Path(__file__).resolve().parents[6]
    script = r'''
import importlib, json, pathlib, sys
paths, name, package, tree = json.loads(sys.argv[1]), sys.argv[2], sys.argv[3], pathlib.Path(sys.argv[4])
sys.path[:] = paths
assert package + '.runtime_prompt' not in sys.modules
owner = importlib.import_module(name)
prompt = importlib.import_module(package + '.runtime_prompt')
assert owner._original_prompt is prompt
assert owner.instructions.__module__ == name
origins = {}
for key, module in tuple(sys.modules.items()):
    if key == 'gene_annotation_episode' or key.startswith('gene_annotation_episode.'):
        path = pathlib.Path(module.__file__).resolve(strict=True)
        assert path.is_relative_to(tree), (key, str(path))
        origins[key] = str(path.relative_to(tree))
print(json.dumps({'entry': name, 'same_prompt_object': True, 'origins': origins}, sort_keys=True))
'''
    for index, row in enumerate(DATA['homes']):
        current = directory / str(index)
        current.mkdir(parents=True)
        environment = dict(os.environ)
        for key in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONOPTIMIZE'):
            environment.pop(key, None)
        for key in ('TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME'):
            path = current / key.lower(); path.mkdir(); environment[key] = str(path)
        environment['PYTHONDONTWRITEBYTECODE'] = '1'
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, json.dumps(sys.path),
            row['instruction_module'], PACKAGE, str(tree)], cwd=current, env=environment,
            check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        value = json.loads(result.stdout)
        assert value['entry'] == row['instruction_module'] and value['same_prompt_object']
        assert row['instruction_module'] in value['origins']
        (current / 'cold-imports.json').write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def context_source(source, workflow, events):
    """Explicit non-executing decision-context ports around real policy methods."""
    source.feedback = source.last_outcome = source.last_outcome_index = None
    source._restored = True
    source._execution_context = None
    source.report_values, source.report_basis, source.interpret_schema = {}, [], {'type': 'object'}
    source.calls = 0
    workflow.execution_binding = workflow.inprocess_replay = None
    workflow.working_state = lambda value: {}
    workflow.local_outcome_preview = lambda value, **kwargs: value
    workflow.source_credit_view = lambda value: {'credit': 0.25}
    workflow.receipt_projection = lambda value: False
    workflow.source_credit_binding = lambda value: {'kind': 'actual supplied scalar'}
    workflow.pending_work = lambda value: None
    workflow.delivery_status = lambda identity: []
    workflow.catalog = lambda scope, *, source: []
    workflow.extra_report_sources = lambda value: {}
    workflow.controller_binding = None
    workflow.knowledge = SimpleNamespace(context=lambda: {})
    def annotation_context(scope, *, source):
        events.append('annotation_context')
        raise BoundaryReached('after actual own Scientific policy')
    workflow.annotation_context = annotation_context


@each_family
def check_context(directory, mode, family):
    with connected(directory, family=family, explicit_graph=mode == 'explicit-graph') as (workflow, jobs, sources, events):
        for row, binding, source in sources:
            observations = []
            for before in (True, False):
                events.clear()
                context_source(source, workflow, events)
                # Exercise real job_episode_options in both its historical
                # absent-marker and explicit graph paths. Declared/available
                # role evaluation remains original, with actual private binding.
                workflow.services.capabilities = lambda: {}
                actual_describe = jobs.describe
                failure = OSError('actual job description unavailable')
                def describe():
                    if mode == 'description-error':
                        events.append('job_description')
                        raise failure
                    return actual_describe()
                captured = []
                def model_inputs(value, *, reports):
                    events.append('model_inputs')
                    captured.append(deepcopy(value))
                    if mode != 'own-scientific-guard':
                        raise BoundaryReached('after actual job context')
                    return value
                view = SimpleNamespace(units_consumed=0, child_reports=(), controller_state={}, model_inputs=model_inputs)
                actual_scientific = workflow.is_scientific_source
                def scientific(value):
                    events.append('is_scientific_source')
                    return actual_scientific(value)
                with patch.object(jobs, 'describe', describe), patch.object(workflow, 'is_scientific_source', scientific):
                    def invoke():
                        if before:
                            return asyncio.run(original_for(row, 'next')(source, view))
                        return asyncio.run(source.next(view))
                    result = outcome(invoke, failure)
                if mode == 'description-error':
                    assert result[0] == 'error' and result[-1] and not captured
                else:
                    assert result[0] == 'error' and result[2] == 'BoundaryReached'
                    assert len(captured) == 1
                    expected = None if mode == 'explicit-graph' else {
                        'controlled_job': {'description': 'Actual configured optional job port'}}
                    assert captured[0]['job_episode_options'] == expected
                    if mode == 'own-scientific-guard':
                        assert events[-2:] == ['is_scientific_source', 'annotation_context']
                observations.append((result, captured, deepcopy(events)))
            assert observations[0] == observations[1], row
