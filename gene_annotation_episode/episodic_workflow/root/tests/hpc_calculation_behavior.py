"""Axis calculations and private consumer custody, without remote execution."""
from copy import deepcopy
import importlib
import importlib.util
import math
from pathlib import Path

import pytest
from .hpc_prediction_inputs import commission, resources


def axis_module(axis, name):
    return importlib.import_module('gene_annotation_episode.episodic_workflow.root.'+axis+'.'+name)


def calculation_module(axis, name):
    package = 'gene_annotation_episode.episodic_workflow.root.'+axis
    selected = 'library.'+name if importlib.util.find_spec(package+'.library.'+name) else name
    return importlib.import_module(package+'.'+selected)


def completion_context(axis, episode_id, *, action_index=7, unit_index=2):
    UnitRef = axis_module(axis, 'method_loop.identities').UnitRef
    return {'version': 'completed_action_estimation_context_v5',
        'current_completion_evidence': {'version': 'completed_action_evidence_v1',
            'run_id': 'calculation-test', 'episode_id': episode_id,
            'unit_ref': UnitRef(episode_id, unit_index).as_record(),
            'original_decision_index': action_index, 'action_kind': 'tool',
            'received_record_refs': [], 'received_progress_refs': [],
            'progress_records': [], 'child_return': None, 'unavailable_reasons': []}}


class HpcCalculationChecks:
    def test_measured_resources_improve_fixed_disjoint_quality(self):
        p, c = calculation_module(self.axis, 'hpc_prediction'), commission()
        original = deepcopy(c)
        model, prior = p.fit(c['model'], c['history'][:6]), p.prior_model(c['model'])
        assert p.quality(model, c['history'][6:]) > p.quality(prior, c['history'][6:])
        small, large = [p.predict(model, {'size': size}) for size in (2, 12)]
        for metric in ('cpu_seconds', 'memory_bytes'):
            assert p.quantile(small['resources'][metric]) < p.quantile(large['resources'][metric])
        assert large['support']['extrapolated_features'] == ['size']
        with pytest.raises(ValueError, match='training_validation_overlap'):
            p.quality(model, c['history'][:1])
        assert c == original

    def test_conditional_survival_quantiles_preserve_censored_information(self):
        p = calculation_module(self.axis, 'hpc_prediction')
        value = p.distribution(math.log1p(100), .5, elapsed=200)
        points = [p.quantile(value, probability) for probability in (.1, .5, .9)]
        assert 0 < points[0] < points[1] < points[2]
        for point, probability in zip(points, (.1, .5, .9)):
            assert p.probability_within(value, point) == pytest.approx(probability)
            assert math.exp(p.log_score(value, point, censored=True)) == pytest.approx(1-probability)
        c = commission()
        row = deepcopy(c['history'][0])
        row['metrics']['work']['censored'] = True
        model = p.fit(c['model'], [row])
        assert model['metrics']['work']['censored'] == 1
        assert model['metrics']['work']['observations'] == 1

    def test_original_physical_attempt_cannot_train_under_two_record_ids(self):
        p, c = calculation_module(self.axis, 'hpc_prediction'), commission()
        original = deepcopy(c['history'][0])
        original['provenance'] = ['123.aurora-pbs-0001.example']
        with pytest.raises(ValueError, match='one_training_case_per_physical_attempt'):
            p.fit(c['model'], [original, {**original, 'id': 'another-record'}])

    def test_accounting_units_and_missing_usage_do_not_become_allocation_capacity(self):
        r = calculation_module(self.axis, 'hpc_resource_prediction')
        observation = {'state': 'running', 'observed_at': '2026-11-04T17:53:00+00:00',
            'native': {'pbs_fields': {'Resource_List': {'ncpus': 208},
                'resources_used': {'cput': '00:00:24', 'mem': '123kb'}}}}
        measured = r.pbs_resource_metrics(observation)
        assert measured['cpu_seconds']['value'] == 24
        assert measured['memory_bytes']['value'] == 123*1024
        assert all(row['censored'] for row in measured.values())
        observation['state'] = 'completed'
        assert not r.pbs_resource_metrics(observation)['cpu_seconds']['censored']
        observation['native']['pbs_fields']['resources_used'] = {}
        assert r.pbs_resource_metrics(observation) == {}
        with pytest.raises(ValueError, match='resource_measurement_unit_conflict'):
            r.measured_value('memory_bytes', {'unit': 'cpu_seconds', 'value': 1})

    def test_resource_forecast_changes_portfolio_value_without_execution_gate(self):
        p, c = calculation_module(self.axis, 'hpc_prediction'), commission()
        forecast = p.predict(p.fit(c['model'], c['history'][:6]), {'size': 4})
        small = deepcopy(c['candidates'][0])
        small['resource_capacity'] = {'cpu_threads': 2, 'memory_bytes': 1024**2}
        large = {**small, 'resource_capacity': {'cpu_threads': 16, 'memory_bytes': 8*1024**3}}
        a, b = [p.compare(candidate, forecast, c['obligations'], c['preferences']) for candidate in (small, large)]
        assert a['expected_actual_credit'] < b['expected_actual_credit']
        assert a['resource_estimates']['memory_fit_probability'] < b['resource_estimates']['memory_fit_probability']
        assert 'allowed' not in a and 'allowed' not in b
        unknown = p.compare(c['candidates'][0], forecast, c['obligations'], c['preferences'])
        assert unknown['resource_estimates']['memory_fit_probability'] is None

    def test_conditioning_uses_original_forecast_without_repeated_precision(self):
        p, c = calculation_module(self.axis, 'hpc_prediction'), commission()
        initial = p.predict(p.prior_model(c['model']), {'size': 1})
        original = deepcopy(initial)
        observation = {'state': 'running', 'work_elapsed_seconds': 100., 'completed_fraction': .25,
            'peak_memory_bytes': 8*1024**3, 'cpu_seconds': 400.}
        updated = p.update(initial, observation)
        assert updated == p.update(initial, observation) and initial == original
        assert updated['resources']['memory_bytes']['elapsed'] == observation['peak_memory_bytes']
        assert updated['resources']['cpu_seconds']['elapsed'] == 400.

    def test_shared_monitor_valuation_retains_possible_success_and_zero_wait_credit(self):
        p, c = calculation_module(self.axis, 'hpc_prediction'), commission()
        monitoring = axis_module(self.axis, 'hpc_monitoring')
        candidate = c['candidates'][0]
        candidate['wall_seconds'] = 600
        value = p.predict(p.prior_model(c['model']), {'size': 1})
        value = p.update(value, {'state': 'queued', 'observed_at': 100.,
            'queue_elapsed_seconds': 20., 'work_elapsed_seconds': 0.})
        value['times']['setup'] = p.distribution(math.log1p(30), 16.2773)
        value['times']['work'] = p.distribution(math.log1p(120), 16.2773)
        assert p.quantile(value['times']['setup']) > candidate['wall_seconds']
        compared = p.compare(candidate, value, c['obligations'], c['preferences'])
        upper = p.probability_within(value['times']['setup'], 600)*value['success_probability']
        assert 0 < compared['attainable_units'][0]['completion_probability'] < upper
        for now in (100., 5001.):
            selected = monitoring.choose_schedule(value, candidate, c, monitoring.DEFAULT_POLICY, now=now)
            assert selected['schedule'] and selected['expected_continuation_credit'] > 0
            assert selected['earned_wait_credit'] == 0


class HpcCalculationConnectionChecks:
    def setup(self, tmp_path):
        module = lambda name: axis_module(self.axis, name)
        c = commission()
        options = dict(store=None, run_id='calculation-test', directory=tmp_path,
            resources=resources(), commissions={'commission': c})
        parent_path = self.binding_path if self.role == 'hpc' else self.binding_path.rsplit('/', 1)[0]
        parent = module(parent_path.replace('/', '.')+'.episode').HPCEpisode(None, **options)
        binding = parent if self.role == 'hpc' else module(self.binding_path.replace('/', '.')+'.episode').HPCEpisode(None, **options)
        Context = module('episode_bindings').BindingContext
        owner = Context('calculation-test', 'owner', 'hpc', (('hpc', 'owner'),),
            {'subject_refs': []}, {'commission_id': 'commission'}, {})
        context = owner if self.role == 'hpc' else Context('calculation-test', self.role, self.role,
            owner.path+((self.role, self.role),), owner.scope,
            {'commission_id': 'commission', 'owner_episode_id': owner.episode_id}, {})
        parent.initialize(owner)
        binding.initialize(context)
        return c, binding, context

    def test_consumer_initialization_uses_same_axis_model_and_ledger_scorer(self, tmp_path, monkeypatch):
        c, binding, context = self.setup(tmp_path)
        p = calculation_module(self.axis, 'hpc_prediction')
        called, original = [], p.prior_model
        def prior(specification):
            called.append(specification)
            return original(specification)
        monkeypatch.setattr(p, 'prior_model', prior)
        binding.initialize(context)
        assert called == [c['model']]
        assert axis_module(self.axis, 'hpc_ledger').log_score is p.log_score
        assert binding.state(context).read('reference_model') == original(c['model'])

    @pytest.mark.parametrize('bound', [False, True])
    def test_private_estimator_authenticates_own_ledger_and_preserves_signed_history(self, tmp_path, bound):
        _, binding, context = self.setup(tmp_path)
        numerical = axis_module(self.axis, 'numerical')
        ledger = binding.state(context)
        body = {'run_id': context.run_id, 'episode_id': context.episode_id,
            'operation_key': f'{context.run_id}:{context.episode_id}:7',
            'active_history_indices': [0, 1], 'active_credit_ceiling': 0.,
            'expected_continuation_credit': 2.}
        if bound:
            body.update(pending_action='collect', valuation={'value_kind': 'unresolved_acceptance_upper_bound'})
        ref = ledger.put('continuation', body, identity='original-continuation')
        packet = completion_context(self.axis, context.episode_id)
        packet['hpc_continuation'] = {'reference': ref, 'evidence': body}
        history, contexts = (0., -.25, 10.), (None, None, packet)
        before = deepcopy(contexts)
        callback = binding.practical_estimator(context).with_continuation_cost(.001)
        estimate = callback(history, numerical.YieldParameters(), contexts)
        assert estimate.diagnostics['active_next_gain']['value'] == 0
        assert estimate.diagnostics['activity_mode'] == ('collect' if bound else 'wait')
        assert estimate.diagnostics['pending_expected_credit'] == (None if bound else 2.)
        assert estimate.expected_next_gain.lower == (0. if bound else 2.)
        assert estimate.expected_next_gain.upper == 2.
        assert contexts == before and ledger.credit_view()['credit'] == 0
        packet['hpc_continuation']['evidence'] = {**body, 'expected_continuation_credit': 3.}
        with pytest.raises(ValueError, match='hpc_continuation_identity_conflict'):
            callback(history, numerical.YieldParameters(), contexts)

    def test_unbound_completed_observations_keep_original_controller_replay(self, tmp_path):
        _, binding, context = self.setup(tmp_path)
        numerical = axis_module(self.axis, 'numerical')
        original = numerical.YieldController('original', 0., .001)
        restored = numerical.YieldController('original', 0., .001, estimate_with_context=binding.practical_estimator(context))
        for value in (0., 0., -.125, .25):
            assert original.observe('action', value).as_record() == restored.observe('action', value).as_record()

    def test_private_consumer_selects_relocated_estimator_and_preserves_configuration(self, tmp_path):
        c, binding, context = self.setup(tmp_path)
        expected = axis_module(self.axis, 'library.hpc_continuation').HPCContinuationEstimator
        callback = binding.practical_estimator(context)
        assert type(callback) is expected
        assert type(callback.with_continuation_cost(.013)) is expected
        assert callback.with_continuation_cost(.013).cost == .013 and callback.cost == 0
        assert binding.as_record()['configuration'] == {'resources': resources(), 'commissions': {'commission': c}}
