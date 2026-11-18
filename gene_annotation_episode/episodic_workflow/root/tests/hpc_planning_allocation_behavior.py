"""Private HPC planning/allocation behavior using retained operands and local ledgers."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import importlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from .hpc_prediction_inputs import commission, resources, recorded_queue
from .axis_roles import HEAD, CLASS, axis_of


class PlanningAllocationBehavior:
    def module(self, name):
        return importlib.import_module('gene_annotation_episode.episodic_workflow.root.'+self.axis+'.'+name)

    def setup(self, tmp_path, *, monitoring=False, supplied=None):
        c = deepcopy(supplied) if supplied is not None else commission()
        if monitoring:
            c['monitoring'] = dict(self.module('hpc_monitoring').DEFAULT_POLICY)
        parent_path = self.binding_path if self.role == 'hpc' else self.binding_path.rsplit('/', 1)[0]
        parent_type = self.module(parent_path.replace('/', '.')+'.episode').HPCEpisode
        selected_type = self.module(self.binding_path.replace('/', '.')+'.episode').HPCEpisode
        options = dict(store=None, run_id='test-run', directory=tmp_path,
            resources=resources(), commissions={'commission': c})
        parent = parent_type(None, **options)
        selected = parent if self.role == 'hpc' else selected_type(None, **options)
        Context = self.module('episode_bindings').BindingContext
        EpisodeRef = self.module('method_loop.identities').EpisodeRef
        head = HEAD[self.axis]
        path = ((head, 'science'), ('hpc', 'parent')) if parent_path.startswith(head + '/') else (('annotation', 'root'), ('hpc', 'parent'))
        owner = Context('test-run', EpisodeRef('test-run', path).episode_id, 'hpc', path,
            {'subject_refs': []}, {'commission_id': 'commission'}, {})
        child_path = path+(('hpc_execution', 'allocation'),)
        context = owner if self.role == 'hpc' else Context('test-run', EpisodeRef('test-run', child_path).episode_id,
            'hpc_execution', child_path, owner.scope,
            {'commission_id': 'commission', 'owner_episode_id': owner.episode_id}, {})
        parent.initialize(owner)
        selected.initialize(context)
        return SimpleNamespace(c=c, parent=parent, binding=selected, owner=owner, context=context,
            ledger=selected.state(context), parent_path=parent_path)

    def execute(self, value, tool, arguments, key):
        return asyncio.run(value.binding.execute(value.context, tool, arguments, key))

    def plan(self, value):
        q = self.module('hpc_queue')
        ref = value.ledger.put('queue', {'snapshot': recorded_queue(q)})
        args = {'candidate_id': value.c['candidates'][0]['id'], 'model_ref': 'reference_model', 'queue_ref': ref}
        return self.execute(value, 'hpc.plan', args, 'original-plan'), args

    def test_original_role_actions_children_and_binding_identity(self, tmp_path):
        v = self.setup(tmp_path)
        assert v.binding.binding_path == self.binding_path and v.binding.roles == (self.role,)
        expected = ('hpc_prediction', 'hpc_execution', 'launch', 'monitor', 'results') if self.role == 'hpc' else ('launch', 'monitor', 'results')
        assert v.binding.child_roles(self.role) == expected
        assert v.binding.permitted_common_actions(v.context) == ('tool', 'child', 'wait', 'redeliver_report')
        names = {row['name'] for row in v.binding.catalog(v.context)}
        assert {'hpc.plan', 'hpc.handoff', 'hpc.monitor', 'hpc.monitor.wait', 'hpc.results', 'hpc.allocation.order'} <= names
        assert 'hpc.model.fit' not in names
        with pytest.raises(ValueError, match='tool_not_available_to_hpc_role'):
            self.execute(v, 'hpc.model.fit', {'training_ids': []}, 'not-acquired')
        assert not v.ledger.records('action_intent')
        assert v.binding.as_record()['configuration'] == {'resources': resources(), 'commissions': {'commission': v.c}}

    def test_monitor_policy_keeps_existing_wait_action_selection(self, tmp_path):
        v = self.setup(tmp_path, monitoring=True)
        assert v.binding.permitted_common_actions(v.context) == ('tool', 'child', 'redeliver_report')
        assert 'hpc.monitor.wait' in {r['name'] for r in v.binding.catalog(v.context)}

    def test_assignment_and_shared_ledger_preserve_original_owner(self, tmp_path):
        v = self.setup(tmp_path)
        assert v.binding.state(v.context).path == v.parent.state(v.owner).path
        if self.role == 'hpc_execution':
            assert v.binding.prepare_assignment(v.owner, self.role, v.context.assignment, v.context.scope, 'request') == v.context.assignment
            with pytest.raises(ValueError, match='must_belong_to_its_original_hpc_parent'):
                v.binding.prepare_assignment(replace(v.owner, episode_id='different'), self.role, v.context.assignment, v.context.scope, 'wrong')
            with pytest.raises(ValueError, match='sister_scope_must_equal_original_parent_scope'):
                v.binding.state(replace(v.context, scope={'subject_refs': ['changed']}))
        else:
            requester = replace(v.owner, role='annotation', path=(('annotation', 'root'),), assignment={})
            assert v.binding.prepare_assignment(requester, self.role, v.context.assignment, v.context.scope, 'request') == v.context.assignment
            with pytest.raises(ValueError, match='hpc_commission_source_not_received_by_parent'):
                v.binding.prepare_assignment(requester, self.role, {'commission_source_ref': 'source_absent'}, v.context.scope, 'wrong')

    @pytest.mark.parametrize('tool,arguments', [('hpc.read', {'reference': 'absent'}),
        ('hpc.compare', {'model_ref': 'reference_model', 'queue_ref': 'wrong-resource'}),
        ('hpc.candidate.propose', {'candidate_json': '{broken'})])
    def test_invalid_executed_result_keeps_identity_replay_and_zero_credit(self, tmp_path, tool, arguments):
        v = self.setup(tmp_path)
        before = v.binding.credit_view(v.context, None)
        outcome = self.execute(v, tool, arguments, 'original-invalid')
        assert outcome['status'] == 'invalid'
        assert self.execute(v, tool, arguments, 'original-invalid') == outcome
        assert len(v.ledger.records('action_intent')) == 1
        assert v.binding.credit_view(v.context, None) == before

    def test_plan_partial_replay_preserves_forecast_manifest_and_allocation(self, tmp_path):
        v = self.setup(tmp_path)
        first, arguments = self.plan(v)
        assert first['status'] == 'completed'
        saved = v.ledger.read(first['result']['plan_ref'])
        assert saved['manifest_sha256'] == self.module('hpc_queue').digest(saved['manifest'])
        assert saved['original_prediction'] == self.module('library.hpc_prediction').predict(
            v.ledger.read('reference_model'), saved['original_prediction']['features'])
        with v.ledger.connection() as db:
            db.execute('DELETE FROM actions WHERE operation_key=?', ('original-plan',))
        assert self.execute(v, 'hpc.plan', arguments, 'original-plan') == first
        assert len(v.ledger.records('plan')) == 1
        assert all(r['body']['plan_id'] == saved['plan_id'] for r in v.ledger.records('forecast'))
        assert v.binding.credit_view(v.context, None)['credit'] == 0

    def test_launch_reservation_and_supplied_inputs_keep_original_plan(self, tmp_path):
        v = self.setup(tmp_path)
        outcome, _ = self.plan(v)
        plan = v.ledger.read(outcome['result']['plan_ref'])
        prefix = self.binding_path.replace('/', '.')
        endpoint = prefix+'.to_child_execution_job_submission'
        selected = endpoint if importlib.util.find_spec('gene_annotation_episode.episodic_workflow.root.'+self.axis+'.'+endpoint) else prefix+'.requests'
        authenticate = self.module(selected).authenticate_launch
        authenticate(v.context, plan['launch_assignment'], 'launch-once', tmp_path)
        authenticate(v.context, plan['launch_assignment'], 'launch-once', tmp_path)
        with pytest.raises(ValueError, match='immutable'):
            authenticate(v.context, plan['launch_assignment'], 'another-action', tmp_path)
        path = v.context.path+(('launch', 'original-launch'),)
        context = replace(v.context, role='launch', path=path, assignment=plan['launch_assignment'])
        supplied = v.binding.initial_decision_context(context)['hpc_execution_job']
        assert supplied['plan_id'] == plan['plan_id']
        assert supplied['scientific_manifest'] == plan['manifest']
        assert json.loads(Path(supplied['supplied_input_file']).read_text()) == plan
        v.ledger.put('closed', {'plan_id': plan['plan_id']})
        authenticate(v.context, plan['launch_assignment'], 'launch-once', tmp_path)
        with pytest.raises(ValueError, match='immutable'):
            authenticate(v.context, plan['launch_assignment'], 'replacement', tmp_path)

    def test_missing_handoff_returns_original_repair_without_relaunch(self, tmp_path):
        v = self.setup(tmp_path)
        outcome, _ = self.plan(v)
        args = {'plan_ref': outcome['result']['plan_ref']}
        failed = self.execute(v, 'hpc.results', args, 'original-results')
        assert failed['status'] == 'invalid'
        assert failed['feedback']['code'] == 'original_handoff_not_attached'
        assert 'redeliver_report' in failed['feedback']['recovery']
        assert self.execute(v, 'hpc.results', args, 'original-results') == failed
        assert not v.ledger.records('launch_commission') and not v.ledger.records('result')

    def test_missing_monitor_controller_preserves_repair_and_original_credit(self, tmp_path, monkeypatch):
        v = self.setup(tmp_path)
        outcome, _ = self.plan(v)
        plan = v.ledger.read(outcome['result']['plan_ref'])
        v.ledger.put('handoff', {'plan_id': plan['plan_id']})
        monkeypatch.setattr(v.binding, '_target', lambda *a: {'execution_id': 'original-job'})
        args = {'plan_ref': outcome['result']['plan_ref']}
        failed = self.execute(v, 'hpc.monitor.wait', args, 'original-wait')
        assert failed['status'] == 'invalid' and failed['feedback']['code'] == 'hpc_monitor_controller_not_attached'
        assert self.execute(v, 'hpc.monitor.wait', args, 'original-wait') == failed
        assert not v.ledger.records('monitor_schedule') and not v.ledger.records('monitor_wake')
        assert v.binding.credit_view(v.context, None)['credit'] == 0

    @pytest.mark.parametrize('state', ['pending', 'partial', 'collected'])
    def test_original_ready_results_keep_unresolved_credit_separate(self, tmp_path, monkeypatch, state):
        current = json.loads((Path(__file__).parent/'fixtures/hpc/completed-unit-before-pbs-finish.json').read_text())['telemetry']
        c = commission()
        c['candidates'][0]['units'][0]['unit_id'] = 'scientific_result'
        if state == 'partial':
            c['obligations']['other-work'] = deepcopy(c['obligations']['original-work'])
            c['candidates'][0]['units'].append({**c['candidates'][0]['units'][0], 'unit_id': 'other-unit', 'obligation_id': 'other-work'})
            current.update(state='running', phase='R', completed_fraction=.5, current_unit_id='other-unit')
        v = self.setup(tmp_path, supplied=c)
        p = self.module('library.hpc_prediction')
        original = p.predict(p.prior_model(c['model']), {'size': 10})
        plan = {'plan_id': 'pending-original', 'candidate_id': c['candidates'][0]['id'], 'original_prediction': original}
        v.ledger.put('plan', plan)
        v.ledger.put('forecast', {'plan_id': plan['plan_id'], 'issued_at': 100.})
        v.ledger.put('monitor', {'plan_id': plan['plan_id'], 'forecast_ref': 'observed-original', 'conditional_prediction': p.update(original, current)})
        monitoring = self.module('hpc_monitoring')
        monitoring.MonitorCronController(v.ledger).attach(plan, 'original-job', monitoring.DEFAULT_POLICY)
        if state == 'collected':
            v.ledger.put('result', {'plan_id': plan['plan_id'], 'unit': {'unit_id': 'scientific_result'}, 'document': {'quality': .1}})
        import time
        monkeypatch.setattr(time, 'time', lambda: current['observed_at'])
        evidence = v.binding.continuation_for_action(v.context, 'test-run:ready:0')['evidence']
        assert v.binding.credit_view(v.context, None)['credit'] == evidence['earned_wait_credit'] == 0
        if state == 'collected':
            assert evidence.get('pending_action') != 'collect' and evidence['expected_continuation_credit'] == 0
        else:
            assert evidence['pending_action'] == 'collect'
            assert evidence['pending_by_obligation']['original-work'] == 10
            if state == 'partial': assert 0 < evidence['pending_by_obligation']['other-work'] <= 10
            else: assert evidence['expected_continuation_credit'] == 10

    def test_accepted_obligation_is_shared_once_and_closes_only_attainable_value(self, tmp_path):
        v = self.setup(tmp_path)
        ref = v.ledger.put('result', {'accepted': True})
        v.ledger.accept('original-work', ref)
        v.ledger.accept('original-work', ref)
        assert v.binding.credit_view(v.context, None)['credit'] == 10
        assert v.parent.credit_view(v.owner, None)['credit'] == 10
        evidence = v.binding.continuation_for_action(v.context, 'test-run:accepted:0')['evidence']
        assert evidence['expected_continuation_credit'] == evidence['active_credit_ceiling'] == 0
        assert evidence['reason'] == 'original_obligations_accepted'

    @pytest.mark.parametrize('case', ['accepted', 'rejected', 'changed_result', 'wrong_allocation', 'running_monitor'])
    def test_observed_allocation_retains_original_bytes_acceptance_and_replay(self, tmp_path, monkeypatch, case):
        import base64
        import hashlib
        import time
        v = self.setup(tmp_path)
        outcome, _ = self.plan(v)
        plan_ref = outcome['result']['plan_ref']
        plan = v.ledger.read(plan_ref)
        candidate = v.c['candidates'][0]
        unit = candidate['units'][0]
        v.ledger.put('handoff', {'plan_id': plan['plan_id'], 'handoff_ref': 'original-handoff', 'job_id': 'original-job'})
        target = {'execution_id': 'original-job', 'resource_id': 'aurora', 'assignment': plan['practical_assignment']}
        monkeypatch.setattr(v.binding, '_target', lambda *a: target)
        document = {'quality': .95 if case != 'rejected' else .1}
        payload = json.dumps(document).encode()
        now = time.time()+1
        result_path = plan['manifest']['workspace']+'/units/'+unit['unit_id']+'/result.json'
        allocation = {'plan_id': 'wrong-plan' if case == 'wrong_allocation' else plan['plan_id'],
            'job_id': 'original-job', 'manifest_sha256': plan['manifest_sha256'],
            'started_at': now-15, 'finished_at': None if case == 'running_monitor' else now-1,
            'updated_at': now, 'current_unit_id': unit['unit_id'] if case == 'running_monitor' else None,
            'units': [{'unit_id': unit['unit_id'], 'obligation_id': unit['obligation_id'],
                'state': 'running' if case == 'running_monitor' else 'complete', 'returncode': 0,
                'result_path': result_path, 'finished_at': now-1,
                'result_sha256': hashlib.sha256(b'changed' if case == 'changed_result' else payload).hexdigest()}]}
        files = {plan['manifest']['workspace']+'/allocation-status.json': json.dumps(allocation).encode(), result_path: payload}
        reads, observations, published = [], [], []
        def read_file(actual_target, *, path, offset, limit, operation_key):
            assert actual_target == target and offset == 0
            reads.append((path, operation_key))
            value = files[path][:limit]
            return {'size_bytes': len(value), 'bytes_base64': base64.b64encode(value).decode()}
        def observe_target(actual_target, *, operation_key):
            assert actual_target == target
            observations.append(operation_key)
            return {'observed_at': now, 'state': 'running' if case == 'running_monitor' else 'completed',
                'native': {'pbs_fields': {'qtime': now-30, 'stime': now-20,
                    'job_state': 'R' if case == 'running_monitor' else 'F',
                    'resources_used': {'cput': '00:00:24', 'mem': '123kb'}}}}
        v.binding._targets = SimpleNamespace(read_file=read_file, observe_target=observe_target)
        def publish(ctx, body):
            assert ctx == v.context and body['job_id'] == 'original-job'
            published.append(body)
            return 'source_original_result'
        monkeypatch.setattr(v.binding, '_publish', publish)
        tool = 'hpc.monitor' if case == 'running_monitor' else 'hpc.results'
        arguments = {'plan_ref': plan_ref, **({'refresh_queue': False} if tool == 'hpc.monitor' else {})}
        if case in ('changed_result', 'wrong_allocation'):
            message = 'result_changed_since_unit_completion' if case == 'changed_result' else 'allocation_receipt_identity_conflict'
            with pytest.raises(ValueError, match=message): self.execute(v, tool, arguments, 'observe-original')
            assert published == [] and v.binding.credit_view(v.context, None)['credit'] == 0
            assert not v.ledger.records('result')
            return
        actual = self.execute(v, tool, arguments, 'observe-original')
        before = (list(reads), list(observations), list(published))
        assert self.execute(v, tool, arguments, 'observe-original') == actual
        assert (reads, observations, published) == before
        assert len(observations) == 1
        if case == 'running_monitor':
            assert actual['result']['conditional_prediction']['telemetry']['state'] == 'running'
            assert actual['result']['measured_ref'] == v.ledger.records('measured')[-1]['id']
            assert not v.ledger.records('result') and published == []
            assert v.binding.credit_view(v.context, None)['credit'] == 0
        else:
            assert actual['record_refs'] == ['source_original_result']
            assert published[0]['document'] == document
            assert len(v.ledger.records('result')) == len(v.ledger.records('closed')) == 1
            assert v.binding.credit_view(v.context, None)['credit'] == (10 if case == 'accepted' else 0)
            assert bool(actual['result']['accepted']) == (case == 'accepted')
            if case == 'rejected': assert actual['result']['rejected'][0]['reason'] == 'original_acceptance_predicate_not_met'
