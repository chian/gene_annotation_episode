"""Actual A104 job ownership, rejected handoffs, caller credit and saved replay.

The fixture caller supplies a declared zero operational projection; this is
explicit test configuration required by the original interface, not a proposed
scientific projector. No real job is submitted or native executable launched.
"""
import asyncio
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

HOMES = ('homology_job_submission', 'homology_job_monitoring', 'homology_result_acquisition')
ROLES = ('job_launch', 'job_monitor', 'job_results')

def module(name):
    return importlib.import_module('gene_annotation_episode.episodic_workflow.root.a104.' + name)

def declared_fixture_credit(store, *, role, assignment, episode_id, run_id):
    """Explicit zero fixture scalar; no result or scientific credit asserted."""
    return 0.

def forbidden(*args, **kwargs):
    raise AssertionError('fixture_does_not_authorize_native_or_provider_work')

@pytest.fixture(params=tuple(zip(HOMES, ROLES)), ids=HOMES)
def case(request, tmp_path):
    home, role = request.param
    jobs_module = module('homology_jobs')
    policy = module('local_jobs').LocalJobPolicy.from_config()
    executable, reference = tmp_path / 'not-a-native-executable', tmp_path / 'references.faa'
    executable.write_bytes(b'An inert required-test operand; never executed.\n')
    reference.write_bytes(b'>explicit_controlled_reference\nMACDEFGH\n')
    asset = lambda path: jobs_module.FileAsset(path, hashlib.sha256(path.read_bytes()).hexdigest())
    jobs = jobs_module.HomologyJobs.create(tmp_path / 'jobs', executable=asset(executable),
        reference_database=asset(reference), policy=policy, max_cpu=1)
    try:
        with module('state').Store(tmp_path / 'store') as store:
            scope = {'subject_refs': store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']}
            query = scope['subject_refs'][0]
            job_ref = jobs.order(query_ref=query, query_fasta='>query\nMACDEFGH\n', cpu=1,
                operation_key='original-unsubmitted-job')
            assignment = {'job_ref': job_ref, 'query_ref': query, 'cpu': 1}
            handoff = {'job_ref': job_ref, 'registry_ref': jobs.config['registry_ref'], 'backend': jobs_module.VERSION,
                'status_interface': 'homology.status.v1', 'progress_interface': 'homology.progress.v1',
                'results_interface': 'homology.results.v1'}
            if role != 'job_launch': assignment['handoff'] = deepcopy(handoff)
            if role == 'job_monitor': assignment.update(prior_sample_refs=[], prior_samples=[])
            definition = {'version': 'explicit_homology_required_test_zero_credit_v1',
                'meaning': 'No scientific or operational completion is claimed by this controlled fixture.'}
            binding = module(home + '.episode').HomologyEpisode(jobs, parser_policy=policy,
                credit_projector=declared_fixture_credit, credit_binding=definition,
                monitoring_projector=declared_fixture_credit, monitoring_binding=definition)
            runtime = module('runtime')
            journal = module('episode_journal').Journal(store, 'original-homology-test')
            path = ((role, 'controlled'),)
            identity = module('method_loop.identities').EpisodeRef(journal.run_id, path).episode_id
            source = SimpleNamespace(path=path, episode_id=identity, scope=scope,
                request=SimpleNamespace(message=SimpleNamespace(as_record=lambda: {'job_assignment': deepcopy(assignment)})),
                workflow=SimpleNamespace(store=store, run_id=journal.run_id, journal=journal))
            journal.save('runtime_episodes', {'episode_id': identity, 'path': runtime._json(path),
                'request': runtime._json({'message': {'scope': scope, 'job_assignment': assignment}}),
                'initial_credit': 0., 'state': 'active', 'completion': None, 'archive': None})
            yield SimpleNamespace(home=home, role=role, binding=binding, jobs=jobs, store=store,
                scope=scope, assignment=assignment, handoff=handoff, source=source,
                journal=journal, runtime=runtime, policy=policy, tmp_path=tmp_path)
    finally:
        jobs.close()

def test_actual_typed_constructor_descriptor_and_own_catalog(case, record_property):
    binding = case.binding
    assert binding.binding_path == case.home and binding.roles == (case.role,)
    assert binding.commissioning_parent == 'legacy_annotation'
    record = binding.as_record()
    assert record['binding_id'] == case.home and record['parser_policy'] == case.policy.to_dict()
    assert record['job_credit_calculator'] == declared_fixture_credit.__module__ + '.' + declared_fixture_credit.__qualname__
    assert binding.initial_credit(case.store, case.role, case.assignment, case.source.episode_id, case.journal.run_id) == 0.
    assert binding.credit_view(case.source) == {'credit': 0.}
    assert binding.working_state(case.source) == {'role': case.role, 'assignment': case.assignment}
    expected = {'job_launch': {'homology.environment', 'homology.configure', 'homology.stage', 'homology.submit',
        'homology.resume_start', 'homology.check_handoff'}, 'job_monitor': {'homology.sample'},
        'job_results': {'homology.extract', 'homology.coverage', 'homology.errors'}}
    assert {row['name'] for row in binding.catalog(case.source)} == expected[case.role]
    assert binding.instructions(case.role) and set(binding.describe()) == {case.role}
    record_property('original_scalar_configuration', json.dumps({'role': case.role,
        'credit_kind': binding.credit_kind(case.role), 'role_credit_bindings': record['role_credit_bindings'],
        'calculator': record['job_credit_calculator'], 'monitor': record['monitoring_projector']}, sort_keys=True))

def test_actual_assignment_replay_or_unsubmitted_handoff_rejection(case):
    selection = {'existing_job_ref': case.assignment['job_ref']} if case.role == 'job_launch' else {
        'handoff': deepcopy(case.handoff), 'prior_sample_refs': []}
    before = [tuple(row) for row in case.jobs.db.execute('SELECT * FROM orders')]
    if case.role == 'job_launch':
        first = case.binding.assign(case.store, case.role, selection, case.scope, operation_key='repair-existing')
        second = case.binding.assign(case.store, case.role, deepcopy(selection), case.scope, operation_key='repair-existing')
        assert first == second == case.assignment
    else:
        with pytest.raises(ValueError, match='job_submission_handoff_unresolved'):
            case.binding.assign(case.store, case.role, selection, case.scope, operation_key='unsubmitted-read')
    assert [tuple(row) for row in case.jobs.db.execute('SELECT * FROM orders')] == before

def test_original_unavailable_execution_result_is_retained(case, monkeypatch, record_property):
    # Submit/configure/stage are forbidden ports. Monitor/Results use the actual
    # unreadable original handoff and must retain the returned failure.
    for name in ('submit', 'resume_start', 'stage'):
        monkeypatch.setattr(case.jobs, name, forbidden)
    action = {'job_launch': ('homology.configure', {}), 'job_monitor': ('homology.sample', {}),
        'job_results': ('homology.extract', {'limit': 1})}[case.role]
    result = asyncio.run(case.binding.execute(case.source, action[0], deepcopy(action[1]),
        operation_key='original-executed-unavailable'))
    assert result['status'] == 'failed' and result['record_refs'] == result['changed_record_refs'] == []
    assert result['feedback']['job_ref'] == case.assignment['job_ref']
    assert result['feedback']['operation'] == action[0]
    assert result['feedback']['code'] == ('configured_executable_unavailable_or_changed'
        if case.role == 'job_launch' else 'job_submission_handoff_unresolved')
    assert not case.jobs._row(case.assignment['job_ref'])['submission_requested']
    record_property('original_failed_native_outcome', json.dumps(result, sort_keys=True))

def test_rejected_tool_is_not_an_executed_action(case):
    def actions():
        return [tuple(row) for row in case.store.db.execute(
            'SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index',
            (case.journal.run_id, case.source.episode_id))]
    before = actions()
    with pytest.raises(ValueError, match='tool_not_owned_by_job_role'):
        asyncio.run(case.binding.execute(case.source, 'not-an-owned-tool', {}, operation_key='never-acquired'))
    assert actions() == before

def test_actual_task_and_original_caller_controller_connection(case, monkeypatch, record_property):
    calls = []
    def supplied_controller(path, initial_credit):
        calls.append((path, initial_credit))
        return module('numerical').YieldController('original-job-controller', initial_credit, .5)
    tools = module('tools').ToolRegistry(case.store, clients=SimpleNamespace(request=forbidden))
    workflow = case.runtime.Workflow(case.store, tools, SimpleNamespace(complete=forbidden),
        case.tmp_path / 'workflow', case.journal.run_id, controller_factory=supplied_controller,
        project_credit=declared_fixture_credit, job_episodes=case.binding,
        annotation_child_roles=(), root_role=case.role, episode_binding_factories=(),
        wait_inputs_version='wait_inputs_binding_v1', completed_action_inputs_version=None)
    # Explicit standalone controlled assignment. This does not claim the
    # rejected parent handoff above was ever admitted or submitted.
    episode = workflow.build(case.role, 'owned-task', 'Preserve the original job boundary', case.scope,
        job_assignment=deepcopy(case.assignment))
    selected = getattr(case.binding, 'decision_source_type', case.runtime.DecisionSource)
    assert type(episode.source) is selected
    if os.environ.get('A104_HOMOLOGY_PHASE') == 'connected':
        assert selected.__module__ == type(case.binding).__module__.removesuffix('.episode') + '.task'
    controller = workflow.controller(episode.source.path)
    assert calls == [(episode.source.path, 0.)]
    initial = controller.state().as_record()
    replay = workflow.controller(episode.source.path)
    assert replay.state().as_record() == initial and len(calls) == 2
    schema = workflow.action_schema(episode.source)
    assert schema
    instructions = episode.source.instructions({})
    assert case.binding.instructions(case.role) in instructions
    selected_action = {'kind': 'tool', 'tool': {'job_launch': 'homology.configure',
        'job_monitor': 'homology.sample', 'job_results': 'homology.extract'}[case.role],
        'arguments': {'limit': 1} if case.role == 'job_results' else {}}
    returned = asyncio.run(episode.source.execute(selected_action, 0))
    saved = workflow.journal.row('runtime_actions', episode.source.episode_id, 0)
    payload = json.loads(saved['result'])
    assert payload['status'] == 'failed' and json.loads(saved['action']) == selected_action
    assert returned.as_record()['credit'] == 0.
    assert asyncio.run(episode.source.execute(deepcopy(selected_action), 0)).as_record() == returned.as_record()
    assert json.loads(workflow.journal.row('runtime_actions', episode.source.episode_id, 0)['result']) == payload
    record_property('original_controller_and_failed_replay', json.dumps({'initial': initial,
        'returned': returned.as_record(), 'payload': payload, 'request': episode.request.as_record()}, sort_keys=True))

def test_private_presentation_uses_original_context_precedence(case):
    kind = module('providers')._SessionConnection
    old, current = object.__new__(kind), object.__new__(kind)
    old.scientific_prompt_states, current.scientific_prompt_states = {}, {}
    renderer = getattr(case.binding, 'decision_prompt_renderer', None)
    decision = module('decision_context')
    original = {'working_state': {'role': case.role}, 'job_assignment': deepcopy(case.assignment)}
    updated = {**original, 'retained_job_outcome': {'status': 'failed'}}
    for context in (original, decision.state_frame(original), decision.state_frame(updated, original),
            {'version': decision.VERSION, 'kind': 'decision_lookup_result', 'result': {'job': 'original'}}):
        expected = old._presentation(case.source.episode_id, 'REASONING', 'Original job goal', deepcopy(context))
        actual = current._presentation(case.source.episode_id, 'REASONING', 'Original job goal', deepcopy(context), prompt_renderer=renderer)
        assert actual == expected and current.scientific_prompt_states == old.scientific_prompt_states
