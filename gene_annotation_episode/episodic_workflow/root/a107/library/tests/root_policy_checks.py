"""Actual Workflow root-policy boundaries against permanent original functions.

Only named provider/dispatch ports are supplied. No child iterator, native job,
model provider or scientific calculation runs. The cold-entry subprocess imports
the same guarded snapshot under the owning serial workload.
"""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from .policy_checks import original, oracle, source_for, scientific_binding


BOUNDARIES = ('default-role-order', 'configured-second-read', 'late-role-filter',
    'fresh-saved-credit-validation', 'wait-and-tool-admission', 'return-sources',
    'catalogue-late-provider', 'execute-composition-bypass', 'saved-tool-replay')


def root_observation(directory, boundary, *, before):
    runtime = original.module('runtime')
    events = []
    class MutableConfigured(runtime.Workflow):
        armed = False
        @property
        def annotation_child_roles(self):
            if not self.armed:
                return self._configured
            events.append('configured-read')
            return ('scientific_process',) if events.count('configured-read') == 1 else None
        @annotation_child_roles.setter
        def annotation_child_roles(self, value):
            self._configured = value
    workflow_type = MutableConfigured if boundary == 'configured-second-read' else runtime.Workflow
    with original.actual_workflow(directory, workflow_class=workflow_type) as workflow, ExitStack() as stack:
        def call(name, *args, **kwargs):
            method = oracle(name) if before else getattr(runtime.Workflow, name)
            return method(workflow, *args, **kwargs)
        if boundary == 'configured-second-read':
            workflow.armed = True
            answer = call('declared_child_roles', 'annotation')
            assert answer is None and events == ['configured-read', 'configured-read']
            return {'events': events, 'answer': answer}
        source, _ = source_for(workflow, 'annotation')
        workflow.root_action_boundary = runtime.ROOT_BOUNDARY_VERSION
        if boundary == 'default-role-order':
            binding = scientific_binding(workflow)
            original.install_entry(workflow, binding)
            class Jobs:
                @property
                def roles(self):
                    events.append('job-roles'); return ('launch',)
            workflow.job_episodes = Jobs()
            workflow.scientific_process_binding = None
            first = call('_default_scientific_child_roles')
            workflow.scientific_process_binding = binding
            second = call('_default_scientific_child_roles')
            assert first == ('improvement', 'launch', 'scientific_process')
            assert second == ('launch', 'scientific_process') and events == ['job-roles'] * 2
            answer = (first, second)
        elif boundary == 'late-role-filter':
            workflow.project_credit = SimpleNamespace(task_credit=False)
            def declared(role, *, path):
                events.append(('declared', role)); return ('improvement', 'scientific_process')
            def specialist(actual):
                assert actual is source
                events.append('specialist'); workflow.project_credit.task_credit = True
                return None
            stack.enter_context(patch.object(workflow, 'declared_child_roles', declared))
            stack.enter_context(patch.object(workflow, 'specialist', specialist))
            answer = call('available_child_roles', source)
            assert answer == ('scientific_process',)
            assert events == [('declared', 'annotation'), 'specialist']
        elif boundary == 'fresh-saved-credit-validation':
            workflow.project_credit = SimpleNamespace(task_credit=True)
            workflow.annotation_child_roles = None
            records = original.module('scientific_process_records')
            selection = {'kind': 'episode_child', 'role': 'scientific_process',
                'scope': deepcopy(source.scope), 'assignment': {
                    'proposed_annotation_ref': 'controlled-received-annotation',
                    'selection': {'version': records.SELECTION_VERSION,
                                  'evidence_axis': {'option_id': 'A1'}}}}
            arm = {'proposed_annotation_ref': 'controlled-received-annotation',
                   'axis': 'A1', 'scope': deepcopy(source.scope)}
            arms = [arm]
            def credit(actual):
                assert actual is source; events.append(('credit', len(arms)))
                return {'credit': {'arms': deepcopy(arms)}}
            stack.enter_context(patch.object(workflow, 'source_credit_view', credit))
            answer = []
            for replay, role, count in ((False, 'scientific_process', 1),
                    (False, 'scientific_process', 2), (True, 'scientific_process', 2),
                    (True, 'improvement', 1)):
                arms[:] = [arm] * count
                try:
                    result = call('validate_child_choice', source, role, selection=selection, original=replay)
                    answer.append(('returned', result))
                except ValueError as error:
                    answer.append(('raised', str(error)))
            assert answer == [('returned', None),
                ('raised', 'axis_assignment_requires_one_received_annotation_subject_scope'),
                ('returned', None), ('raised', 'annotation_root_commissions_evidence_axes')]
            assert events == [('credit', 1), ('credit', 2)]
        elif boundary == 'wait-and-tool-admission':
            literature = original.module('published_evidence_assessment.episode').LiteratureEpisode(workflow.services)
            original.install_entry(workflow, literature)
            workflow.annotation_child_roles = ('literature',)
            assert literature.supports_wait is False
            resolve = workflow.episode_bindings.for_child
            def child(path, role):
                events.append(('resolve', role)); return resolve(path, role)
            stack.enter_context(patch.object(workflow.episode_bindings, 'for_child', child))
            workflow.receipts = None
            answer = [call('permits_common_action', source, 'wait'),
                      call('permits_common_action', source, 'tool')]
            workflow.receipts = SimpleNamespace(known=lambda episode_id: ())
            answer.append(call('permits_common_action', source, 'tool'))
            stack.enter_context(patch.object(type(literature), 'supports_wait', property(lambda self: True)))
            answer.append(call('permits_common_action', source, 'wait'))
            assert answer == [False, False, True, True]
            assert events == [('resolve', 'literature')] * 2
        elif boundary == 'return-sources':
            def received(context, role):
                events.append((context.role, tuple(context.path), role))
                return ['credit', 'supplied-unresolved-qualification']
            workflow.project_credit = SimpleNamespace(child_return_sources=received)
            answer = call('root_child_return_sources', source, 'scientific_process')
            assert answer == ('credit', 'supplied-unresolved-qualification')
            assert events == [('annotation', tuple(source.path), 'scientific_process')]
            if not before:
                assert runtime.Workflow.root_child_return_sources is original.module('annotation_child_policy').root_child_return_sources
        elif boundary == 'catalogue-late-provider':
            entries = [{'name': 'supplied-shared-coordination'}]
            def shared(actual):
                assert actual is source; events.append('shared-catalogue'); return entries
            def late_wait():
                events.append('late-wait-definition'); return {'name': 'supplied-late-wait'}
            def permit(actual, action):
                assert actual is source and action == 'wait'; events.append('permit-wait')
                runtime._wait_estimate_operation = late_wait
                return True
            stack.enter_context(patch.object(runtime, '_wait_estimate_operation', original.forbidden))
            stack.enter_context(patch.object(workflow, 'shared_information_catalog', shared))
            stack.enter_context(patch.object(workflow, 'permits_common_action', permit))
            workflow.receipts = SimpleNamespace(known=lambda episode_id: ())
            answer = call('catalog', source.scope, source=source)
            assert answer is entries and answer[-1] == {'name': 'supplied-late-wait'}
            assert events == ['shared-catalogue', 'permit-wait', 'late-wait-definition']
            workflow.receipts = None
            stack.enter_context(patch.object(workflow, 'shared_information_catalog', lambda actual: None))
            assert call('catalog', source.scope, source=source) is None
        elif boundary == 'execute-composition-bypass':
            marker = LookupError('stop at original composition catalogue port')
            def composition(actual_workflow, actual_source):
                assert actual_workflow is workflow and actual_source is source
                events.append('composition-catalogue'); raise marker
            stack.enter_context(patch.object(runtime, 'composition_catalog', composition))
            workflow.receipts = None
            method = oracle('execute') if before else runtime.Workflow.execute
            first = asyncio.run(method(workflow, source, 'controlled.not-shared', {},
                decision_index=1, operation_key='controlled-operation'))
            assert first['status'] == 'invalid'
            assert first['feedback']['code'] == 'root_tool_requires_shared_coordination_operation'
            try:
                asyncio.run(method(workflow, source, 'controlled.not-shared', {},
                    decision_index=1, operation_key='controlled-operation', _composition_lookup=True))
            except LookupError as error:
                assert error is marker
            else:
                raise AssertionError('composition gate did not reach the original supplied port')
            answer = first
            assert events == ['composition-catalogue']
        elif boundary == 'saved-tool-replay':
            selection = {'kind': 'tool', 'tool': 'controlled.unavailable', 'arguments': {}}
            workflow.journal.save('runtime_actions', {'episode_id': source.episode_id,
                'decision_index': 1, 'action': runtime._json(selection),
                'result': runtime._json({'status': 'unavailable'}), 'credit': None})
            marker = LookupError('stop after original replay admission')
            def permit(actual, action):
                assert actual is source; events.append(('permit', action)); return True
            def catalog(scope, *, source):
                events.append('catalogue'); return []
            def closed(actual, value, index):
                assert actual is source; events.append(('closed-port', index)); raise marker
            stack.enter_context(patch.object(workflow, 'permits_common_action', permit))
            stack.enter_context(patch.object(workflow, 'catalog', catalog))
            stack.enter_context(patch.object(workflow, '_closed_child_commission', closed))
            answer = []
            for index in (1, 2):
                try:
                    call('selected', source, deepcopy(selection), index)
                except (LookupError, ValueError) as error:
                    answer.append((type(error).__name__, str(error), error is marker))
                else:
                    raise AssertionError('unexpected acquisition past the controlled dispatch port')
            assert answer == [('LookupError', str(marker), True),
                ('ValueError', 'action_not_available_to_episode', False)]
            assert events == [('permit', 'tool'), ('closed-port', 1), ('permit', 'tool'), 'catalogue']
        else:
            raise AssertionError(boundary)
        return {'events': deepcopy(events), 'answer': deepcopy(answer)}


def paired_root(directory, boundary):
    before = root_observation(directory / 'original', boundary, before=True)
    after = root_observation(directory / 'current', boundary, before=False)
    assert after == before


def schema_filter_observation(directory, role, *, before):
    runtime = original.module('runtime')
    with original.actual_workflow(directory) as workflow, ExitStack() as stack:
        source, binding = source_for(workflow, role)
        events, owner_calls = [], []
        if binding is not None:
            stack.enter_context(patch.object(binding, 'validate_context', lambda context: None))
        workflow.receipts = None
        genuine_restricted = runtime.restricted_root
        stack.enter_context(patch.object(runtime, 'restricted_root', genuine_restricted))
        def late_restricted(actual_workflow, actual_source):
            assert actual_workflow is workflow and actual_source is source
            events.append('late-root-predicate'); return True
        def permit(actual, action):
            assert actual is source and action == 'wait'
            events.append('wait-admission')
            runtime.restricted_root = late_restricted
            return True
        stack.enter_context(patch.object(workflow, 'permits_common_action', permit))
        stack.enter_context(patch.object(workflow, 'catalog', original.forbidden))
        def reasoning(actual):
            events.append('reasoning')
            return {'type': 'object', 'properties': {'kind': {'type': 'string', 'const': 'reason'}}}
        stack.enter_context(patch.object(workflow, 'reasoning_action_schema', reasoning))
        root_owner = original.module('annotation_child_policy')
        original_filter = root_owner.filter_root_common_actions
        def selected_filter(*args):
            owner_calls.append('actual-root-filter'); return original_filter(*args)
        stack.enter_context(patch.object(root_owner, 'filter_root_common_actions', selected_filter))
        selected = oracle('action_schema') if before else runtime.Workflow.action_schema
        answer = selected(workflow, source)
        kinds = [item['properties']['kind']['const'] for item in answer['properties']['selection']['anyOf']]
        assert 'tool' not in kinds and 'reason' in kinds and 'wait' in kinds
        assert events[:3] == ['wait-admission', 'late-root-predicate', 'reasoning']
        assert owner_calls == ([] if before else ['actual-root-filter'])
        return {'events': events, 'answer': answer}


def paired_schema_filter(directory, role):
    before = schema_filter_observation(directory / 'original', role, before=True)
    after = schema_filter_observation(directory / 'current', role, before=False)
    assert after == before


def cold_owner_entry(directory):
    directory.mkdir(parents=True)
    tree = Path(original.__file__).resolve().parents[5]
    assert tree.is_dir() and (tree / 'gene_annotation_episode').is_dir()
    script = r'''
import importlib, json, pathlib, sys
paths, package, tree = json.loads(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
sys.path[:] = paths
assert package + '.runtime' not in sys.modules
owner = importlib.import_module(package + '.annotation_child_policy')
runtime = importlib.import_module(package + '.runtime')
assert owner._original_runtime is runtime
assert runtime.Workflow.root_child_return_sources is owner.root_child_return_sources
defaults = importlib.import_module(package + '.library.child_role_policy')
assert runtime.Workflow._default_scientific_child_roles is defaults._default_scientific_child_roles
origins = {}
for name, module in tuple(sys.modules.items()):
    if name == 'gene_annotation_episode' or name.startswith('gene_annotation_episode.'):
        path = pathlib.Path(module.__file__).resolve(strict=True)
        assert path.is_relative_to(tree), (name, str(path))
        origins[name] = str(path.relative_to(tree))
print(json.dumps({'origins': origins, 'same_runtime_object': True, 'same_method_objects': True}, sort_keys=True))
'''
    environment = dict(os.environ)
    environment.pop('PYTHONPATH', None)
    environment.pop('PYTHONHOME', None)
    environment.pop('PYTHONOPTIMIZE', None)
    for key in ('TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME'):
        path = directory / key.lower(); path.mkdir()
        environment[key] = str(path)
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    completed = subprocess.run([sys.executable, '-I', '-B', '-c', script,
        json.dumps(sys.path), original.PACKAGE, str(tree)], cwd=directory,
        env=environment, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    value = json.loads(completed.stdout)
    assert value['same_runtime_object'] is True and value['same_method_objects'] is True
    assert original.PACKAGE + '.annotation_child_policy' in value['origins']
    assert original.PACKAGE + '.runtime' in value['origins']
    (directory / 'cold-imports.json').write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
