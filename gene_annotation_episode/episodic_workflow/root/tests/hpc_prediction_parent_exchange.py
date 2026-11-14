"""Prediction message checks with real ledgers/journals and controlled receipt ports."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import importlib
import json
import sqlite3
from types import SimpleNamespace

import pytest

from .hpc_prediction_inputs import commission, resources


class PredictionReceiptDatabase:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row

    @contextmanager
    def transaction(self):
        with self.db:
            yield

    read_snapshot = transaction

    def get(self, reference):
        raise KeyError(reference)

    def reference_subset(self, references, scope):
        return []

    def validate_scope(self, scope, *, parent_scope):
        assert scope == parent_scope
        return deepcopy(scope)


class PredictionParentExchangeChecks:
    def module(self, name):
        return importlib.import_module('gene_annotation_episode.episodic_workflow.root.' + self.axis + '.' + name)

    @pytest.fixture
    def exchange(self, tmp_path, monkeypatch):
        runtime = self.module('runtime')
        Context = self.module('episode_bindings').BindingContext
        EpisodeRef = self.module('method_loop.identities').EpisodeRef
        database = PredictionReceiptDatabase(tmp_path/'receipts.sqlite')
        journal = self.module('episode_journal').Journal(database, 'run')
        parent_type = self.module(self.parent_path.replace('/', '.')+'.episode').HPCEpisode
        child_type = self.module(self.parent_path.replace('/', '.')+'.hpc_resource_prediction.episode').HPCEpisode
        options = dict(store=database, run_id='run', directory=tmp_path,
                       resources=resources(), commissions={'commission': commission()})
        parent, child = parent_type(None, **options), child_type(None, **options)
        parent_path = (('hpc', 'parent'),)
        child_path = parent_path+(('hpc_prediction', 'child_3'),)
        scope = {'subject_refs': []}
        owner_id, child_id = [EpisodeRef('run', path).episode_id for path in (parent_path, child_path)]
        owner_assignment = {'commission_id': 'commission'}
        child_assignment = {**owner_assignment, 'owner_episode_id': owner_id}
        def context(identity, role, path, assignment):
            request = {'message': {'scope': scope, 'episode_assignment': assignment}}
            return Context('run', identity, role, path, scope, assignment, request)
        owner = context(owner_id, 'hpc', parent_path, owner_assignment)
        predicted = context(child_id, 'hpc_prediction', child_path, child_assignment)
        for value in (owner, predicted):
            journal.save('runtime_episodes', {'episode_id': value.episode_id, 'path': runtime._json(value.path),
                'request': runtime._json(value.request), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
        parent.initialize(owner)
        child.initialize(predicted)
        schema = child.decision_context(predicted, {})['hpc_report_form']
        facts = child.facts(predicted, {})
        form = {name: facts[name] for name in schema['properties']}
        child.validate_report(predicted, form, schema)
        journal.save('runtime_forms', {'episode_id': child_id, 'facts': runtime._json(facts), 'form': runtime._json(form)})
        receipts, progress, attributions, cache_reads = [], [], [], []
        cache = {'references': None}
        def recorded(records, context, admitted, contract, index):
            cache_reads.append(index)
            return cache['references']
        monkeypatch.setattr(self.module('episode_return_records').EpisodeReturnRecords,
                            'recorded_admission_references', recorded)
        provider = SimpleNamespace(receive_form=lambda *args: progress.append(args))
        source = SimpleNamespace(episode_id=owner_id, path=parent_path, scope=scope,
                                 _delivery_resolution_ref=None, request=SimpleNamespace(goal=runtime.EpisodeGoal.root(objective='Predict', result_contract={})))
        registry = self.module('episode_bindings').EpisodeBindingRegistry((parent, child))
        workflow = SimpleNamespace(store=database, journal=journal, run_id='run',
            receipts=SimpleNamespace(receive=lambda *args, **kwargs: receipts.append((args, kwargs))),
            progress_provider=provider, specialist=lambda source: parent,
            binding_context=lambda source: predicted if source.episode_id == child_id else owner,
            is_job_source=lambda source: False, native_timing_information=None, job_episodes=None,
            episode_bindings=registry, receive_tool_attributions=lambda *args, **kwargs: attributions.append((args[1], kwargs)) or [])
        value = SimpleNamespace(parent=parent, child=child, owner=owner, predicted=predicted,
            source=source, workflow=workflow, runtime=runtime, schema=schema, form=form,
            receipts=receipts, progress=progress, attributions=attributions, cache=cache, cache_reads=cache_reads,
            database=database, journal=journal, registry=registry)
        self.action(value, 3, {'kind': 'episode_child', 'role': 'hpc_prediction'})
        self.attempt(value, 3)
        try:
            yield value
        finally:
            database.db.close()

    @staticmethod
    def action(value, index, action):
        value.journal.save('runtime_actions', {'episode_id': value.owner.episode_id, 'decision_index': index,
            'action': json.dumps(action), 'result': None, 'credit': None})

    @staticmethod
    def attempt(value, index, *, child_id=None):
        value.journal.save('runtime_report_attempts', {'parent_episode_id': value.owner.episode_id,
            'decision_index': index, 'delivery_ref': 'original-delivery',
            'child_episode_id': child_id or value.predicted.episode_id,
            'contract': '{}', 'form': json.dumps(value.form), 'failure': None})

    def test_original_request_and_child_admission_preserve_selected_operands(self, exchange):
        v = exchange
        original = v.runtime._plain(v.predicted.assignment)
        prepared = v.parent.prepare_child_request(v.owner, 'hpc_prediction', original)
        admitted = v.child.prepare_assignment(v.owner, 'hpc_prediction', prepared, v.predicted.scope, 'commission')
        assert admitted == original and original == v.runtime._plain(v.predicted.assignment)
        assert v.registry.for_child(v.source.path, 'hpc_prediction') is v.child
        unrelated = {'selected': 'allocation-work'}
        assert v.parent.prepare_child_request(v.owner, 'launch', unrelated) is unrelated

    @pytest.mark.parametrize('change', [{'owner_episode_id': 'another-parent'}, {'unexpected': True}])
    def test_bad_request_rejected_before_child_initialization(self, exchange, change):
        v = exchange
        selected = {**v.runtime._plain(v.predicted.assignment), **change}
        before = v.child.state(v.predicted).records('model_entry')
        with pytest.raises((ValueError, self.module('domain').ContractError)):
            prepared = v.parent.prepare_child_request(v.owner, 'hpc_prediction', selected)
            v.child.prepare_assignment(v.owner, 'hpc_prediction', prepared, v.predicted.scope, 'invalid')
        assert v.child.state(v.predicted).records('model_entry') == before

    def test_typed_report_retains_model_and_actual_credit(self, exchange):
        v = exchange
        v.child.validate_report(v.predicted, v.form, v.schema)
        assert v.form['hpc_model_ref'] == 'reference_model'
        with pytest.raises(ValueError, match='hpc_report_disagrees_with_recorded_evidence'):
            v.child.validate_report(v.predicted, {**v.form, 'hpc_credit': 3}, v.schema)
        with pytest.raises(v.runtime.ReportBoundaryError):
            v.child.validate_report(v.predicted, {**v.form, 'hpc_model_ref': 12}, v.schema)

    def test_original_receipt_and_redelivery_do_not_reprice_prediction(self, exchange):
        v = exchange
        before = v.parent.credit_view(v.owner, None)
        assert v.runtime.Workflow._receive_form(v.workflow, v.source, v.form, v.schema, 3) == []
        self.action(v, 7, {'kind': 'redeliver_report', 'delivery_ref': 'original-delivery'})
        self.attempt(v, 7)
        assert v.runtime.Workflow._receive_form(v.workflow, v.source, v.form, v.schema, 7, redelivery=True) == []
        assert [row[-1] for row in v.progress] == ['run:'+v.owner.episode_id+':3:typed_form', 'run:'+v.owner.episode_id+':7:typed_form']
        assert [kwargs for _, kwargs in v.receipts] == [
            {'kind': 'child_form', 'source_index': 3}, {'kind': 'report_redelivery', 'source_index': 7}]
        assert v.cache_reads == [3]
        assert v.parent.credit_view(v.owner, None) == before
        assert len(v.child.state(v.predicted).records('model_entry')) == 1

    def test_recorded_admission_reuses_original_references(self, exchange):
        v = exchange
        v.cache['references'] = ['source_original_receipt']
        assert v.runtime.Workflow._receive_form(v.workflow, v.source, v.form, v.schema, 3) == ['source_original_receipt']
        assert v.progress == v.receipts == v.attributions == []
        assert v.cache_reads == [3]

    def test_redelivery_rejects_a_different_parent(self, exchange):
        v = exchange
        self.action(v, 7, {'kind': 'redeliver_report', 'delivery_ref': 'original-delivery'})
        path = (('hpc', 'different-parent'), ('hpc_prediction', 'child_3'))
        v.journal.save('runtime_episodes', {'episode_id': 'wrong-child', 'path': json.dumps(path),
            'request': '{}', 'initial_credit': 0, 'state': 'yielded', 'completion': None, 'archive': None})
        self.attempt(v, 7, child_id='wrong-child')
        with pytest.raises(v.runtime.WorkflowError, match='original_delivery_parent_conflict'):
            v.runtime.Workflow._receive_form(v.workflow, v.source, v.form, v.schema, 7, redelivery=True)
        assert v.receipts == v.progress == []

    def test_closed_model_reference_keeps_original_read_only_custody(self, exchange):
        v = exchange
        ledger = v.child.state(v.predicted)
        before = ledger.path.read_bytes()
        assert v.child.frozen_reference(v.predicted, 'reference_model', 'hpc_model') is True
        assert v.child.frozen_reference(v.predicted, 'unknown_model', 'hpc_model') is False
        assert ledger.path.read_bytes() == before
        with pytest.raises(ValueError, match='hpc_closed_original_context_conflict'):
            v.child.frozen_reference(replace(v.predicted, assignment={**v.runtime._plain(v.predicted.assignment),
                'owner_episode_id': 'another-parent'}, request={'message': {'scope': v.runtime._plain(v.predicted.scope),
                'episode_assignment': {**v.runtime._plain(v.predicted.assignment), 'owner_episode_id': 'another-parent'}}}),
                'reference_model', 'hpc_model')

    def test_other_child_keeps_original_receiving_path(self, exchange):
        v = exchange
        self.action(v, 9, {'kind': 'episode_child', 'role': 'launch'})
        assert v.runtime.Workflow._receive_form(v.workflow, v.source, {}, v.runtime._object({}), 9) == []
        assert len(v.receipts) == len(v.progress) == 1

    def test_runtime_uses_this_parents_named_prediction_receiver(self, exchange, monkeypatch):
        v = exchange
        receiver = v.parent.child_report_receiver('hpc_prediction')
        assert receiver.__module__ == v.parent.__module__.removesuffix('.episode') + '.from_child_hpc_resource_prediction'
        launch = v.parent.child_report_receiver('launch')
        if self.axis == 'a104':
            assert launch.__module__ == v.parent.__module__.removesuffix('.episode') + '.from_child_execution_job_submission'
        else:
            assert launch is None
        calls = []
        def selected(role):
            assert role == 'hpc_prediction'
            def receive(*args, **kwargs):
                calls.append((args[4], kwargs))
                return receiver(*args, **kwargs)
            return receive
        monkeypatch.setattr(v.parent, 'child_report_receiver', selected)
        v.cache['references'] = ['source_saved']
        assert v.runtime.Workflow._receive_form(v.workflow, v.source, v.form, v.schema, 3) == ['source_saved']
        assert calls == [(3, {'redelivery': False})]
        assert v.progress == v.receipts == []

    def test_only_declared_original_source_refs_enter_parent_receipts(self, exchange):
        v = exchange
        reference = 'source_'+'a'*24
        context = replace(v.predicted, received_record_refs=(reference,))
        v.child.services = SimpleNamespace(reference_in_scope=lambda ref, scope, namespace: ref == reference)
        v.child.state(context).put('result', {'source_ref': reference}, identity='controlled-original-result')
        v.database.get = lambda ref: {'id': reference, 'record_type': 'source'} if ref == reference else None
        v.database.reference_subset = lambda refs, scope: [ref for ref in refs if ref == reference]
        facts = v.child.facts(context, {})
        form = {name: facts[name] for name in v.schema['properties']}
        v.child.validate_report(context, form, v.schema)
        assert form['hpc_result_refs'] == [reference]
        before = v.parent.credit_view(v.owner, None)
        assert v.runtime.Workflow._receive_form(v.workflow, v.source, form, v.schema, 3) == [reference]
        assert v.receipts == [((v.owner.episode_id, [reference]), {'kind': 'child_form', 'source_index': 3})]
        assert v.parent.credit_view(v.owner, None) == before

    def test_runtime_commission_calls_parent_request_then_original_child_admission(self, exchange, monkeypatch):
        v = exchange
        selected = {'kind': 'episode_child', 'role': 'hpc_prediction',
            'scope': v.source.scope, 'assignment': v.runtime._plain(v.predicted.assignment),
            'goal': 'Improve the original resource predictions', 'purpose': 'Choose useful original portfolios'}
        self.action(v, 3, selected)
        events, built = [], []
        send, admit = v.parent.prepare_child_request, v.child.prepare_assignment
        def request(*args):
            events.append('parent_request')
            return send(*args)
        def admission(*args):
            events.append('child_admission')
            return admit(*args)
        monkeypatch.setattr(v.parent, 'prepare_child_request', request)
        monkeypatch.setattr(v.child, 'prepare_assignment', admission)
        child = SimpleNamespace(source=SimpleNamespace(episode_id=v.predicted.episode_id))
        def build(*args, **kwargs):
            built.append((args, kwargs))
            return child
        w = v.workflow
        w.annotation_child_roles = w.execution_binding = w.inprocess_replay = w.scientific_process_binding = None
        w.episode_branch_lifecycle = None
        w.validate_child_choice = lambda *args, **kwargs: None
        w.permits_common_action = lambda source, action: source is v.source and action == 'child'
        w._closed_child_commission = lambda *args: None
        w.expanded_contract_form = lambda *args: (v.schema, None)
        w.child_initial_report_input = lambda *args: '{}'
        w.services = SimpleNamespace(capabilities=lambda: {})
        w.launch_instructions = SimpleNamespace(materialize=lambda *args: None)
        w.build = build
        w.resolver = lambda *args, **kwargs: lambda *args: True
        monkeypatch.setattr(v.runtime, 'TimedChildUnit', lambda child, *args, **kwargs: child)
        assert v.runtime.Workflow.selected(w, v.source, selected, 3) is child
        assert events == ['parent_request', 'child_admission']
        assert built[0][0][:3] == ('hpc_prediction', 'child_3', selected['goal'])
        assert built[0][1]['episode_assignment'] == selected['assignment']
        assert built[0][1]['parent_path'] == v.source.path
        assert built[0][1]['contract'].schema == v.schema
