"""Bounded pure/storage checks. No SSH stub, qsub, native process or model call."""
import asyncio
from copy import deepcopy
import json
import math
from pathlib import Path
import time

import pytest

from gene_annotation_episode import hpc_prediction as prediction
from gene_annotation_episode import hpc_queue
from gene_annotation_episode.hpc_campaign import accepts, build_plan, validate_commission, telemetry
from gene_annotation_episode.hpc_ledger import HPCLedger
from gene_annotation_episode.hpc_episodes import HPCEpisodes
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.domain import validate_schema
from hpc_helpers import commission, resources, recorded_queue, FIXTURES


def context(role='hpc', owner='parent'):
    assignment = {'commission_id': 'commission'}
    if role == 'hpc_prediction':
        assignment['owner_episode_id'] = owner
    identity = owner if role == 'hpc' else 'prediction'
    return BindingContext('test-run', identity, role, ((role, identity),), {'subject_refs': []}, assignment, {})


def test_live_recorded_scores_are_not_pbs_priority():
    observed = recorded_queue()
    candidate = commission()['candidates'][0]
    scores = [row['scheduler_score'] for row in observed['jobs']]
    assert all(row['priority'] == 0 for row in observed['jobs'])
    assert len(set(scores)) > 1
    target = min(observed['jobs'], key=lambda row: row['scheduler_score'])
    result = hpc_queue.features(observed, candidate, job_id=target['job_id'])
    assert result['higher_score_jobs'] == 2
    assert result['higher_pbs_priority_jobs'] == 0
    assert result['queued_jobs'] == 2
    assert result['queue_rules']['max_wall_seconds'] == 3600
    assert result['reservations']


def test_stale_activity_does_not_manufacture_queue_rank():
    jobs, queues, activity = [json.loads((FIXTURES/('aurora_'+name+'.json')).read_text())
                              for name in ('jobs', 'queues', 'activity')]
    observed = hpc_queue.snapshot(jobs, queues, activity, captured_at=activity['updated']+1000)
    assert all(row['scheduler_score'] is None for row in observed['jobs'])
    result = hpc_queue.features(observed, commission()['candidates'][0])
    assert result['higher_score_jobs'] is None
    assert result['unknown_score_jobs'] == 3
    assert observed['reservations'] is None


def test_duration_and_multi_chunk_nodes():
    assert hpc_queue.seconds('2:01:02:03') == 176523
    assert hpc_queue.seconds('168:00:00') == 604800
    assert hpc_queue.nodes({'select': '2:ncpus=8+3:ncpus=4'}) == 5
    assert hpc_queue.nodes({'select': 'host=x1+host=x2'}) == 2


def test_distribution_survival_and_density_are_conditional():
    prior = prediction.distribution(math.log1p(100), .7)
    conditioned = prediction.distribution(prior['mu'], prior['sigma'], elapsed=200)
    assert prediction.log_score(conditioned, 0, censored=True) == pytest.approx(0.)
    expected = prediction.log_score(prior, 250, censored=True)-prediction.log_score(prior, 200, censored=True)
    assert prediction.log_score(conditioned, 50, censored=True) == pytest.approx(expected)
    assert prediction.quantile(conditioned) > 0
    for elapsed in (0, 1e6, 1e10):
        d = prediction.distribution(math.log1p(100), .5, elapsed=elapsed)
        assert math.isfinite(prediction.log_score(d, 1, censored=True))
        assert prediction.probability_within(d, prediction.quantile(d)) == pytest.approx(.5)


def test_training_generalizes_and_heldout_overlap_is_rejected():
    c = commission()
    prior = prediction.prior_model(c['model'])
    trained = prediction.fit(c['model'], c['history'][:6])
    heldout = c['history'][6:]
    assert prediction.quality(trained, heldout) > prediction.quality(prior, heldout)
    small = prediction.predict(trained, {'size': 2})
    large = prediction.predict(trained, {'size': 12})
    assert prediction.quantile(large['times']['work']) > prediction.quantile(small['times']['work'])
    assert large['support']['extrapolated_features'] == ['size']
    with pytest.raises(ValueError, match='overlap'):
        prediction.quality(trained, c['history'][:1])


def test_censoring_does_not_turn_long_failure_into_fast_success():
    c = commission()
    original = prediction.prior_model(c['model'])
    censored = deepcopy(c['history'][0])
    censored.update(metrics={'work': {'seconds': 5000, 'censored': True}}, success=False)
    model = prediction.fit(c['model'], [censored])
    before = prediction.predict(original, {'size': 1})
    after = prediction.predict(model, {'size': 1})
    assert prediction.quantile(after['times']['work']) > prediction.quantile(before['times']['work'])
    assert after['success_probability'] < before['success_probability']
    assert model['metrics']['work']['censored'] == 1


def test_monitoring_conditions_and_updates_progress_without_repeated_learning():
    c = commission()
    forecast = prediction.predict(prediction.prior_model(c['model']), {'size': 1})
    original = deepcopy(forecast)
    current = {'state': 'running', 'work_elapsed_seconds': 600, 'completed_fraction': .2,
               'allocation_remaining_seconds': 60, 'peak_memory_bytes': 95, 'memory_limit_bytes': 100}
    updated = prediction.update(forecast, current)
    assert updated['times']['queue'] is None
    assert updated['overrun_probability'] > .5
    assert updated['resource_alarm'] is True
    assert prediction.update(forecast, current) == updated
    assert forecast == original


def test_credit_slots_are_fixed_and_censored_score_is_replaced(tmp_path):
    c = commission()
    ledger = HPCLedger(tmp_path, c)
    prior = prediction.predict(prediction.prior_model(c['model']), {'size': 1})
    better = deepcopy(prior)
    better['times']['queue'] = prediction.distribution(math.log1p(150), .3)
    body = {'plan_id': 'plan', 'issued_at': 10, 'prediction': better, 'reference': prior, 'elapsed': {}}
    original = ledger.freeze(body, ['original-queue'])
    ledger.freeze({**body, 'issued_at': 20, 'prediction': prior}, ['original-queue'])
    first = ledger.put('measured', {'plan_id': 'plan', 'metrics': {'queue': {'seconds': 100, 'censored': True, 'observed_at': 110}}})
    ledger.score(first)
    ledger.score(first)
    assert len(ledger.credit_view()['contributions']) == 1
    actual = ledger.put('measured', {'plan_id': 'plan', 'metrics': {'queue': {'seconds': 150, 'censored': False, 'observed_at': 160}}})
    ledger.score(actual)
    view = ledger.credit_view()
    expected = .1*(prediction.log_score(better['times']['queue'], 150)-prediction.log_score(prior['times']['queue'], 150))
    assert view['credit'] == pytest.approx(expected)
    ledger.score(first)
    assert ledger.credit_view() == view
    assert ledger.read(original)['issued_at'] == 10
    reopened = HPCLedger(tmp_path, c)
    assert reopened.credit_view() == view
    ledger.model_credit('model', -2)
    assert ledger.credit_view()['components']['model'] == -.02


def test_no_forecast_credit_after_the_event_and_no_duplicate_work_credit(tmp_path):
    c = commission()
    ledger = HPCLedger(tmp_path, c)
    value = prediction.predict(prediction.prior_model(c['model']), {'size': 1})
    ledger.freeze({'plan_id': 'plan', 'issued_at': 300, 'prediction': value, 'reference': value, 'elapsed': {}}, ['original-queue'])
    ref = ledger.put('measured', {'plan_id': 'plan', 'metrics': {'queue': {'seconds': 100, 'observed_at': 200}}})
    ledger.score(ref)
    assert ledger.credit_view()['credit'] == 0
    result = ledger.put('result', {'quality': .99})
    ledger.accept('original-work', result)
    ledger.accept('original-work', result)
    assert ledger.credit_view()['credit'] == 10
    with pytest.raises(ValueError, match='immutable'):
        HPCLedger(tmp_path, {**c, 'objective': 'different'})


def test_actual_acceptance_is_callers_predicate_not_parser_success():
    obligation = commission()['obligations']['original-work']
    assert accepts({'quality': .95}, obligation)
    assert not accepts({'quality': .8}, obligation)
    assert not accepts({'quality': True}, obligation)
    assert not accepts({'claimed_credit': 100}, obligation)


def test_episode_can_design_candidates_without_caller_job_commands(tmp_path):
    c = commission()
    candidate = c['candidates'].pop()
    candidate['files'] = [{'path': 'work.py', 'text': 'print("{allocation_workspace}")\n'}]
    candidate['preparation'] = ['Discover and prepare the actual inputs under {allocation_workspace}.']
    candidate['units'][0]['argv'] = ['python3', '{allocation_workspace}/work.py']
    binding = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
                          resources=resources(), commissions={'commission': c})
    parent = context()
    binding.initialize(parent)
    args = {'candidate_json': json.dumps(candidate)}
    result = asyncio.run(binding.execute(parent, 'hpc.candidate.propose', args, 'propose'))
    assert asyncio.run(binding.execute(parent, 'hpc.candidate.propose', args, 'propose')) == result
    ledger = binding.state(parent)
    assert ledger.commission['candidates'] == []
    assert binding._candidates(ledger) == [candidate]
    plan = build_plan(c, candidate, resources()['aurora'], {'owner': 'parent'}, 0)
    workspace = plan['manifest']['workspace']
    assert plan['manifest']['units'][0]['argv'][-1] == workspace+'/work.py'
    assert plan['files_to_stage'][-1]['text'] == 'print("'+workspace+'")\n'
    changed = {**candidate, 'wall_seconds': 1800}
    rejected = asyncio.run(binding.execute(parent, 'hpc.candidate.propose',
        {'candidate_json': json.dumps(changed)}, 'change'))
    assert rejected['status'] == 'invalid'
    assert rejected['feedback']['code'] == 'candidate_identity_is_immutable'
    assert binding._candidates(ledger) == [candidate]
    candidate['files'][0]['path'] = '../escape.py'
    with pytest.raises(ValueError, match='relative_to_allocation_workspace'):
        validate_commission({**c, 'candidates': [candidate]}, resources())


def test_hpc_provider_presentation_preserves_executable_preparation_operands():
    from gene_annotation_episode.hpc_prompt import is_hpc_context, render_hpc_prompt
    plan = build_plan(commission(), commission()['candidates'][0], resources()['aurora'], {'owner': 'parent'}, 0)
    state = {'hpc_portfolio_preparation': plan, 'execution_assignment': plan['launch_assignment'],
             'available_report_facts': {}, 'scope': {'subject_refs': []}}
    assert is_hpc_context(state)
    rendered = render_hpc_prompt(state, 'Use the original plan.')
    recovered = json.loads(rendered.split('Supplied operational operands (JSON):\n', 1)[1])
    assert recovered == state


def test_aurora_identity_when_qstat_omits_variable_list():
    import ast
    import shlex
    from gene_annotation_episode.practical_pbs_operations import _REMOTE_WORKER
    # Exercise the actual remote parser without launching or emulating SSH.
    function = next(node for node in ast.parse(_REMOTE_WORKER).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'token_matches')
    namespace = {'shlex': shlex, 'configuration': {'account': 'BioReason-Aurora-Test'}}
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<PBS identity parser>', 'exec'), namespace)
    matches = namespace['token_matches']
    ledger = {'job_name': 'original-job', 'submission_token': 'original-token',
              'submission_command': ['qsub', '-A', 'BioReason-Aurora-Test', '-v',
                                     'EPISODE_SUBMISSION_TOKEN=original-token', '/project/job.sh']}
    record = {'Job_Name': 'original-job', 'Account_Name': 'BioReason-Aurora-Test',
              'Submit_arguments': shlex.join(ledger['submission_command'][1:])}
    assert matches(record, ledger)
    assert not matches({**record, 'Submit_arguments': record['Submit_arguments'].replace('original-token', 'different')}, ledger)
    assert not matches({**record, 'Submit_arguments': record['Submit_arguments'].replace('/project/job.sh', '/other/job.sh')}, ledger)
    assert not matches({**record, 'Variable_List': {'EPISODE_SUBMISSION_TOKEN': 'different'}}, ledger)
    assert not matches({**record, 'Account_Name': 'another-account'}, ledger)


def test_plan_is_real_launch_contract_with_hashed_portfolio():
    c, r = commission(), resources()
    validate_commission(c, r)
    plan = build_plan(c, c['candidates'][0], r['aurora'], {'owner': 'parent'}, 0)
    assert plan['manifest_sha256'] == hpc_queue.digest(plan['manifest'])
    assert plan['submission_arguments']['resources'] == ['select=1', 'walltime=01:00:00', 'filesystems=flare']
    from gene_annotation_episode.practical_execution_records import validate_assignment
    validate_assignment(plan['practical_assignment'])
    from gene_annotation_episode.practical_pbs_operations import PBSPracticalOperations
    operation = PBSPracticalOperations(r['aurora'])
    operation.validate_assignment(plan['practical_assignment'])
    operation.validate_action(plan['practical_assignment'], 'practical.job.start', plan['submission_arguments'])
    from gene_annotation_episode.hpc_allocation import run
    # Even an absent manifest must fail before any local scientific work.
    with pytest.raises(RuntimeError, match='real_PBS_allocation_required'):
        run('/no/manifest', 'none')


@pytest.mark.parametrize('effort', [{'iterations': 2000000}, None, True, 0, -1, float('nan'), float('inf')])
def test_malformed_effort_is_a_repairable_validation_error(effort):
    from gene_annotation_episode.hpc_campaign import validate_commission
    value = commission()
    value['candidates'][0]['units'][0]['effort'] = effort
    with pytest.raises(ValueError, match='effort_requires_positive_finite_number'):
        validate_commission(value, resources())


def test_invalid_candidate_returns_feedback_and_can_be_repaired_without_a_job(tmp_path):
    c = commission()
    candidate = c['candidates'].pop()
    binding = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
                          resources=resources(), commissions={'commission': c})
    parent = context()
    binding.initialize(parent)
    candidate['units'][0]['effort'] = {'iterations': 2000000}
    arguments = {'candidate_json': json.dumps(candidate)}
    failed = asyncio.run(binding.execute(parent, 'hpc.candidate.propose', arguments, 'bad-proposal'))
    assert failed['status'] == 'invalid'
    assert failed['feedback']['code'] == 'work_unit_effort_requires_positive_finite_number'
    assert asyncio.run(binding.execute(parent, 'hpc.candidate.propose', arguments, 'bad-proposal')) == failed
    candidate['units'][0]['effort'] = 1.
    repaired = asyncio.run(binding.execute(parent, 'hpc.candidate.propose',
        {'candidate_json': json.dumps(candidate)}, 'repaired-proposal'))
    assert repaired['status'] == 'completed'
    assert binding.state(parent).records('handoff') == []
    assert binding.credit_view(parent, None)['credit'] == 0


def test_binding_has_real_iterative_roles_and_direct_parent_tools(tmp_path):
    binding = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
                          resources=resources(), commissions={'commission': commission()})
    EpisodeBindingRegistry([binding])
    parent = context()
    binding.initialize(parent)
    assert binding.child_roles('hpc') == ('hpc_prediction', 'hpc_execution', 'launch', 'monitor', 'results')
    assert {'hpc.monitor', 'hpc.results', 'hpc.allocation.order'} <= {row['name'] for row in binding.catalog(parent)}
    child = context('hpc_prediction')
    binding.prepare_assignment(parent, child.role, dict(child.assignment), dict(child.scope), 'prepare')
    binding.initialize(child)
    training = [row['id'] for row in commission()['history'][:6]]
    outcome = asyncio.run(binding.execute(child, 'hpc.model.fit', {'training_ids': training}, 'fit'))
    assert outcome['result']['validation_quality'] > outcome['result']['reference_quality']
    assert binding.credit_view(child, None)['credit'] > 0
    assert asyncio.run(binding.execute(child, 'hpc.model.fit', {'training_ids': training}, 'fit')) == outcome
    ledger = binding.state(parent)
    queue_ref = ledger.put('queue', {'snapshot': recorded_queue()})
    args = {'candidate_id': 'one-portfolio', 'model_ref': outcome['result']['model_ref'], 'queue_ref': queue_ref}
    plan = asyncio.run(binding.execute(parent, 'hpc.plan', args, 'plan'))
    assert plan['result']['launch_assignment']['immutable_input_versions'] == []
    assert asyncio.run(binding.execute(parent, 'hpc.plan', args, 'plan')) == plan
    another = asyncio.run(binding.execute(parent, 'hpc.plan', args, 'another-plan'))
    assert another['result']['plan_id'] != plan['result']['plan_id']
    reopened = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
                           resources=resources(), commissions={'commission': commission()})
    assert reopened.as_record() == binding.as_record()
    assert reopened.credit_view(parent, None) == binding.credit_view(parent, None)


def test_factory_roundtrip_and_binding_composition(tmp_path):
    from gene_annotation_episode.state import Store
    factory = ExecutionServiceFactory(resources(), {}, 1., 1., 1., hpc_commissions={'commission': commission()})
    assert ExecutionServiceFactory.from_record(factory.as_record()).as_record() == factory.as_record()
    with Store(tmp_path/'store') as store:
        application = factory(store, run_id='test-run', directory=tmp_path)
        descriptors = application.episode_binding_descriptors
        assert [row['binding_id'] for row in descriptors] == ['execution_episodes', 'monitor', 'hpc']
        assert {'hpc', 'hpc_prediction'} <= set(application.role_credit_bindings)
        # Actual launch schema, no fabricated transport or job.
        from gene_annotation_episode.execution_episodes import ExecutionEpisodes
        execution = ExecutionEpisodes(None, store=store, directory=tmp_path, run_id='test-run',
            resources=resources(), initial_information={}, tool_registry=None, handoff_unit=1,
            acquired_record_unit=1, log_window_bytes=8192, log_roles=('stdout', 'stderr'))
        c = commission()
        plan = build_plan(c, c['candidates'][0], resources()['aurora'], {'owner': 'parent'}, 0)
        validate_schema(plan['launch_assignment'], execution.assignment_schema('launch'))


def test_launch_receives_preparation_and_cannot_commission_duplicate_allocation(tmp_path):
    from method_loop.identities import EpisodeRef
    from gene_annotation_episode.hpc_episodes import authenticate_launch
    path = (('annotation', 'root'), ('hpc', 'campaign'))
    owner = EpisodeRef('test-run', path).episode_id
    parent = BindingContext('test-run', owner, 'hpc', path, {'subject_refs': []}, {'commission_id': 'commission'}, {})
    binding = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
                          resources=resources(), commissions={'commission': commission()})
    binding.initialize(parent)
    ledger = binding.state(parent)
    c = commission()
    plan = build_plan(c, c['candidates'][0], resources()['aurora'], ledger.read('owner'), 0)
    ledger.put('plan', plan)
    authenticate_launch(parent, plan['launch_assignment'], 'launch-once', tmp_path)
    authenticate_launch(parent, plan['launch_assignment'], 'launch-once', tmp_path)
    with pytest.raises(ValueError, match='immutable'):
        authenticate_launch(parent, plan['launch_assignment'], 'launch-again', tmp_path)
    launch_path = (*path, ('launch', 'allocation'))
    child = BindingContext('test-run', EpisodeRef('test-run', launch_path).episode_id, 'launch', launch_path,
                           parent.scope, plan['launch_assignment'], {})
    prepared = binding.initial_decision_context(child)['hpc_portfolio_preparation']
    assert prepared['files_to_stage'] == plan['files_to_stage']
    assert prepared['submission_arguments'] == plan['submission_arguments']
    ledger.put('closed', {'plan_id': plan['plan_id']})
    authenticate_launch(parent, plan['launch_assignment'], 'launch-once', tmp_path)
    with pytest.raises(ValueError, match='immutable'):
        authenticate_launch(parent, plan['launch_assignment'], 'replacement-after-close', tmp_path)


def test_plan_partial_recovery_does_not_create_another_allocation(tmp_path):
    binding = HPCEpisodes(None, store=None, run_id='test-run', directory=tmp_path,
                          resources=resources(), commissions={'commission': commission()})
    parent = context()
    binding.initialize(parent)
    ledger = binding.state(parent)
    queue_ref = ledger.put('queue', {'snapshot': recorded_queue()})
    args = {'candidate_id': 'one-portfolio', 'model_ref': 'reference_model', 'queue_ref': queue_ref}
    before = asyncio.run(binding.execute(parent, 'hpc.plan', args, 'original-plan'))
    # Only the final envelope was lost; the real plan and forecast are durable.
    with ledger.connection() as db:
        db.execute('DELETE FROM actions WHERE operation_key=?', ('original-plan',))
    after = asyncio.run(binding.execute(parent, 'hpc.plan', args, 'original-plan'))
    assert before == after
    assert len(ledger.records('plan')) == 1
    assert len(ledger.records('forecast')) == 1


def test_active_unit_progress_uses_effort_and_phase():
    from gene_annotation_episode.hpc_campaign import incorporate_progress
    c = commission()['candidates'][0]
    current = {'current_unit_id': 'unit-1', 'observed_at': 100., 'completed_fraction': 0.}
    result = incorporate_progress(current, {'unit_id': 'unit-1', 'observed_at': 80.,
        'completed_fraction': .4, 'phase': 'analysis'}, c)
    assert result['completed_fraction'] == .4
    assert result['progress_age_seconds'] == 20.
    assert current['completed_fraction'] == 0


def test_remote_worker_and_allocation_program_compile_without_execution():
    from gene_annotation_episode.practical_pbs_operations import _REMOTE_WORKER
    compile(_REMOTE_WORKER, '<actual PBS worker>', 'exec')
    path = Path(__file__).parents[1]/'gene_annotation_episode'/'hpc_allocation.py'
    compile(path.read_text(), str(path), 'exec')


def test_result_sources_require_actual_receipt_and_original_scope(tmp_path):
    from dataclasses import replace
    from gene_annotation_episode.state import Store
    with Store(tmp_path/'store') as store:
        problem = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        parent = replace(context(), scope={'subject_refs': problem['subject_refs']})
        binding = HPCEpisodes(None, store=store, run_id='test-run', directory=tmp_path,
                              resources=resources(), commissions={'commission': commission()})
        body = {'run_id': 'test-run', 'scope': dict(parent.scope), 'unit': {'finished_at': 100.},
                'document': {'quality': .95}}
        reference = binding._publish(parent, body)
        assert binding.resolve_received_reference(parent, reference, 'source') is False
        received = replace(parent, received_record_refs=(reference,))
        assert binding.resolve_received_reference(received, reference, 'source') is True
        assert binding.resolve_received_reference(replace(received, scope={'subject_refs': []}), reference, 'source') is False
        assert binding._publish(parent, body) == reference
