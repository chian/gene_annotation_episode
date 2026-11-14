"""Shared original A106 policy oracles and explicit boundary ports.

The real parent Store/Workflow/constructors are used for schema comparisons.
Other controls invoke actual Workflow entry methods with named engineering
ports and compare original callback order, whole returns and original errors.
They do not acquire a child, provider, native task or scientific result.
"""
import ast
import asyncio
from copy import deepcopy
from types import SimpleNamespace, MethodType

from .test_implicit_annotation_parent import (
    actual_workflow, module, root, original_function, original_member, failure,
)

class PolicyPortError(RuntimeError):
    pass

def capture(function, *args, **kwargs):
    try:
        value = function(*args, **kwargs)
        if asyncio.iscoroutine(value):
            value = asyncio.run(value)
        return {'return': deepcopy(value)}
    except Exception as error:
        return {'error': failure(error)}

def same(traces):
    assert len(traces) == 2 and traces[0] == traces[1]
    return traces[0]

def original_or_current(name, original):
    return original_function('Workflow', name) if original else getattr(module('runtime').Workflow, name)

def source_port(path=(('annotation', 'root'),)):
    return SimpleNamespace(path=path, episode_id='boundary_episode', scope={'subject_refs': ['boundary_subject']},
        _delivery_resolution_ref=None)

def assert_schema_boundary(tmp_path, monkeypatch, parent, mode):
    traces = []
    rt = module('runtime')
    original_object, original_array, original_json = rt._object, rt._array, rt._json
    for old in (True, False):
        with monkeypatch.context() as patch:
            def configured(*args, **kwargs):
                receipts = {'episode_record_receipts': True, 'initial_known_record_refs': []} if parent == 'annotation' else {}
                return rt.Workflow(*args, root_role=parent, **receipts, **kwargs)
            with actual_workflow(tmp_path / str(old), cls=configured) as workflow:
                source = (root(workflow) if parent == 'annotation' else workflow.build(
                    'improvement', 'root', 'Preserve original policy meaning', workflow.store.validate_scope())).source
                expected_type = module('episode').AnnotationTask if parent == 'annotation' else module('annotation_improvement.episode').ImprovementTask
                assert type(source) is expected_type
                if parent == 'annotation': assert workflow.receipts is not None
                events = []
                def object_schema(value):
                    events.append(('object', tuple(value)))
                    if mode == 'initial_failure' and len(events) == 1:
                        raise PolicyPortError('original_first_form_failure')
                    return original_object(value)
                def array_schema(value):
                    events.append(('array', tuple(value)))
                    return original_array(value)
                def json_schema(value):
                    events.append(('json', tuple(value)))
                    return original_json(value)
                def late_json(value):
                    events.append(('late_json', tuple(value)))
                    raise PolicyPortError('original_late_form_failure')
                def catalog(scope, *, source):
                    events.append(('catalog', rt._plain(scope)))
                    if mode == 'late_global_failure':
                        patch.setattr(rt, '_json', late_json)
                    return []
                class Jobs:
                    roles = ()
                    def commission_schemas(self, child):
                        events.append(('commission_schemas', child['properties']['kind']['const']))
                        raise PolicyPortError('original_job_schema_failure')
                patch.setattr(rt, '_object', object_schema)
                patch.setattr(rt, '_array', array_schema)
                patch.setattr(rt, '_json', json_schema)
                workflow.catalog = catalog
                workflow.reasoning_action_schema = lambda value: events.append(('reason', value.path)) or {'type': 'object', 'properties': {'kind': {'const': 'reason'}}}
                if mode == 'job_callback_failure': workflow.job_episodes = Jobs()
                # Compare the actual original nested policy functions too;
                # the original action_schema does not borrow new helper logic.
                for name in ('permits_common_action', 'available_child_roles', '_default_scientific_child_roles'):
                    setattr(workflow, name, MethodType(original_or_current(name, old), workflow))
                result = capture(original_or_current('action_schema', old), workflow, source)
                traces.append((events, result))
    events, result = same(traces)
    assert events[0][0] == 'object'
    if mode == 'normal':
        assert 'return' in result
        selection = result['return']['properties']['selection']['anyOf']
        assert any(row['properties']['kind']['const'] == 'child' for row in selection)
        assert any(event[0] == 'catalog' for event in events)
    else:
        expected = {'initial_failure': 'original_first_form_failure',
            'late_global_failure': 'original_late_form_failure', 'job_callback_failure': 'original_job_schema_failure'}[mode]
        assert result['error']['message'] == expected
        if mode == 'initial_failure': assert len(events) == 1
        if mode == 'late_global_failure':
            assert next(i for i, e in enumerate(events) if e[0] == 'catalog') < next(i for i, e in enumerate(events) if e[0] == 'late_json')


def assert_permission_boundary(mode):
    rt = module('runtime'); traces = []
    for old in (True, False):
        events = []; source = source_port()
        class Child:
            @property
            def supports_wait(self):
                events.append('supports_wait')
                if mode == 'wait_callback_failure': raise PolicyPortError('wait_capability_failure')
                return False
        class Registry:
            @property
            def roles(self): events.append('roles'); return ('literature',)
            def for_child(self, path, role): events.append(('for_child', path, role)); return Child()
        workflow = SimpleNamespace(annotation_child_roles=('literature',), episode_bindings=Registry(),
            root_action_boundary=rt.ROOT_BOUNDARY_VERSION,
            receipts=object() if mode == 'tool_receipts' else None)
        workflow.specialist = lambda value: events.append('specialist') or None
        workflow.is_job_source = lambda value: events.append('is_job_source') or False
        action = 'wait' if mode in ('wait_blocked', 'wait_callback_failure') else 'tool' if mode.startswith('tool_') else 'reason'
        if mode == 'ordinary_fallback': workflow.root_action_boundary = None
        result = capture(original_or_current('permits_common_action', old), workflow, source, action)
        traces.append((events, result))
    events, result = same(traces)
    if mode == 'wait_callback_failure': assert result['error']['message'] == 'wait_capability_failure'
    else: assert result['return'] is (mode in ('tool_receipts', 'ordinary_fallback'))
    if mode.startswith('tool_'): assert events == []
    if mode == 'wait_blocked': assert events == ['roles', ('for_child', source.path, 'literature'), 'supports_wait']


def assert_roles_boundary(mode):
    traces = []
    for old in (True, False):
        events = []; source = source_port() if mode != 'nested_unchanged' else source_port((('annotation', 'root'), ('improvement', 'child')))
        class Credit:
            @property
            def task_credit(self):
                events.append('task_credit')
                if mode == 'credit_callback_failure': raise PolicyPortError('original_credit_flag_failure')
                return True
        allowed = ('scientific_process', 'literature', 'scientific_process')
        declared = allowed if mode != 'outside_declared' else ('scientific_process',)
        class Specialist:
            def allowed_children(self, context, capabilities): events.append('allowed'); return allowed
        workflow = SimpleNamespace(project_credit=Credit(), services=SimpleNamespace(capabilities=lambda: events.append('capabilities') or {}))
        workflow.declared_child_roles = lambda *args, **kwargs: events.append('declared') or declared
        workflow.specialist = lambda value: events.append('specialist') or Specialist()
        workflow.binding_context = lambda value: events.append('context') or 'supplied_context'
        result = capture(original_or_current('available_child_roles', old), workflow, source)
        traces.append((events, result))
    events, result = same(traces)
    assert events[:5] == ['declared', 'specialist', 'context', 'capabilities', 'allowed']
    if mode == 'outside_declared':
        assert result['error']['message'] == 'available_child_outside_declared_type_edges'
        assert 'task_credit' not in events
    elif mode == 'credit_callback_failure': assert result['error']['message'] == 'original_credit_flag_failure'
    else:
        assert type(result['return']) is tuple
        assert result['return'] == (('scientific_process', 'scientific_process') if mode == 'root_filter' else allowed)
        if mode == 'nested_unchanged': assert 'task_credit' not in events


def assert_default_roles_boundary(mode):
    traces = []
    for old in (True, False):
        events = []
        class Jobs:
            @property
            def roles(self):
                events.append('job_roles')
                if mode == 'job_failure': raise PolicyPortError('original_job_roles_failure')
                return ('launch', 'monitor')
        class Registry:
            @property
            def entry_roles(self): events.append('entry_roles'); return ('scientific_process', 'literature')
        workflow = SimpleNamespace(scientific_process_binding=object() if mode == 'bound_scientific' else None,
            job_episodes=None if mode == 'no_jobs' else Jobs(), episode_bindings=Registry())
        result = capture(original_or_current('_default_scientific_child_roles', old), workflow)
        traces.append((events, result))
    events, result = same(traces)
    if mode == 'job_failure':
        assert events == ['job_roles'] and result['error']['message'] == 'original_job_roles_failure'
    else:
        prefix = () if mode == 'bound_scientific' else ('improvement',)
        jobs = () if mode == 'no_jobs' else ('launch', 'monitor')
        assert result['return'] == (*prefix, *jobs, 'scientific_process', 'literature')
    method = module('runtime').Workflow._default_scientific_child_roles
    assert method is module('library.unbound_child_action_options')._default_scientific_child_roles
    assert method.__globals__ is vars(module('runtime'))
    assert method.__qualname__ == 'Workflow._default_scientific_child_roles'
    assert method.__module__ == module('runtime').__name__


def assert_choice_boundary(mode):
    rt = module('runtime'); traces = []
    for old in (True, False):
        events = []; source = source_port()
        class Credit:
            @property
            def task_credit(self): events.append('task_credit'); return True
        scope = {'subject_refs': ['boundary_subject']}
        selection = {'kind': 'episode_child', 'role': 'scientific_process', 'scope': deepcopy(scope),
            'assignment': {'selection': {'version': 'scientific_process_selection_v3', 'evidence_axis': {'option_id': 'A106'}},
                'proposed_annotation_ref': 'annotation_boundary'}}
        def validate_scope(value, parent):
            events.append('validate_scope')
            if mode == 'scope_failure': raise PolicyPortError('original_scope_callback_failure')
            return deepcopy(value)
        def credit_view(value):
            events.append('credit_view')
            arm = {'axis': 'A106', 'proposed_annotation_ref': 'annotation_boundary', 'scope': deepcopy(scope)}
            return {'credit': {'arms': [] if mode == 'no_arm' else [arm]}}
        workflow = SimpleNamespace(project_credit=Credit(), annotation_child_roles=None,
            store=SimpleNamespace(validate_scope=validate_scope), source_credit_view=credit_view)
        role = 'literature' if mode == 'wrong_role' else 'scientific_process'
        if mode == 'malformed_selection': selection['assignment']['selection'] = {}
        result = capture(original_or_current('validate_child_choice', old), workflow, source, role,
            selection=selection, original=mode == 'saved_original')
        traces.append((events, result))
    events, result = same(traces)
    expected = {'wrong_role': 'annotation_root_commissions_evidence_axes',
        'malformed_selection': 'scientific_process_selection_invalid',
        'scope_failure': 'original_scope_callback_failure',
        'no_arm': 'axis_assignment_requires_one_received_annotation_subject_scope'}
    if mode in expected: assert result['error']['message'] == expected[mode]
    else: assert result == {'return': None}
    if mode in ('wrong_role', 'malformed_selection', 'saved_original'): assert events == ['task_credit']
    elif mode == 'scope_failure': assert events == ['task_credit', 'validate_scope']
    else: assert events == ['task_credit', 'validate_scope', 'credit_view']


def assert_selected_replay_boundary(mode):
    rt = module('runtime'); traces = []
    for old in (True, False):
        events = []; source = source_port(); selection = {'kind': 'tool', 'tool': 'supplied.operation', 'arguments': {}}
        def journal(*args):
            events.append(('journal', args))
            if mode == 'journal_failure': raise PolicyPortError('original_journal_failure')
            return {'result': '{}', 'action': rt._json(selection)} if mode == 'saved_replay' else None
        def catalog(scope, *, source):
            events.append('catalog')
            return [] if mode == 'absent_tool' else [{'name': 'supplied.operation'}]
        marker = {'boundary': 'after_original_tool_admission'}
        workflow = SimpleNamespace(root_action_boundary=rt.ROOT_BOUNDARY_VERSION,
            permits_common_action=lambda *args: events.append('permission') or True,
            journal=SimpleNamespace(row=journal), catalog=catalog,
            _closed_child_commission=lambda *args: events.append('closed_commission') or marker)
        result = capture(original_or_current('selected', old), workflow, source, selection, 7)
        traces.append((events, result))
    events, result = same(traces)
    assert events[0] == 'permission' and events[1][0] == 'journal'
    if mode == 'absent_tool': assert result['error']['message'] == 'action_not_available_to_episode' and events[-1] == 'catalog'
    elif mode == 'journal_failure': assert result['error']['message'] == 'original_journal_failure' and len(events) == 2
    else:
        assert result == {'return': marker} and events[-1] == 'closed_commission'
        assert ('catalog' in events) is (mode != 'saved_replay')


def assert_catalog_boundary(mode):
    rt = module('runtime'); traces = []
    for old in (True, False):
        events = []; source = source_port()
        def supplied_catalog(value):
            events.append('shared_catalog')
            if mode == 'callback_failure': raise PolicyPortError('original_catalog_failure')
            return None if mode == 'opaque_none' else [{'name': 'supplied.shared'}]
        workflow = SimpleNamespace(root_action_boundary=rt.ROOT_BOUNDARY_VERSION,
            shared_information_catalog=supplied_catalog,
            receipts=None if mode == 'opaque_none' else object(),
            permits_common_action=lambda *args: events.append('wait_permission') or mode == 'wait_entry')
        result = capture(original_or_current('catalog', old), workflow, source.scope, source=source)
        traces.append((events, result))
    events, result = same(traces)
    if mode == 'callback_failure': assert result['error']['message'] == 'original_catalog_failure' and events == ['shared_catalog']
    elif mode == 'opaque_none': assert result == {'return': None} and events == ['shared_catalog']
    else:
        assert events == ['shared_catalog', 'wait_permission']
        assert len(result['return']) == (2 if mode == 'wait_entry' else 1)
        if mode == 'wait_entry': assert result['return'][1]['name'] == 'episode.estimate_wait'


def assert_execute_boundary(mode):
    rt = module('runtime'); traces = []
    for old in (True, False):
        events = []; source = source_port()
        shared_name = module('shared_information').TOOLS[0]
        name = 'unavailable.operation' if mode == 'unlisted' else 'episode.estimate_wait' if mode == 'wait_failure' else shared_name
        outcome = {'status': mode if mode in ('failed', 'unavailable') else 'completed',
            'record_refs': [], 'changed_record_refs': [], 'result': {'original_operation_key': 'policy_operation'},
            'feedback': {'code': 'supplied_service_outcome'}}
        class Repository:
            def execute(self, context, operation, arguments, *, known_record_refs, operation_key):
                events.append(('service_execute', operation, arguments, known_record_refs, operation_key))
                return deepcopy(outcome)
        def permits(value, action):
            events.append(('permission', action))
            if mode == 'wait_failure': raise PolicyPortError('original_wait_permission_failure')
            return True
        def repository():
            events.append('repository')
            if mode == 'repository_failure': raise ValueError('original_repository_failure')
            return Repository()
        workflow = SimpleNamespace(root_action_boundary=rt.ROOT_BOUNDARY_VERSION,
            receipts=None if mode == 'no_receipts' else SimpleNamespace(known=lambda episode: events.append(('known', episode)) or ('supplied_receipt',)),
            permits_common_action=permits, specialist=lambda value: events.append('specialist') or None,
            scientific_process_binding=None, knowledge=SimpleNamespace(operation_catalog=lambda: []),
            launch_instructions=SimpleNamespace(operation_catalog=lambda: []), shared_information_repository=repository,
            binding_context=lambda value: events.append('context') or 'supplied_context')
        result = capture(original_or_current('execute', old), workflow, source, name, {'original': True},
            decision_index=7, operation_key='policy_operation')
        traces.append((events, result))
    events, result = same(traces)
    if mode in ('no_receipts', 'unlisted'):
        assert result['return'] == {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'code': 'root_tool_requires_shared_coordination_operation'}}
        assert events == []
    elif mode == 'wait_failure': assert result['error']['message'] == 'original_wait_permission_failure' and events == [('permission', 'wait')]
    elif mode == 'repository_failure':
        assert result['return']['status'] == 'invalid' and result['return']['feedback'] == {'code': 'original_repository_failure'}
    else:
        assert result['return'] == outcome
        assert events[-1] == ('service_execute', name, {'original': True}, ('supplied_receipt',), 'policy_operation')


def assert_scientific_snapshot_boundary(mode):
    method = original_member('Workflow', 'facts')
    guarded, = [n for n in ast.walk(method) if isinstance(n, ast.If) and ast.unparse(n.test) == 'specialist is self.scientific_process_binding']
    assert len(guarded.body) == 1
    fn = ast.parse('def original_snapshot(self, source, context, snapshot, facts):\n    pass').body[0]
    fn.body = deepcopy(guarded.body)
    namespace = {}; exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), '<authenticated-original-scientific-snapshot>', 'exec'), namespace)
    traces = []
    for callback in (namespace['original_snapshot'], module('scientific_process.completion_snapshot').completion_snapshot):
        events = []; source = source_port(); facts = {'credit': 1.25, 'episode_yield': None}
        class Snapshot(dict):
            @property
            def update(self):
                events.append('update_lookup')
                def apply(**values): events.append('update_apply'); return super(Snapshot, self).update(values)
                return apply
        def journal(*args):
            events.append(('journal', args))
            return None if mode == 'missing_initial' else {'initial_credit': 0.5}
        def controller(value):
            events.append('controller')
            if mode == 'controller_failure': raise PolicyPortError('original_controller_failure')
            return {'credit_kind': 'supplied_engineering_port'}
        def parent(context):
            events.append(('parent', context))
            if mode == 'parent_failure': raise PolicyPortError('original_parent_invocation_failure')
            return None
        workflow = SimpleNamespace(journal=SimpleNamespace(row=journal), source_controller_credit=controller,
            services=SimpleNamespace(scientific_parent_invocation=parent))
        snapshot = Snapshot({'retained': ['original']})
        result = capture(callback, workflow, source, 'supplied_context', snapshot, facts)
        traces.append((events, result, dict(snapshot)))
    events, result, snapshot = same(traces)
    assert events[0] == 'update_lookup' and events[1] == ('journal', ('runtime_episodes', source.episode_id))
    if mode == 'normal':
        assert result == {'return': None} and events[-1] == 'update_apply'
        assert snapshot == {'retained': ['original'], 'initial_credit': 0.5, 'credit': 1.25,
            'controller_credit': {'credit_kind': 'supplied_engineering_port'}, 'episode_yield': None, 'parent_invocation_ref': None}
    else:
        assert snapshot == {'retained': ['original']} and 'update_apply' not in events
        if mode == 'missing_initial': assert result['error']['type'] == 'builtins.TypeError' and len(events) == 2
        else: assert result['error']['message'] == 'original_' + ('controller' if mode == 'controller_failure' else 'parent_invocation') + '_failure'


def assert_late_scientific_report_consumer(tmp_path, mode):
    """All three real facts entries, with a late rebound identity and actual DB."""
    rt = module('runtime')
    parent = 'improvement' if mode == 'improvement_report' else 'annotation'
    def configured(*args, **kwargs): return rt.Workflow(*args, root_role=parent, **kwargs)
    with actual_workflow(tmp_path, cls=configured) as workflow:
        source = (root(workflow) if parent == 'annotation' else workflow.build(
            'improvement', 'root', 'Preserve original completion custody', workflow.store.validate_scope())).source
        events, snapshots = [], []
        def report(context, snapshot):
            events.append('specialist.facts'); snapshots.append(deepcopy(snapshot)); return {}
        specialist = SimpleNamespace(facts=report)
        workflow.specialist = lambda value: specialist
        def credit(value):
            events.append('credit'); workflow.scientific_process_binding = specialist
            return {'credit': 1.25}
        workflow.source_credit_view = credit
        workflow.source_controller_credit = lambda value: events.append('controller_credit') or None
        workflow.pending_handles = lambda value: []
        workflow.services.scientific_parent_invocation = lambda context: events.append('parent_invocation') or None
        original_row = workflow.journal.row
        def row(table, *args):
            if table == 'runtime_episodes': events.append('episode_row')
            return original_row(table, *args)
        workflow.journal.row = row
        current = rt.Workflow.facts if mode == 'runtime_fallback' else module(
            'report' if mode == 'annotation_report' else 'annotation_improvement.report').facts
        assert current.__globals__ is vars(rt)
        if mode == 'runtime_fallback': assert not module('episode').is_annotation_parent(workflow, source)
        results = []
        for callback in (original_function('Workflow', 'facts'), current):
            events.clear(); snapshots.clear(); workflow.scientific_process_binding = None
            result = callback(workflow, source, completion_record=None)
            assert events == ['credit', 'episode_row', 'controller_credit', 'parent_invocation', 'specialist.facts']
            assert len(snapshots) == 1 and snapshots[0]['credit'] == 1.25
            assert snapshots[0]['initial_credit'] == original_row('runtime_episodes', source.episode_id)['initial_credit']
            assert snapshots[0]['controller_credit'] is None and snapshots[0]['parent_invocation_ref'] is None
            results.append((deepcopy(result), list(events), deepcopy(snapshots)))
        same(results)
