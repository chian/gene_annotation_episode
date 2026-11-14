"""Controlled Terminal boundaries; no command, provider, scheduler or transport dispatch.

The actual private constructors, task MRO, state, yield and catalogue execute.
Task next() uses a controlled call/apply boundary to isolate its original input
and saved-input behavior; this does not claim provider or full-workflow replay.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from importlib import import_module
import json
import sqlite3
from types import SimpleNamespace

from gene_annotation_episode.episodic_workflow.root.method_loop import EpisodeGoal, EpisodeRequest
from gene_annotation_episode.episodic_workflow.root.task_values import Record
from terminal_original_checks import assignment
from terminal_original_next import OriginalTerminalNext


ROOT = 'gene_annotation_episode.episodic_workflow.root'
HOMES = (
    'local_job_execution', 'hpc_job_execution',
    'legacy_annotation/local_job_execution', 'legacy_annotation/hpc_job_execution',
    'scientific_process/local_job_execution', 'scientific_process/hpc_job_execution',
)


def configuration(workspace):
    return {'resources': {
        'local': {'kind': 'local', 'workspace': str(workspace),
                  'policy': {'memory_bytes': 128 * 1024 ** 2, 'scratch_bytes': 8 * 1024 ** 2}},
        'hpc': {'kind': 'pbs_ssh', 'workspace': str(workspace),
                'ssh_argv': ['never-dispatch-this-test-transport'],
                'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test',
                'scheduler': {'kind': 'pbs', 'required_resources': []}}},
        'initial_information': {}}


def private(home, tmp_path):
    module = import_module(ROOT + '.' + home.replace('/', '.') + '.episode')
    kind = 'local' if home.endswith('/local_job_execution') or home == 'local_job_execution' else 'hpc'
    cls = module.LocalEpisodeBinding if kind == 'local' else module.HPCEpisodeBinding
    value = assignment(tmp_path)
    value['resource_kind'] = kind
    value['constraints'] = {}
    binding = cls(None, directory=tmp_path / 'run', **configuration(tmp_path))
    parent_role = ('improvement' if home.startswith('legacy_annotation/') else
                   'scientific_process' if home.startswith('scientific_process/') else 'annotation')
    role = 'launch_' + kind
    context = SimpleNamespace(role=role, run_id='terminal-boundary', episode_id='terminal-child',
        path=((parent_role, 'parent'), (role, 'child')), assignment=value, scope={})
    return binding, context


def task_fixture(home, tmp_path, *, saved=False, standalone=False):
    binding, context = private(home, tmp_path)
    if standalone:
        context.path = (context.path[-1],)
    events = []
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE runtime_actions (run_id TEXT, episode_id TEXT, action TEXT, result TEXT, decision_index INTEGER)')
    @contextmanager
    def snapshot():
        events.append('snapshot.enter')
        try:
            yield
        finally:
            events.append('snapshot.exit')
    saved_context = {'saved': 'exact original context'}
    saved_schema = {'saved': 'exact original schema'}
    def row(table, *key):
        if table == 'runtime_model_calls' and saved:
            return {'request': json.dumps({'context': saved_context, 'schema': saved_schema}),
                    'response': '{}'}
        return None
    def schema(source):
        events.append('action_schema')
        return {'type': 'object'}
    def state(source):
        events.append('working_state')
        return {}
    workflow = SimpleNamespace(context=SimpleNamespace(require_run_id=lambda: context.run_id),
        grains={context.role: SimpleNamespace(name=context.role)}, run_id=context.run_id,
        specialist=lambda source: binding, is_job_source=lambda source: False,
        execution_binding=None, inprocess_replay=None, execution_handle=None,
        journal=SimpleNamespace(row=row, db=db, elapsed_view=lambda *_: {}),
        store=SimpleNamespace(read_snapshot=snapshot, get=lambda ref: None),
        working_state=state, local_outcome_preview=lambda value, **kw: value,
        source_credit_view=lambda source: binding.credit_view(context, {}),
        source_credit_binding=lambda source: {'version': 'controlled-original-credit-input'},
        pending_work=lambda source: [], delivery_status=lambda episode_id: [],
        controller_binding={}, catalog=lambda scope, **kw: [],
        knowledge=SimpleNamespace(context=lambda: {}), job_episode_options=lambda source: [],
        extra_report_sources=lambda source: {}, binding_context=lambda source: context,
        tools=SimpleNamespace(), action_schema=schema)
    request = EpisodeRequest(EpisodeGoal.root(objective='Retain original Terminal boundary behavior',
        result_contract={'type': 'object'}), Record({'initial_report': {}, 'episode_assignment': context.assignment}))
    try:
        task = binding.decision_source_type(workflow, context.path, request, {})
    except BaseException:
        db.close()
        raise
    context.episode_id = task.episode_id
    outcome = {'status': 'completed', 'feedback': {'code': 'original-returned-feedback'}}
    task.last_outcome = outcome
    task.feedback = outcome['feedback']
    seen = []
    returned = object()
    async def call(inputs, selected_schema):
        events.append('call')
        seen.append({'context': deepcopy(inputs), 'schema': deepcopy(selected_schema)})
        if not saved:
            assert inputs['feedback'] is task.feedback
        return {}, len(seen) - 1, inputs, selected_schema
    def apply_response(response, index, actual_context, selected_schema):
        events.append('apply_response')
        if len(seen) == 1 and not saved:
            task.feedback = {'status': 'invalid', 'code': 'controlled-returned-invalid'}
            return None
        return returned
    task.call, task.apply_response = call, apply_response
    view = SimpleNamespace(units_consumed=0, child_reports=(), controller_state={},
        model_inputs=lambda value, **kw: value)
    return SimpleNamespace(binding=binding, context=context, task=task, view=view, events=events,
        seen=seen, returned=returned, db=db, saved_context=saved_context, saved_schema=saved_schema)


def observe_next(value, *, original):
    call = OriginalTerminalNext.next if original else type(value.task).next
    try:
        actual = asyncio.run(call(value.task, value.view))
        assert actual is value.returned
        return {'events': value.events, 'seen': value.seen, 'feedback': value.task.feedback}
    finally:
        value.db.close()
