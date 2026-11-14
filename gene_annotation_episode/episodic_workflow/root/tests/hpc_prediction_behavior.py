"""Prediction custody and mathematics checks using recorded inputs, without SSH."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from importlib import import_module
import json
from pathlib import Path
import sqlite3
import time

import pytest

from .hpc_prediction_inputs import commission, resources, recorded_queue


class PredictionBehavior:
    def module(self, name):
        return import_module('gene_annotation_episode.episodic_workflow.root.' + self.axis + '.' + name)

    def setup(self, tmp_path, *, heldout=True):
        c = commission()
        if not heldout:
            c['validation_ids'] = []
        parent_type = self.module(self.binding_path.rsplit('/', 1)[0].replace('/', '.') + '.episode').HPCEpisode
        child_type = self.module(self.binding_path.replace('/', '.') + '.episode').HPCEpisode
        options = dict(store=None, run_id='test-run', directory=tmp_path,
                       resources=resources(), commissions={'commission': c})
        parent, child = parent_type(None, **options), child_type(None, **options)
        Context = self.module('episode_bindings').BindingContext
        owner = Context('test-run', 'parent', 'hpc', (('hpc', 'parent'),),
                        {'subject_refs': []}, {'commission_id': 'commission'}, {})
        context = Context('test-run', 'prediction', 'hpc_prediction',
                          owner.path + (('hpc_prediction', 'prediction'),), owner.scope,
                          {'commission_id': 'commission', 'owner_episode_id': 'parent'}, {})
        parent.initialize(owner)
        child.initialize(context)
        return c, parent, child, owner, context

    def execute(self, child, context, tool, arguments, identity):
        return asyncio.run(child.execute(context, tool, arguments, identity))

    def test_private_identity_and_permitted_work(self, tmp_path):
        _, _, child, _, context = self.setup(tmp_path)
        assert child.binding_path == self.binding_path
        assert child.roles == ('hpc_prediction',)
        assert child.child_roles(context.role) == ()
        assert child.permitted_common_actions(context) == ('tool',)
        assert {row['name'] for row in child.catalog(context)} == {
            'hpc.read', 'hpc.compare', 'hpc.discovery.run', 'hpc.candidate.propose',
            'hpc.queue.observe', 'hpc.model.fit'}
        with pytest.raises(ValueError, match='tool_not_available_to_hpc_role'):
            self.execute(child, context, 'hpc.plan', {}, 'not-executed')
        assert child.state(context).records('action_intent') == []

    def test_assignment_authenticates_original_commissioning_parent(self, tmp_path):
        _, _, child, owner, context = self.setup(tmp_path)
        assert child.prepare_assignment(owner, context.role, context.assignment, context.scope, 'commission') == context.assignment
        with pytest.raises(ValueError, match='must_belong_to_its_original_hpc_parent'):
            child.prepare_assignment(replace(owner, episode_id='different'), context.role,
                                     context.assignment, context.scope, 'wrong-parent')
        with pytest.raises(ValueError, match='unknown_hpc_role'):
            child.assignment_schema('hpc_execution')

    def test_child_opens_only_existing_parent_ledger_and_checks_scope(self, tmp_path):
        _, parent, child, owner, context = self.setup(tmp_path)
        assert child.state(context).path == parent.state(owner).path
        wrong = replace(context, assignment={**context.assignment, 'owner_episode_id': 'absent'})
        with pytest.raises(sqlite3.OperationalError):
            child.state(wrong)
        assert len(list((tmp_path/'hpc').iterdir())) == 1
        with pytest.raises(ValueError, match='sister_scope_must_equal_original_parent_scope'):
            child.state(replace(context, scope={'subject_refs': ['different']}))

    def test_training_resume_and_completed_replay_preserve_entry(self, tmp_path):
        c, _, child, _, context = self.setup(tmp_path)
        ledger = child.state(context)
        entry = ledger.read('entry:' + context.episode_id)
        arguments = {'training_ids': [row['id'] for row in c['history'][:6]]}
        first = self.execute(child, context, 'hpc.model.fit', arguments, 'original-fit')
        assert first['status'] == 'completed'
        assert first['result']['model_ref'] != entry['model_ref']
        child.initialize(context)
        assert ledger.read('entry:' + context.episode_id) == entry
        assert self.execute(child, context, 'hpc.model.fit', arguments, 'original-fit') == first
        assert len(ledger.records('model_choice')) == 1
        assert len(ledger.records('action_intent')) == 1
        assert child._current_model(ledger) == first['result']['model_ref']
        quality = first['result']['validation_quality'] - entry['quality']
        assert quality > 0
        assert child.credit_view(context, None)['credit'] == pytest.approx(c['credit']['model_scale'] * quality)
        assert child.credit_view(context, None)['actual_job_credit_counted_here'] is False

    @pytest.mark.parametrize('tool,arguments', [
        ('hpc.read', {'reference': 'absent'}),
        ('hpc.compare', {'model_ref': 'reference_model', 'queue_ref': 'resource:wrong-kind'}),
        ('hpc.candidate.propose', {'candidate_json': '{broken'})])
    def test_invalid_return_is_saved_under_original_action(self, tmp_path, tool, arguments):
        _, _, child, _, context = self.setup(tmp_path)
        before = child.credit_view(context, None)
        first = self.execute(child, context, tool, arguments, 'original-invalid')
        assert first['status'] == 'invalid'
        assert self.execute(child, context, tool, arguments, 'original-invalid') == first
        assert len(child.state(context).records('action_intent')) == 1
        assert child.credit_view(context, None) == before

    def test_fixed_validation_cannot_be_training(self, tmp_path):
        c, _, child, _, context = self.setup(tmp_path)
        with pytest.raises(ValueError, match='training_ids_must_be_original_nonvalidation_cases'):
            self.execute(child, context, 'hpc.model.fit', {'training_ids': c['validation_ids']}, 'leaked-validation')
        assert child.state(context).records('model_choice') == []

    def test_candidate_identity_remains_immutable(self, tmp_path):
        c, _, child, _, context = self.setup(tmp_path)
        candidate = deepcopy(c['candidates'][0])
        candidate['id'] = 'alternative'
        arguments = {'candidate_json': json.dumps(candidate)}
        assert self.execute(child, context, 'hpc.candidate.propose', arguments, 'new-candidate')['status'] == 'completed'
        candidate['nodes'] = 2
        rejected = self.execute(child, context, 'hpc.candidate.propose',
                                {'candidate_json': json.dumps(candidate)}, 'changed-candidate')
        assert rejected['status'] == 'invalid'
        assert rejected['feedback']['code'] == 'candidate_identity_is_immutable'
        assert len(child.state(context).records('candidate')) == 1

    def test_continuation_uses_available_evidence_and_new_data_reopens(self, tmp_path):
        c, _, child, _, context = self.setup(tmp_path, heldout=False)
        ledger = child.state(context)
        assert child.continuation_for_action(context, 'before-training') is None
        fitted = self.execute(child, context, 'hpc.model.fit',
                              {'training_ids': [row['id'] for row in c['history']]}, 'fit-all')
        observed = recorded_queue(self.module('hpc_queue'))
        observed['captured_at'] = time.time()
        ledger.put('queue', {'snapshot': observed}, identity='recorded-queue')
        assert child.continuation_for_action(context, 'before-comparison') is None
        compared = self.execute(child, context, 'hpc.compare',
            {'model_ref': fitted['result']['model_ref'], 'queue_ref': 'recorded-queue'}, 'compare-current')
        assert compared['status'] == 'completed'
        ready = child.continuation_for_action(context, 'ready')
        assert ready['evidence']['active_credit_ceiling'] == 0
        assert ready['evidence']['comparison_operation'] == 'compare-current'
        assert ledger.read(ready['reference']) == ready['evidence']
        assert child.credit_view(context, None)['credit'] == 0
        new = deepcopy(c['history'][0])
        new.update(id='later-measured-allocation', observed_at=time.time())
        ledger.put('shared_history', {'observations': [new]}, identity='later-history')
        assert child.continuation_for_action(context, 'reopened') is None
        trained = self.execute(child, context, 'hpc.model.fit',
                              {'training_ids': [new['id']]}, 'later-fit')
        assert trained['result']['validation_quality'] is None
        assert child.credit_view(context, None)['credit'] == 0

    def test_model_math_preserves_measured_resource_demand(self, tmp_path):
        c, _, _, _, _ = self.setup(tmp_path)
        p = self.module('library.hpc_prediction')
        model = p.fit(c['model'], c['history'][:6])
        assert p.quality(model, c['history'][6:]) > p.quality(p.prior_model(c['model']), c['history'][6:])
        small, large = [p.predict(model, {'size': size}) for size in (2, 12)]
        for metric in ('cpu_seconds', 'memory_bytes'):
            assert p.quantile(small['resources'][metric]) < p.quantile(large['resources'][metric])
        assert large['support']['extrapolated_features'] == ['size']

    def test_report_preserves_actual_model_and_credit(self, tmp_path):
        _, _, child, _, context = self.setup(tmp_path)
        summary = child.decision_context(context, {})
        facts = child.facts(context, {})
        form = {key: facts[key] for key in ('hpc_credit', 'hpc_model_ref', 'hpc_result_refs')}
        child.validate_report(context, form, summary['hpc_report_form'])
        with pytest.raises(ValueError, match='hpc_report_disagrees_with_recorded_evidence'):
            child.validate_report(context, {**form, 'hpc_credit': 1}, summary['hpc_report_form'])
        assert summary['hpc_available_training_ids'] == ['measurement-' + str(i) for i in range(1, 7)]

    def test_saved_description_config_and_prediction_goal(self, tmp_path):
        c, _, child, _, context = self.setup(tmp_path)
        record = child.as_record()
        assert record['binding_id'] == self.binding_path
        assert record['configuration'] == {'resources': resources(), 'commissions': {'commission': c}}
        assert len(record['implementation_sha256']) == 64
        assert 'fixed reference and validation set cannot change' in child.instructions(context)
        assert 'Unknown inputs stay unknown' in child.instructions(context)
