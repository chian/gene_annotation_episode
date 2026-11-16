"""Own A104 Store/Journal/build/task boundary fixtures; no scientific producer.

The host uses the actual Workflow constructor with a literal scientific-only
factory and original operands. This scoped registered tree does not claim the
complete A104 execution registry. Scientific constructors, libraries, admission,
reference readers, projectors, receipts and Journal are actual implementations.
"""
import asyncio
from copy import deepcopy
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104'
TASKS = ('panel_identity', 'alignment_suitability', 'family_phylogeny', 'target_placement',
    'characterized_clades', 'organismal_history', 'paralog_discrimination', 'robustness', 'synthesis')
def own(name): return importlib.import_module(PREFIX + '.' + name)
def plain(value): return own('communication').plain(value)
def forbidden(*args, **kwargs): raise AssertionError('no external producer/model/native process in scientific head fixture')
def capture(callback):
    try:
        value = callback()
        return {'status': 'returned', 'value': plain(value.as_record() if hasattr(value, 'as_record') else value)}
    except Exception as error:
        return {'status': 'raised', 'type': type(error).__module__ + '.' + type(error).__qualname__,
            'message': str(error), 'code': getattr(error, 'code', None)}
def logical_rows(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: [dict(row) for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '" ORDER BY rowid')]
        for name in names if name.startswith('runtime_')}

def build_case(original, *, task_name=None, standalone=False):
    v = SimpleNamespace(**vars(original)); store = v.store
    scope = plain(v.context.scope)
    v.form = deepcopy(original.form)
    v.form['properties']['status']['description'] = 'The assigned engineering question remains unresolved; no scientific support is asserted.'
    v.invocation = {**deepcopy(original.invocation), 'report_schema': v.form}
    assert task_name is None or task_name in TASKS
    assert tuple(own('a104_investigation').TASKS) == TASKS
    payload = {key: [] for key in store.reasoning_schema()['properties']}
    payload['hypotheses'] = [{'alias': 'original', 'subject_refs': [v.target],
        'predicate': 'biological_role', 'value': {'type': 'enum', 'value': 'unresolved'}, 'context_refs': []}]
    committed = store.commit_reasoning(payload, scope, 'a104-head-original-proposed-annotation')
    assert committed['status'] in ('completed', 'partial')
    proposed = committed['aliases']['original']
    assignment = deepcopy(v.assignment)
    assignment['proposed_annotation_ref'] = proposed
    assignment['evidence_refs'].append(proposed)
    if task_name is not None:
        assignment['context']['a104_task'] = {'name': task_name, 'allowed_tasks': list(TASKS)}
    selector_module = ('scientific_process.task_projector'
        if hasattr(type(v.binding), 'decision_source_type') else 'a104_scientific_process_binding')
    projector = own(selector_module).original_task_projector(assignment)
    key = 'A104:' + (task_name if task_name is not None else projector.as_record()['kind'])
    declaration = {'kind': projector.yield_method, 'cutoff': .25,
        'parameters': {'uncertainty_alpha': .1}, 'credit_definition': projector.as_record()}
    runtime = own('runtime')
    tools = own('tools').ToolRegistry(store)
    acquired = []; outcome = {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
        'result': {'controlled_boundary': 'selected engineering operation'}, 'feedback': None}
    def execute_tool(name, arguments, **operands):
        acquired.append({'name': name, 'arguments': deepcopy(arguments), 'operands': plain(operands)})
        return deepcopy(outcome)
    def factory(services):
        services.tool_catalog = lambda scope: deepcopy(v.catalog)
        services.tool_information_catalog = lambda scope: deepcopy(v.catalog)
        services.execute_tool = execute_tool
        return own('scientific_process.episode').ScientificProcessEpisode(services,
            library=v.library, tool_library=v.tool_library, child_roles=('scientific_process',),
            yield_bindings={key: declaration})
    host = runtime.Workflow(store, tools,
        SimpleNamespace(complete=forbidden, has_session=lambda *args: False), v.directory / 'workflow',
        'a104-private-scientific-head', controller_factory=forbidden, project_credit=projector,
        episode_binding_factories=[factory], episode_record_receipts=True,
        initial_known_record_refs=[v.target, proposed], annotation_child_roles=('scientific_process',),
        root_role='scientific_process' if standalone else 'annotation')
    binding = host.scientific_process_binding
    parent_path = (('annotation', 'original_parent'),)
    parent_id = own('method_loop.identities').EpisodeRef(host.run_id, parent_path).episode_id
    parent = own('episode_bindings').BindingContext(host.run_id, parent_id, 'annotation', parent_path,
        scope, {'proposed_annotation_ref': proposed}, {}, (v.target, proposed))
    host.receipts.bind(parent_id); host.receipts.receive(parent_id, [v.target, proposed], kind='initial')
    prepared = binding.prepare_invocation(parent, 'scientific_process', assignment, scope,
        'a104-original-head-invocation', invocation=v.invocation)
    parent_goal = None if standalone else runtime.EpisodeGoal.root(objective='Original annotation parent',
        result_contract={'role': 'annotation'})
    contract = runtime.TypedReportContract(v.invocation['purpose'], v.form,
        lambda reference: reference in (v.target, proposed))
    build_arguments = {'parent': parent_goal, 'parent_path': () if standalone else parent_path,
        'contract': contract, 'initial': v.invocation['initial_report'],
        'episode_assignment': prepared['assignment'], 'scientific_process': prepared['scientific_process']}
    episode = host.build('scientific_process', 'original_child', v.invocation['objective'], scope,
        **build_arguments)
    task = episode.source
    binding.validate_execution_context(host.binding_context(task))
    assert host.specialist(task) is binding
    assert host.journal.row('runtime_episodes', task.episode_id) is not None
    return SimpleNamespace(workflow=host, binding=binding, task=task, episode=episode,
        store=store, original=v, runtime=runtime, projector=projector, proposed=proposed,
        assignment=assignment, prepared=prepared, declaration=declaration, key=key,
        acquired=acquired, outcome=outcome, standalone=standalone, task_name=task_name,
        build_arguments=build_arguments)

def identity(v):
    context = v.workflow.binding_context(v.task)
    projector = v.binding.credit_projector(context)
    assert type(projector) is type(v.projector) and projector.as_record() == v.projector.as_record()
    assert v.binding.allowed_children(context, None) == ('scientific_process',)
    assert v.binding.permitted_common_actions(context) == ('tool', 'reason', 'child', 'redeliver_report')
    assert v.binding.continuation_task(context) == v.key
    controller = v.binding.yield_controller(context, 0., 'original-a104-controller')
    initial = plain(controller.state().as_record())
    observation = plain(controller.observe('original-zero-credit', {'credit': 0.}).as_record())
    duplicate = v.binding.yield_controller(context, 0., 'original-a104-controller')
    assert plain(duplicate.state().as_record()) == initial
    assert plain(duplicate.observe('original-zero-credit', {'credit': 0.}).as_record()) == observation
    credit = v.workflow.source_credit_view(v.task)
    assert credit['credit'] == 0.
    original_request = json.loads(v.workflow.journal.row('runtime_episodes', v.task.episode_id)['request'])
    assert original_request == plain(v.task.request.as_record())
    return {'projector': projector.as_record(), 'projector_class': type(projector).__module__ + '.' + type(projector).__qualname__,
        'controller_class': type(controller).__module__ + '.' + type(controller).__qualname__,
        'controller_initial': initial, 'controller_observation': observation, 'credit': credit,
        'episode_id': v.task.episode_id, 'path': plain(v.task.path), 'assignment': plain(context.assignment),
        'binding_descriptor': v.binding.as_record(), 'request': original_request}

def executed(v, status, *, saved=False, kind='tool'):
    host, task = v.workflow, v.task
    original_receive = host.receive_outcome; received = []
    def receive(source, selection, result, index):
        received.append((index, deepcopy(result))); return original_receive(source, selection, result, index)
    host.receive_outcome = receive
    async def execute(source, name, arguments, **operands):
        return await v.binding.execute(host.binding_context(source), name, arguments, operands['operation_key'])
    host.execute = execute
    v.outcome['status'] = status
    if status not in ('completed', 'partial'): v.outcome['feedback'] = {'code': 'controlled_' + status}
    selection = {'kind': 'tool', 'tool': 'fixture.inspect', 'arguments': {'record': v.original.target}}
    if kind == 'reason':
        commit = {key: [] for key in v.store.reasoning_schema()['properties']}
        commit['hypotheses'] = [{'alias': 'continued', 'subject_refs': [v.original.target],
            'predicate': 'biological_role', 'value': {'type': 'enum', 'value': 'still_unresolved'}, 'context_refs': []}]
        selection = {'kind': 'reason', 'commit': commit}
    elif kind == 'wait':
        assert saved, 'fresh_wait_is_not_admitted_by_original_scientific_policy'
        selection = {'kind': 'wait', 'condition': {'original_saved_dependency': True}}
    index = 3
    if saved:
        host.journal.save('runtime_actions', {'episode_id': task.episode_id, 'decision_index': index,
            'action': v.runtime._json(selection), 'result': v.runtime._json(v.outcome), 'credit': None})
    first = asyncio.run(task.execute(selection, index))
    before = logical_rows(v.store)
    second = asyncio.run(task.execute(selection, index))
    assert plain(first.as_record()) == plain(second.as_record()) and logical_rows(v.store) == before
    action = dict(host.journal.row('runtime_actions', task.episode_id, index))
    returned = json.loads(action['result'])
    assert json.loads(action['action']) == selection and action['credit'] == 0.
    assert len(received) == 1 and received[0] == (index, returned)
    assert len(v.acquired) == (1 if kind == 'tool' and not saved else 0)
    if kind != 'reason' or saved: assert returned['status'] == status
    assert task.last_outcome == returned
    return {'selection': selection, 'returned': returned, 'credit': action['credit'],
        'controller_input': plain(first.as_record()), 'received': plain(received),
        'acquired': deepcopy(v.acquired), 'replay_rows_unchanged': True}

# Required head_cases.py addition; exact original standalone denial observer.
COMMISSION_ONLY_TASKS = ('panel_identity', 'alignment_suitability', 'robustness')

def original_build_denial(original, *, task_name):
    """Observe the original root credit rejection without supplying a commission."""
    assert task_name in COMMISSION_ONLY_TASKS
    projector_type = getattr(own('a104_credit'), {
        'panel_identity': 'A104PanelIdentityCredit',
        'alignment_suitability': 'A104AlignmentSuitabilityCredit',
        'robustness': 'A104RobustnessCredit'}[task_name])
    try:
        build_case(original, task_name=task_name, standalone=True)
    except Exception as error:
        assert type(error) is own('domain').ContractError
        assert error.args == ('a104_original_commission_scope_required',)
        assert str(error) == 'a104_original_commission_scope_required'
        assert error.detail == {} and not hasattr(error, 'code')
        frames = []
        trace = error.__traceback__
        while trace is not None:
            frames.append(trace.tb_frame)
            trace = trace.tb_next
        def one(code):
            matched = [frame for frame in frames if frame.f_code is code]
            assert len(matched) == 1
            return matched[0].f_locals
        fixture = one(build_case.__code__)
        services = one(own('episode_services').WorkflowServices.scientific_credit.__code__)
        projection = one(projector_type.read_details.__code__)
        context = services['context']
        assert len(context.path) == 1 and context.role == 'scientific_process'
        assert services['local'] is False and 'assignment' not in services['arguments']
        assert projection['assignment'] is None and type(projection['self']) is projector_type
        assert type(services['projector']) is projector_type
        assert fixture['standalone'] is True and fixture['task_name'] == task_name
        assert fixture['acquired'] == []
        # The request row was tentatively saved inside the original build
        # transaction. Its failed initial-credit projection rolls that row
        # back; this is not a returned task or a saved closed carrier.
        host = fixture['host']
        assert host.journal.row('runtime_episodes', context.episode_id) is None
        assert host.journal.row('runtime_actions', context.episode_id, 0) is None
        return {'status': 'raised', 'task_name': task_name, 'standalone': True,
            'error': {'type': type(error).__module__ + '.' + type(error).__qualname__,
                'message': str(error), 'args': plain(error.args), 'detail': plain(error.detail),
                'code_attribute_present': False},
            'boundary': 'Workflow.build.initial_credit.scientific_credit.read_details',
            'projector_class': projector_type.__module__ + '.' + projector_type.__qualname__,
            'context': context.as_record(), 'prepared_invocation': plain(fixture['prepared']),
            'root_path_length': len(context.path), 'services_supplied_assignment': False,
            'projector_assignment': None, 'acquired_operations': [],
            'runtime_episode_row_after_rollback': None, 'runtime_action_zero': None,
            'returned_task': False, 'closed_carrier': False}
    raise AssertionError('original_standalone_commission_denial_was_not_preserved')
