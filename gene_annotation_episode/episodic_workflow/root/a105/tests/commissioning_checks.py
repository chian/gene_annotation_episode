"""Original/current commissioning gates, with real workflow/source/journal inputs."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from . import implicit_parent_checks as original
from . import policy_assembly_checks as policy


class BoundaryStop(Exception):
    pass


def paired(directory, scenario):
    runtime = original.module('runtime')
    records = original.module('scientific_process_records')
    results = []
    for old in (True, False):
        with original.actual_workflow(directory / str(old)) as workflow:
            source = original.root(workflow).source
            events = []
            def call(name, *args, **kwargs):
                method = original.original_function('Workflow', name) if old else getattr(runtime.Workflow, name)
                result = method(workflow, *args, **kwargs)
                return asyncio.run(result) if asyncio.iscoroutine(result) else result
            def restricted(actual_workflow, actual):
                assert actual_workflow is workflow and actual is source
                events.append('root_classifier')
                return True
            with patch.object(runtime, 'restricted_root', restricted):
                if scenario == 'wait':
                    workflow.annotation_child_roles = ('literature',)
                    workflow.episode_bindings = SimpleNamespace(roles=('literature',),
                        for_child=lambda path, role: events.append('actual_child_wait_declaration') or
                            SimpleNamespace(supports_wait=False))
                    workflow.specialist = original.forbidden
                    value = call('permits_common_action', source, 'wait')
                    assert value is False and events == ['actual_child_wait_declaration']
                elif scenario == 'receipt':
                    workflow.specialist = original.forbidden
                    workflow.receipts = None
                    absent = call('permits_common_action', source, 'tool')
                    workflow.receipts = object()
                    present = call('permits_common_action', source, 'tool')
                    value = (absent, present)
                    assert value == (False, True) and events == ['root_classifier', 'root_classifier']
                elif scenario == 'declarations':
                    workflow.scientific_process_binding = None
                    workflow.job_episodes = SimpleNamespace(roles=('declared_job',))
                    workflow.episode_bindings = SimpleNamespace(entry_roles=('declared_private',), roles=())
                    first = call('_default_scientific_child_roles')
                    workflow.annotation_child_roles = ('declared_private',)
                    root = call('declared_child_roles', 'annotation', path=source.path)
                    improvement = call('declared_child_roles', 'improvement', path=(('improvement', 'declared'),))
                    workflow.scientific_process_binding = object()
                    last = call('_default_scientific_child_roles')
                    value = first, root, improvement, last
                    assert value == (('improvement', 'declared_job', 'declared_private'),
                                     ('declared_private',), ('improvement', 'declared_job', 'declared_private'),
                                     ('declared_job', 'declared_private'))
                elif scenario == 'declaration_none':
                    workflow.episode_bindings = SimpleNamespace(roles=())
                    workflow._default_scientific_child_roles = original.forbidden
                    values = iter((('original_declaration',), None))
                    def changed_declaration(actual):
                        assert actual is workflow
                        events.append('declaration_read')
                        return next(values)
                    # The authentic condition and return read this property
                    # twice. None on the second read is a handled result.
                    with patch.object(type(workflow), 'annotation_child_roles',
                                      property(changed_declaration), create=True):
                        value = call('declared_child_roles', 'annotation', path=source.path)
                    assert value is None and events == ['declaration_read', 'declaration_read']
                elif scenario == 'late_filter':
                    workflow.declared_child_roles = lambda *args, **kwargs: events.append('declared') or ('improvement', 'scientific_process')
                    def allowed(context, capabilities):
                        events.append('allowed')
                        workflow.project_credit.task_credit = True
                        return ('improvement', 'scientific_process')
                    workflow.specialist = lambda actual: events.append('specialist') or SimpleNamespace(allowed_children=allowed)
                    with patch.object(workflow.services, 'capabilities', lambda: events.append('capabilities') or {}):
                        value = call('available_child_roles', source)
                    assert value == ('scientific_process',)
                    assert events == ['declared', 'specialist', 'capabilities', 'allowed']
                elif scenario in ('fresh_arm', 'replay_arm', 'wrong_arm'):
                    workflow.project_credit.task_credit = True
                    workflow.annotation_child_roles = None
                    selection = {'kind': 'episode_child', 'role': 'scientific_process', 'scope': deepcopy(source.scope),
                        'assignment': {'proposed_annotation_ref': 'controlled_annotation', 'selection': {
                            'version': records.SELECTION_VERSION, 'evidence_axis': {'option_id': 'controlled_axis'}}}}
                    arm = {'proposed_annotation_ref': 'controlled_annotation', 'axis': 'controlled_axis', 'scope': deepcopy(source.scope)}
                    def credit(actual):
                        events.append('credit_arms')
                        return {'credit': {'arms': [] if scenario == 'wrong_arm' else [arm]}}
                    workflow.source_credit_view = original.forbidden if scenario == 'replay_arm' else credit
                    try:
                        value = call('validate_child_choice', source, 'scientific_process', selection=selection,
                                     original=scenario == 'replay_arm')
                    except ValueError as error:
                        assert scenario == 'wrong_arm'
                        value = original.error_record(error)
                        assert str(error) == 'axis_assignment_requires_one_received_annotation_subject_scope'
                    else:
                        assert scenario != 'wrong_arm' and value is None
                    assert events == ([] if scenario == 'replay_arm' else ['credit_arms'])
                elif scenario in ('catalog_none', 'catalog_wait'):
                    workflow.receipts = None if scenario == 'catalog_none' else object()
                    workflow.shared_information_catalog = lambda actual: events.append('shared_catalog') or (
                        None if scenario == 'catalog_none' else [{'name': 'controlled_information'}])
                    workflow.permits_common_action = lambda actual, action: events.append(('permission', action)) or True
                    with patch.object(runtime, '_wait_estimate_operation',
                                      lambda: events.append('wait_operation') or {'name': 'controlled_wait'}):
                        value = call('catalog', source.scope, source)
                    assert value == (None if scenario == 'catalog_none' else [
                        {'name': 'controlled_information'}, {'name': 'controlled_wait'}])
                elif scenario in ('execute_rejection', 'execute_lookup'):
                    workflow.receipts = None
                    def pending(actual, index):
                        events.append('lookup_port')
                        raise BoundaryStop('composition_lookup')
                    workflow.pending_contract_information = pending
                    try:
                        value = call('execute', source, runtime.CONTRACT_INFORMATION_OPERATIONS[0], {},
                                     decision_index=3, operation_key='controlled_operation',
                                     _composition_lookup=scenario == 'execute_lookup')
                    except BoundaryStop as error:
                        assert scenario == 'execute_lookup'; value = str(error)
                    else:
                        assert scenario == 'execute_rejection'
                        assert value == {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [],
                            'result': None, 'feedback': {'code': 'root_tool_requires_shared_coordination_operation'}}
                    assert events == (['root_classifier', 'lookup_port'] if scenario == 'execute_lookup' else ['root_classifier'])
                elif scenario in ('selected_fresh', 'selected_replay'):
                    selection = {'kind': 'tool', 'tool': 'unavailable_tool', 'arguments': {}}
                    workflow.permits_common_action = lambda *args: True
                    def catalog(*args, **kwargs):
                        events.append('fresh_catalog')
                        return []
                    workflow.catalog = original.forbidden if scenario == 'selected_replay' else catalog
                    def closed(*args):
                        events.append('after_original_root_guard')
                        raise BoundaryStop('saved_guard_passed')
                    workflow._closed_child_commission = closed
                    if scenario == 'selected_replay':
                        workflow.journal.save('runtime_actions', {'episode_id': source.episode_id,
                            'decision_index': 3, 'action': json.dumps(selection),
                            'result': json.dumps({'status': 'completed'}), 'credit': None})
                    try:
                        call('selected', source, deepcopy(selection), 3)
                    except ValueError as error:
                        assert scenario == 'selected_fresh'
                        value = original.error_record(error)
                        assert str(error) == 'action_not_available_to_episode'
                    except BoundaryStop as error:
                        assert scenario == 'selected_replay'; value = str(error)
                    else:
                        raise AssertionError('original guard control did not stop before acquisition')
                    assert events == (['root_classifier', 'fresh_catalog'] if scenario == 'selected_fresh' else
                                      ['root_classifier', 'after_original_root_guard'])
                elif scenario == 'return_form':
                    workflow.receipts = None
                    workflow.project_credit.child_return_sources = lambda context, role: events.append('return_sources') or ('credit',)
                    workflow.project_credit.child_return_form = lambda context, role: events.append('return_form') or deepcopy(original.SCHEMA)
                    declared = call('root_child_return_sources', source, 'scientific_process')
                    form = json.loads(call('child_form_input', source, {}, 'scientific_process'))
                    initial = call('child_initial_report_input', source, {}, 'scientific_process')
                    before = list(events)
                    supplied = call('child_form_input', source, {'schema_json': 'supplied'}, 'scientific_process')
                    supplied_initial = call('child_initial_report_input', source, {'initial_report_json': 'original'}, 'scientific_process')
                    assert events == before
                    value = declared, form, initial, supplied, supplied_initial
                    assert value == (('credit',), original.SCHEMA, '{}', 'supplied', 'original')
                else:
                    raise AssertionError(scenario)
            results.append((value, events))
    assert results[0] == results[1]
    return results[1]


def schema_filter(directory):
    # Only the extracted root option-filter interface is newly exercised here;
    # complete schema/current-global comparisons remain the accepted policy30.
    for home in ('annotation', 'improvement', 'custom'):
        policy.paired_schema(directory / home, home)


def cold_entry(directory, name):
    tree = Path(os.environ['PYTHONPATH'].split(os.pathsep)[0]).resolve()
    assert (tree / 'gene_annotation_episode').is_dir()
    directory.mkdir(parents=True, exist_ok=True)
    package = original.PACKAGE
    code = '''import importlib, json, pathlib, sys
tree = pathlib.Path(sys.argv[1]).resolve()
package, name = sys.argv[2:]
owner = importlib.import_module(package + '.' + name)
runtime = importlib.import_module(package + '.runtime')
assert owner._original_runtime is runtime
assert callable(owner.root_child_return_sources if name == 'commissioning_policy' else owner.available_child_roles)
imports = {}
for key, value in tuple(sys.modules.items()):
    if key == 'gene_annotation_episode' or key.startswith('gene_annotation_episode.') or key == 'method_loop' or key.startswith('method_loop.'):
        filename = getattr(value, '__file__', None)
        if filename:
            path = pathlib.Path(filename).resolve()
            assert path.is_relative_to(tree), (key, str(path))
            imports[key] = str(path.relative_to(tree))
print(json.dumps(imports, sort_keys=True))
'''
    process = subprocess.run([sys.executable, '-B', '-c', code, str(tree), package, name],
        cwd=directory, env=dict(os.environ), capture_output=True, text=True)
    (directory / 'cold.stdout').write_text(process.stdout)
    (directory / 'cold.stderr').write_text(process.stderr)
    assert process.returncode == 0, process.stderr
    imports = json.loads(process.stdout)
    assert package + '.' + name in imports and package + '.runtime' in imports
    (directory / 'cold_imports.json').write_text(json.dumps(imports, indent=2, sort_keys=True) + '\n')
