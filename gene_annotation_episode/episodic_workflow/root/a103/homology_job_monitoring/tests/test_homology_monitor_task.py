"""One actual legacy monitor/registry/Store, with explicitly controlled native status."""

import asyncio
from contextlib import contextmanager
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace, MethodType
from unittest.mock import patch
import pytest
PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a103'

def module(name):
    return import_module(PACKAGE + '.' + name)

def forbidden(*a, **kw):
    raise AssertionError('no process/network/native submission in task checks')

def operational(*a, **kw):
    return 0

@contextmanager
def actual(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with patch('subprocess.Popen', forbidden), patch('socket.socket.connect', forbidden), patch('socket.socket.connect_ex', forbidden):
        with module('state').Store(directory / 'store') as store:
            try:
                store.problem()
            except module('domain').ContractError as error:
                if str(error) != 'problem_not_initialized':
                    raise
                store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
            query = store.targets()[0]['id']
            scope = store.validate_scope()
            jm = module('homology_jobs')
            policy = module('local_jobs').LocalJobPolicy(128 * 1024 ** 2, 4 * 1024 ** 2)
            if not (directory / 'jobs/configuration.json').exists():
                program = directory / 'unexecuted-native-identity'
                program.write_text('never executed\n')
                database = directory / 'reference.faa'
                database.write_text('>controlled\nMACDEFGH\n')
                jobs = jm.HomologyJobs.create(directory / 'jobs', executable=jm.FileAsset(program, jm.digest(program)), reference_database=jm.FileAsset(database, jm.digest(database)), policy=policy, max_cpu=1)
            else:
                jobs = jm.HomologyJobs(directory / 'jobs')
            try:
                families = module('homology_service_setup').create_homology_bindings(jobs, parser_policy=policy, credit_projector=operational, credit_binding={'version': 'controlled-operational-no-credit'}, monitoring_projector=module('monitoring_credit').MonitoringInformationCredit(information_unit=3), monitoring_binding={'version': 'controlled-monitor-information-unit', 'information_unit': 3})
                bindings = families['legacy_annotation']
                binding = bindings['job_monitor']
                run_id = 'private-homology-monitor-check'
                runtime = module('runtime')
                job = jobs.order(query_ref=query, query_fasta='>query\nMACDEFGH\n', cpu=1, operation_key='original-fixed-job')
                handoff = {'job_ref': job, 'registry_ref': jobs.config['registry_ref'], 'backend': jm.VERSION, 'status_interface': 'homology.status.v1', 'progress_interface': 'homology.progress.v1', 'results_interface': 'homology.results.v1'}
                status = {'job_ref': job, 'registry_ref': jobs.config['registry_ref'], 'state': 'running', 'outcome': 'pending', 'elapsed_seconds': 1.0, 'duration_measure': 'systemd_service_wall_seconds', 'native_returncode': None, 'failure_code': None, 'resource': None, 'progress_kind': 'native_execution_state_and_output_bytes_not_search_fraction', 'outputs': [{'role': role, 'available': False, 'bytes': None, 'writer_closed': False} for role in jm.OUTPUTS]}
                with patch.object(jobs, 'handoff', return_value=deepcopy(handoff)), patch.object(jobs, 'receive', return_value=deepcopy(status)):
                    assignment = {'job_ref': job, 'query_ref': query, 'cpu': 1, 'handoff': deepcopy(handoff), 'prior_sample_refs': [], 'prior_samples': []}
                    path = (('annotation', 'root'), ('job_monitor', 'original'))
                    episode_id = module('method_loop.identities').EpisodeRef(run_id, path).episode_id
                    journal = module('episode_journal').Journal(store, run_id)
                    projected = []
                    received = []
                    executed = []

                    def credit(source):
                        value = binding.credit_view(source)
                        projected.append(deepcopy(value))
                        return value

                    async def execute(source, name, arguments, **kw):
                        executed.append(kw['operation_key'])
                        return await binding.execute(source, name, arguments, operation_key=kw['operation_key'])

                    async def updates(source, index, result):
                        return result
                    workflow = SimpleNamespace(context=object(), grains={'job_monitor': object(), 'annotation': object()}, inprocess_completion_order=None, receipts=None, scientific_process_binding=None, episode_bindings=module('episode_bindings').EpisodeBindingRegistry(()), job_episodes=binding, contract_information_profile=lambda source: None, binding_context=lambda source: source, specialist=lambda source: None, journal=journal, run_id=run_id, store=store, source_credit_view=credit, expose_assigned_job=lambda source: None, receive_tool_attributions=lambda *a, **kw: None, archive=SimpleNamespace(store=lambda value: value), execution_binding=None, inprocess_replay=None, pending_work=lambda source:[],  execute=execute, receive_native_outcome=lambda *a: None, receive_outcome=lambda source, selection, result, index: received.append((index, result['status'])), automatic_score_updates=updates, controller_value=lambda source, index, value: {'index': index, 'credit': value}, is_job_source=lambda source: source.path[-1][0] == 'job_monitor', permits_common_action=lambda source, kind: kind in {'tool', 'wait'}, native_event_information=None, decision_protocol=None, services=SimpleNamespace(instructions=module('runtime_prompt').instructions), progress_provider=None, native_timing_information=None)
                    workflow.homology_episode_bindings = families
                    for name in ('legacy_parent_for_path', 'job_episode_for_child', 'job_episode_for_path'):
                        setattr(workflow, name, MethodType(getattr(runtime.Workflow, name), workflow))
                    with patch.object(runtime.Episode, 'identity', return_value=SimpleNamespace(episode_id=episode_id)), patch.object(runtime, 'FeedbackEpisode', side_effect=lambda grain, key, source, *a, **kw: source):
                        task = runtime.Workflow.build(workflow, 'job_monitor', 'original', 'Learn actual assigned execution information.', module('communication').plain(scope), parent_path=path[:-1], job_assignment=deepcopy(assignment))
                    task.checkpoint = lambda: None
                    projected.clear()
                    yield SimpleNamespace(binding=binding, bindings=bindings, task=task, workflow=workflow, jobs=jobs, store=store, journal=journal, assignment=assignment, handoff=handoff, status=status, runtime=runtime, projected=projected, received=received, executed=executed, episode_id=episode_id)
            finally:
                jobs.close()

def action(f, index=0):
    selection = {'kind': 'tool', 'tool': 'homology.sample', 'arguments': {}}
    return asyncio.run(f.task.execute(selection, index))

@pytest.fixture
def f(tmp_path):
    with actual(tmp_path) as value:
        yield value


def test_actual_build_selects_registered_legacy_monitor(f):
    assert type(f.task) is getattr(f.binding, 'decision_source_type', f.runtime.DecisionSource)
    if hasattr(f.binding, 'decision_source_type'):
        assert not isinstance(f.task, f.runtime.DecisionSource)

@pytest.mark.parametrize('variant', ['no-job-binding', 'submission-sibling', 'registry-priority'])
def test_build_fallback_keeps_original_selection_priority(f, variant):
    original = f.workflow.job_episodes
    if variant == 'no-job-binding':
        f.workflow.job_episodes = None
    elif variant == 'submission-sibling':
        f.workflow.job_episodes = f.bindings['job_launch']
    else:
        f.workflow.episode_bindings = SimpleNamespace(roles=('job_monitor',), for_path=lambda p: SimpleNamespace(decision_source_type=f.runtime.DecisionSource))
    f.workflow.source_credit_view = lambda source: {'credit': 0}
    f.workflow.expose_assigned_job = lambda source: None
    with patch.object(f.runtime.Episode, 'identity', return_value=SimpleNamespace(episode_id=f.episode_id)), patch.object(f.runtime, 'FeedbackEpisode', side_effect=lambda grain, key, source, *a, **kw: source):
        task = f.runtime.Workflow.build(f.workflow, 'job_monitor', 'original', 'Learn actual assigned execution information.', f.task.scope, parent_path=f.task.path[:-1], job_assignment=deepcopy(f.assignment))
    assert type(task) is f.runtime.DecisionSource
    f.workflow.job_episodes = original

def test_original_incoming_schema_and_role_rejection(f):
    schemas = f.binding.commission_schemas({'properties': {'kind': {'const': 'child'}, 'goal': {'type': 'string'}}})
    assert len(schemas) == 1 and schemas[0]['properties']['role'] == {'type': 'string', 'const': 'job_monitor'}
    assert 'prior_sample_refs' in schemas[0]['properties'] and 'delay_seconds' in schemas[0]['properties']
    with pytest.raises(ValueError, match='^unknown_job_episode_role$'):
        f.binding.assign(f.store, 'job_launch', {}, f.task.scope, operation_key='unacquired')
    assert f.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0

def test_real_sample_record_action_progress_and_replay(f):
    first = action(f)
    again = action(f)
    assert first == again and len(f.executed) == len(f.projected) == len(f.received) == 1
    row = f.journal.row('runtime_actions', f.episode_id, 0)
    outcome = json.loads(row['result'])
    sample = outcome['result']
    assert outcome['operational_sample_ref'] == sample['sample_ref']
    assert json.loads(f.jobs.db.execute('SELECT body FROM samples WHERE sample_ref=?', (sample['sample_ref'],)).fetchone()[0]) == sample
    assert first['credit'] == f.binding.credit_view(f.task)['credit']
    assert f.binding.latest_sample(f.task) == sample and f.binding.recorded_sample(f.store, sample['sample_ref'], f.assignment) == sample

@pytest.mark.parametrize('failure', [ValueError('controlled_status_failure'), sqlite3.OperationalError('controlled_storage_failure')], ids=['invalid-status', 'storage-failure'])
def test_returned_sample_failure_enters_original_progress(f, failure):
    with patch.object(f.jobs, 'sample', side_effect=failure):
        result = action(f)
        replay = action(f)
    assert result == replay and f.received == [(0, 'failed')] and (len(f.projected) == len(f.executed) == 1)
    assert json.loads(f.journal.row('runtime_actions', f.episode_id, 0)['result'])['status'] == 'failed'

def test_unchanged_new_sample_is_not_information_progress(f):
    first = action(f, 0)
    second = action(f, 1)
    assert first['credit'] == second['credit'] and len(f.executed) == 2 and (len(f.received) == 2)
    assert f.jobs.db.execute('SELECT count(*) FROM samples').fetchone()[0] == 2

@pytest.mark.parametrize('completed', [False, True], ids=['unfinished', 'completed'])
def test_original_saved_reason_branch_replay(f, completed):
    selection = {'kind': 'reason', 'commit': {'interpretation_accounts': []}}
    result = {'status': 'completed', 'record_refs': [], 'changed_record_refs': []}
    f.journal.save('runtime_actions', {'episode_id': f.episode_id, 'decision_index': 9, 'action': json.dumps(selection), 'result': json.dumps(result) if completed else None, 'credit': 0 if completed else None})
    with patch.object(f.store, 'commit_reasoning', return_value=result) as commit:
        observed = asyncio.run(f.task.execute(selection, 9))
        assert asyncio.run(f.task.execute(selection, 9)) == observed
    assert commit.call_count == (0 if completed else 1)
    assert len(f.received) == (0 if completed else 1)

def test_selected_wait_preserves_prior_credit(f):
    calls = []

    async def wait(source, condition, index):
        calls.append((condition, index))
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': []}
    f.workflow.perform_selected_wait = wait
    f.workflow.last_observed_credit = lambda source: 7
    selection = {'kind': 'wait', 'condition': {'original': 'wait'}}
    assert asyncio.run(f.task.execute(selection, 4)) == {'index': 4, 'credit': 7}
    assert asyncio.run(f.task.execute(selection, 4)) == {'index': 4, 'credit': 7}
    assert calls == [(selection['condition'], 4)] and (not f.projected)

def test_original_sample_validation_rejects_changed_native_fact(f):
    action(f)
    sample = f.binding.latest_sample(f.task)
    schema = module('homology_jobs').SAMPLE_SCHEMA
    f.binding.validate_report(sample, f.assignment, role='job_monitor', store=f.store, schema=schema)
    changed = {**sample, 'elapsed_seconds': sample['elapsed_seconds'] + 1}
    with pytest.raises(module('communication').ReportBoundaryError, match='Native sample fields differ'):
        f.binding.validate_report(changed, f.assignment, role='job_monitor', store=f.store, schema=schema)

@pytest.mark.parametrize('redelivery', [False, True], ids=['initial', 'redelivery'])
def test_original_saved_parent_counterpart_receives_progress(f, redelivery):
    parent = SimpleNamespace(episode_id='original-parent', path=(('annotation', 'root'),), scope=f.task.scope)
    f.journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': 3, 'action': json.dumps({'kind': 'job_child', 'role': 'job_monitor'}), 'result': None, 'credit': None})
    values = []
    f.workflow.is_job_source = lambda source: source is f.task
    f.workflow.progress_provider = SimpleNamespace(receive_form=lambda *a: values.append(a))
    f.workflow._receive_form = lambda *a, **kw: f.runtime.Workflow._receive_form(f.workflow, *a, **kw)
    schema = {'type': 'object', 'properties': {}, 'additionalProperties': True}
    form = {'controlled': 'original report'}
    assert f.runtime.Workflow.receive_form(f.workflow, parent, form, schema, 3, redelivery=redelivery) == []
    assert values == [(parent.episode_id, form, schema, parent.scope, f'{f.workflow.run_id}:{parent.episode_id}:3:typed_form')]

@pytest.mark.parametrize('scenario', ['minimal', 'bootstrap', 'full-unrecognized', 'lookup-without-state', 'hpc-priority', 'hpc-bootstrap', 'hpc-update', 'hpc-lookup', 'lost-task-update'])
def test_actual_provider_preserves_original_policy(f, scenario):
    providers = module('providers')
    frames = module('decision_context')
    original = object.__new__(providers._SessionConnection)
    private = object.__new__(providers._SessionConnection)
    original.scientific_prompt_states = {}
    private.scientific_prompt_states = {}
    state = {'working_state': f.binding.working_state(f.task), 'scope': f.task.scope, 'goal': {'objective': 'Observe assigned work'}}
    hpc_state = {**state, 'hpc_commission': {'objective': 'Preserve original priority'}}
    context = {} if scenario == 'minimal' else frames.state_frame(state) if scenario == 'bootstrap' else state if scenario == 'full-unrecognized' else {'version': frames.VERSION, 'kind': 'decision_lookup_result', 'result': {'original': 'record'}} if scenario == 'lookup-without-state' else hpc_state
    key = (f.episode_id, 'REASONING')
    if scenario == 'hpc-bootstrap':
        context = frames.state_frame(hpc_state)
    if scenario in {'hpc-update', 'hpc-lookup', 'lost-task-update'}:
        original.scientific_prompt_states[key] = deepcopy(hpc_state)
        private.scientific_prompt_states[key] = deepcopy(hpc_state)
        context = {'version': frames.VERSION, 'kind': 'decision_lookup_result', 'result': {'original': 'record'}} if scenario == 'hpc-lookup' else frames.state_frame(state, hpc_state) if scenario == 'lost-task-update' else frames.state_frame({**hpc_state, 'goal': {'objective': 'Retain the original task state.'}}, hpc_state)
    instructions = f.task.instructions({})
    expected = original._presentation(f.episode_id, 'REASONING', instructions, deepcopy(context))
    renderer = getattr(f.binding, 'decision_prompt_renderer', None)
    observed = private._presentation(f.episode_id, 'REASONING', instructions, deepcopy(context), **{'prompt_renderer': renderer} if renderer else {})
    assert observed == expected and private.scientific_prompt_states == original.scientific_prompt_states
    if scenario in {'minimal', 'bootstrap', 'full-unrecognized', 'lookup-without-state', 'lost-task-update'}:
        assert observed == (json.dumps(context, allow_nan=False), instructions)
    else:
        assert isinstance(observed[0], str) and observed[0] and (key in private.scientific_prompt_states)

def test_original_instruction_composition_and_caller_yield(f):
    assert f.task.instructions({}) == module('runtime_prompt').instructions(f.task, {})
    assert 'Repeated unchanged samples are not progress.' in f.task.instructions({})
    calls = []
    sentinel = object()
    f.workflow.controller_factory = lambda path, credit: calls.append((path, credit)) or sentinel
    f.workflow.has_native_estimation = lambda: False
    with patch.object(f.runtime.Episode, 'identity', return_value=SimpleNamespace(episode_id=f.episode_id)), patch.object(f.runtime, 'ExecutionContextController', side_effect=lambda controller, *a, **kw: controller):
        assert f.runtime.Workflow.controller(f.workflow, f.task.path) is sentinel
    assert calls == [(f.task.path, f.journal.row('runtime_episodes', f.episode_id)['initial_credit'])]


def test_ready_owned_child_precedes_new_decision(f):
    child = object()
    paths = []
    f.task._execution_context = SimpleNamespace(_ready_owned_child=lambda path: paths.append(path) or child)
    assert asyncio.run(f.task.next(SimpleNamespace(units_consumed=0))) is child
    assert paths == [f.task.path] and f.task.calls == 0

def test_inherited_sample_is_input_without_new_monitor_credit(f):
    action(f)
    sample = f.binding.latest_sample(f.task)
    assignment = {**deepcopy(f.assignment), 'prior_sample_refs': [sample['sample_ref']], 'prior_samples': [deepcopy(sample)]}
    inherited = SimpleNamespace(path=(('job_monitor', 'new-original-child'),), episode_id='new-original-child', workflow=f.workflow, request=SimpleNamespace(message=SimpleNamespace(as_record=lambda: {'job_assignment': assignment})))
    assert f.binding.credit_view(inherited)['credit'] == 0
    assert f.binding.latest_sample(inherited) is None and f.binding.latest_sample(inherited, include_inherited=True) == sample

@pytest.mark.parametrize('prior', ['none', 'retained', 'foreign'])
def test_actual_incoming_assignment_preserves_original_sample_identity(f, prior):
    samples = []
    if prior == 'retained':
        action(f)
        samples = [f.binding.latest_sample(f.task)['sample_ref']]
    elif prior == 'foreign':
        samples = ['job_sample_unowned']
    selection = {'handoff': deepcopy(f.handoff), 'prior_sample_refs': samples}
    with patch.object(f.jobs, 'check_handoff', return_value={'handoff': deepcopy(f.handoff), 'sample': deepcopy(f.status)}):
        if prior == 'foreign':
            with pytest.raises(ValueError, match='^prior_monitoring_sample_must_belong_to_assigned_job$'):
                f.binding.assign(f.store, 'job_monitor', selection, f.task.scope, operation_key='controlled-parent-selection')
        else:
            assigned = f.binding.assign(f.store, 'job_monitor', selection, f.task.scope, operation_key='controlled-parent-selection')
            assert assigned['job_ref'] == f.assignment['job_ref'] and assigned['query_ref'] == f.assignment['query_ref']
            assert assigned['handoff'] == f.handoff and assigned['prior_sample_refs'] == samples
            assert assigned['prior_samples'] == ([] if prior == 'none' else [f.binding.latest_sample(f.task)])
    assert f.jobs._row(f.assignment['job_ref'])['submission_requested'] == 0


@pytest.mark.parametrize('role', ['job_launch', 'job_results'])
def test_monitor_fresh_catalog_and_goal_exclude_other_owned_roles(f, role):
    source = SimpleNamespace(path=((role, 'counterfactual-nonowner'),))
    assert [item['name'] for item in f.binding.catalog(f.task)] == ['homology.sample']
    if hasattr(f.binding, 'decision_source_type'):
        with pytest.raises(KeyError):
            f.binding.catalog(source)
        with pytest.raises(KeyError):
            f.binding.instructions(role)
    else:
        assert f.binding.catalog(source) == f.bindings[role].catalog(source)
        assert f.binding.instructions(role) == f.bindings[role].instructions(role)
    assert set(f.binding.describe()) == {'job_monitor'}

@pytest.mark.parametrize('role', ['job_launch', 'job_results'])
def test_actual_adapter_uses_authenticated_sibling_owner(f, role):
    adapter = module('a103_homology_resource_adapter').HomologyResourceAdapter(f.bindings, f.store, f.journal)
    assert type(adapter.homology[role]) is type(f.bindings[role]) and adapter.homology['job_monitor'] is f.binding
    selected = adapter._selection(f.assignment['cpu'])
    assignment = {'adapter_assignment': deepcopy(f.assignment), 'resource_selection': selected, 'handoff': {'resource_selection': selected}, 'requested_data_selector': {}}
    context = SimpleNamespace(role='results' if role == 'job_results' else 'launch_local', episode_id='original-resource-owner', run_id=f.workflow.run_id, path=(('resource', 'original-resource-owner'),), scope=f.task.scope, assignment=assignment)
    source = adapter._legacy(context)
    assert source.path[-1][0] == role and source.episode_id == context.episode_id
    assert adapter.catalog(context) == f.bindings[role].catalog(source)
    name = 'homology.coverage' if role == 'job_results' else 'homology.environment'
    calls = []
    outcome = {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': {'controlled': 'sibling-port'}, 'feedback': None}

    async def execute(actual, name, args, *, operation_key):
        calls.append((actual.path, name, args, operation_key))
        return deepcopy(outcome)
    with patch.object(f.bindings[role], 'execute', side_effect=execute), patch.object(adapter.information, 'selected_handoff', return_value=None), patch.object(adapter.information, 'publish_handoff', side_effect=lambda c, n, a, o, k: o):
        assert asyncio.run(adapter.execute(context, name, {}, 'original-resource-operation')) == outcome
    assert calls == [(source.path, name, {}, 'original-resource-operation')] and f.jobs._row(f.assignment['job_ref'])['submission_requested'] == 0


@pytest.mark.parametrize('role', ['job_launch', 'job_results', 'unregistered'])
def test_original_nonowner_fact_source_and_incoming_guards(f, role):
    assert f.binding.fact_sources(role) == {}
    with pytest.raises(ValueError, match='^unknown_job_episode_role$'):
        f.binding.credit_kind(role)
    with pytest.raises(ValueError, match='^unknown_job_episode_role$'):
        f.binding.assign(f.store, role, {}, f.task.scope, operation_key='rejected-before-acquisition')
    assert f.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
    assert f.jobs._row(f.assignment['job_ref'])['submission_requested'] == 0

def test_monitor_credit_uses_original_lexical_callback_and_binding(f):
    method = f.binding._monitor_credit
    assert method.__qualname__ == 'HomologyEpisodeCredit._monitor_credit'
    descriptor = f.binding.as_record()
    assert descriptor['job_credit_calculator'] == operational.__module__ + '.' + operational.__qualname__
    assert descriptor['monitoring_projector'] == type(f.binding.monitoring_projector).__module__ + '.' + type(f.binding.monitoring_projector).__qualname__
    value = f.binding.initial_credit(f.store, 'job_monitor', f.assignment, f.episode_id, f.workflow.run_id)
    assert value == f.binding.credit_view(f.task)['credit'] == 0
    with pytest.raises(ValueError, match='^unknown_job_episode_role$'):
        f.binding.initial_credit(f.store, 'unregistered', f.assignment, f.episode_id, f.workflow.run_id)
    assert not hasattr(f.binding, '_launch_credit') and (not hasattr(f.binding, '_results_credit'))
    for role, home, name in (('job_launch', 'homology_job_submission', '_launch_credit'), ('job_results', 'homology_result_acquisition', '_results_credit')):
        callback = getattr(f.bindings[role], name)
        assert callback.__self__ is f.bindings[role]
        assert callback.__qualname__ == 'HomologyEpisodeCredit.' + name

def test_actual_saved_monitor_facts_bypass_new_projection(f):
    action(f)
    with patch.object(f.jobs, 'check_handoff', return_value={'handoff': f.handoff, 'sample': f.status}):
        facts = f.binding.facts(f.task)
    assert facts['job_sample'] == f.binding.latest_sample(f.task)
    assert 'job_checked_status' not in facts and 'job_result_progress' not in facts
    f.journal.save('runtime_forms', {'episode_id': f.episode_id, 'facts': json.dumps({**facts, 'interpretations': {}}), 'form': json.dumps({})})
    f.workflow.episode_bindings = SimpleNamespace(current_report_facts=lambda context: {})
    with patch.object(f.binding, 'facts', side_effect=forbidden), patch.object(f.workflow, 'source_credit_view', side_effect=forbidden):
        assert f.runtime.Workflow.facts(f.workflow, f.task) == facts

@pytest.mark.parametrize('prior', ['retained', 'foreign'])
def test_original_incoming_checked_status_uses_actual_sibling_result(f, prior):
    checked = {'checked_at_unix_seconds': 3, **deepcopy(f.status)}
    control = {'handoff': deepcopy(f.handoff), 'sample': deepcopy(f.status), 'checked_at_unix_seconds': 3}
    launch = f.bindings['job_launch']
    source = SimpleNamespace(path=(('job_launch', 'original-port'),), episode_id='original-launch-port', workflow=f.workflow, scope=f.task.scope, request=f.task.request)
    with patch.object(f.jobs, 'check_handoff', return_value=deepcopy(control)):
        result = asyncio.run(launch.execute(source, 'homology.check_handoff', {}, operation_key='original-launch-check'))
        assert result['status'] == 'completed' and result['result'] == control
        f.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': 0, 'action': json.dumps({'kind': 'tool', 'tool': 'homology.check_handoff', 'arguments': {}}), 'result': json.dumps(result), 'credit': 0})
        supplied = deepcopy(checked)
        if prior == 'foreign':
            supplied['checked_at_unix_seconds'] = 4
        selection = {'handoff': deepcopy(f.handoff), 'prior_sample_refs': [], 'prior_checked_statuses': [supplied]}
        if prior == 'foreign':
            with pytest.raises(ValueError, match='^prior_checked_status_must_match_recorded_assigned_job_check$'):
                f.binding.assign(f.store, 'job_monitor', selection, f.task.scope, operation_key='original-monitor-request')
        else:
            assignment = f.binding.assign(f.store, 'job_monitor', selection, f.task.scope, operation_key='original-monitor-request')
            assert assignment['prior_checked_statuses'] == [checked] and assignment['prior_sample_refs'] == []
    assert f.jobs._row(f.assignment['job_ref'])['submission_requested'] == 0

@pytest.mark.parametrize('mode', ['returned', 'raised'])
def test_original_instruction_service_callback(f, mode):
    context = object()
    marker = object()
    error = RuntimeError('original callback exception')
    calls = []

    def callback(source, state):
        calls.append((source, state))
        if mode == 'raised':
            raise error
        return marker
    f.workflow.services = SimpleNamespace(instructions=callback)
    with patch.object(type(f.task), 'instruction_composer', staticmethod(forbidden), create=True):
        if mode == 'raised':
            with pytest.raises(RuntimeError) as caught_error:
                f.task.instructions(context)
            assert caught_error.value is error
        else:
            assert f.task.instructions(context) is marker
    assert calls == [(f.task, context)]

def test_default_instruction_service_uses_private_composer(f):
    context = {}
    calls = []
    prompt = module('runtime_prompt')
    f.workflow.services = module('episode_services').WorkflowServices(f.workflow)
    original = getattr(type(f.task), 'instruction_composer', None)
    if hasattr(f.binding, 'decision_source_type'):
        assert original is module('homology_job_monitoring.instructions').instructions

        def composer(source, state):
            calls.append((source, state))
            return original(source, state)
        expected = original(f.task, context)
        with patch.object(type(f.task), 'instruction_composer', staticmethod(composer)), patch.object(prompt, 'instructions', side_effect=forbidden):
            assert f.task.instructions(context) == expected
    else:
        assert original is None
        original = prompt.instructions
        expected = original(f.task, context)

        def composer(source, state):
            calls.append((source, state))
            return original(source, state)
        with patch.object(prompt, 'instructions', side_effect=composer):
            assert f.task.instructions(context) == expected
    assert calls == [(f.task, context)] and f.projected == f.executed == f.received == []

def test_default_instruction_service_nonparticipant_fallback(f):
    context = object()
    marker = object()
    calls = []
    source = SimpleNamespace(instruction_composer=forbidden)
    service = module('episode_services').WorkflowServices(f.workflow)
    with patch.object(module('runtime_prompt'), 'instructions', side_effect=lambda owner, state: calls.append((owner, state)) or marker):
        assert service.instructions(source, context) is marker
    assert calls == [(source, context)]
