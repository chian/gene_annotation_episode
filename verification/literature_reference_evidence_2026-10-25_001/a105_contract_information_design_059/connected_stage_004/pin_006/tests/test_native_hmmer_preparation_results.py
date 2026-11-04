"""R1 boundary operations over retained native bytes and explicit runtime fixtures.

These tests execute bounded retained-data grading/projection workers. The native
producer already ran in267/270; ownership and observation are synthetic fixtures.
They do not run method_loop or claim a new live HMMER execution.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
from types import MethodType, SimpleNamespace

import pytest

from gene_annotation_episode import native_hmmer_preparation_acquisition as acquisition
from gene_annotation_episode import native_hmmer_preparation_result_publication as publication
from gene_annotation_episode import native_hmmer_preparation_results as results_module
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.native_hmmer_preparation_returns import NativeHmmerPreparationReturns
from gene_annotation_episode.numerical import NumericBand, YieldParameters
from gene_annotation_episode.practical_yield import PracticalYieldEstimator
from gene_annotation_episode.state import Store
from test_practical_yield import completion_context
from test_native_hmmer_preparation_acquisition import RETAINED, synthetic_custody
from test_native_hmmer_preparation_returns import (
    SavedReturns, schema_for, selector, FACT_SOURCES, REFERENCE_SOURCE, ROWS,
    ARTIFACTS, POPULATION, FAILURES, GENERIC, COMPLETE,
)


class NativeBoundaryFixture(SavedReturns):
    def __init__(self, store, tmp_path, monkeypatch, *, selected=None, sources=None,
                 program='hmmemit', mode='consensus_simple', retained_plan=None):
        self.store, self.run_id = store, 'capture270-synthetic'
        self.journal, self.receipts = Journal(store, self.run_id), EpisodeReceipts(store, self.run_id)
        self.scope = {'subject_refs': store.create_problem(raw_sequence='ACGTACGTACGT', molecule='dna')['subject_refs']}
        with monkeypatch.context() as scoped:
            self.native_root, self.plan, self.bundle, target = synthetic_custody(
                tmp_path, scoped, program, mode, retained_plan=retained_plan)
        monkeypatch.setattr(acquisition, 'local_hmmer_preparation_plan', lambda *a: deepcopy(self.plan))
        handoff = self.source('explicit-native-handoff-fixture')
        target.update(handle=handoff, scope=deepcopy(self.scope))
        self.target, self.observations = target, 0

        def read_target(reference, scope):
            assert reference == handoff
            store.validate_scope(target['scope'], parent_scope=plain(scope))
            return deepcopy(target)

        def observe_target(selected_target, *, operation_key):
            assert selected_target == target
            self.observations += 1
            # Explicit native-state fixture. Real observed success is root's
            # integration responsibility, not inferred from an artifact path.
            return {'state': 'completed' if self.bundle['returncode'] == 0 else 'failed',
                'returncode': self.bundle['returncode'], 'observed_at': '2026-10-26T00:00:00Z'}

        self.owner = SimpleNamespace(store=store, run_id=self.run_id, directory=tmp_path / 'run',
            resources={target['resource_id']: {'policy': self.plan['policy']}},
            job_progress_provider=SimpleNamespace(targets=SimpleNamespace(
                read_target=read_target, observe_target=observe_target)),
            acquired_record_unit=2, handoff_unit=3)
        self.owner._target = lambda context: read_target(context.assignment['handoff_ref'], context.scope)
        self.owner._result_directory = MethodType(ExecutionEpisodes._result_directory, self.owner)
        self.owner._selected_result_action = MethodType(ExecutionEpisodes._selected_result_action, self.owner)
        self.results = results_module.NativeHmmerPreparationResults(self.owner)
        self.owner.native_hmmer_preparation_results = self.results
        self.boundary = NativeHmmerPreparationReturns(self.owner)
        self.owner.native_hmmer_preparation_returns = self.boundary
        self.root = self.context((('annotation', 'root'),), {}, None)
        selected = selected or selector('calculations', ('length',), ('consensus_length',),
            artifacts=[{'direction': 'output', 'role': 'generated_sequences', 'ordinal': 0}])
        schema = schema_for(*(sources or (*FACT_SOURCES, REFERENCE_SOURCE, COMPLETE)))
        self.child_context = self.child(self.root, schema)
        assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': handoff, 'selector': selected}
        request = plain(self.child_context.request)
        request['message']['episode_assignment'] = assignment
        self.child_context = replace(self.child_context, assignment=assignment, request=request)
        store.db.execute('UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?',
            (canonical(request), self.run_id, self.child_context.episode_id))
        action = json.loads(self.journal.row('runtime_actions', self.root.episode_id, 0)['action'])
        action['assignment'] = assignment
        store.db.execute('UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0',
            (canonical(action), self.run_id, self.root.episode_id))
        self.schema = schema

    def execute(self, index=0, tool='execution.results.collect'):
        child = self.child_context
        self.journal.save('runtime_actions', {'episode_id': child.episode_id, 'decision_index': index,
            'action': canonical({'kind': 'tool', 'tool': tool, 'arguments': {}}), 'result': None, 'credit': None})
        key = f'{self.run_id}:{child.episode_id}:{index}'
        outcome = asyncio.run(self.results.execute(child, self.target, tool, {}, key))
        self.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
            (canonical(outcome), self.run_id, child.episode_id, index))
        self.receipts.receive(child.episode_id, outcome['record_refs'], kind='own_action', source_index=index)
        return outcome

    def record_path(self, body, name='receipt.json'):
        return self.results._saved_directory(body['episode_id'], body['operation_key']) / name


def no_new_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Replay or return validation attempted original work')
    monkeypatch.setattr(publication, 'run_local_job', forbidden)
    monkeypatch.setattr(acquisition, 'local_hmmer_preparation_plan', forbidden)
    monkeypatch.setattr(acquisition, '_capture_file', forbidden)
    monkeypatch.setattr('gene_annotation_episode.native_hmmer_preparation_worker.grade_hmmer_preparation', forbidden)
    monkeypatch.setattr('gene_annotation_episode.native_hmmer_preparation_worker.recalculate_hmmer_preparation', forbidden)
    return forbidden


def test_native_numerical_return_exact_completion_credit_and_unchanged_replay(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        case = NativeBoundaryFixture(store, tmp_path, monkeypatch)
        outcome = case.execute()
        body, child = outcome['result'], case.child_context
        assert body['complete'], body['failures']
        assert any(q['path'] == 'length' and q['value'] == 12 and q['state'] == 'present'
            for row in body['rows'] for q in row['quantities'])
        assert body['population']['requested_artifact_count'] == 1
        assert body['population']['returned_artifact_count'] >= 1
        full = store.get_artifact
        numerical = {body['prepared'][k] for k in ('grading_artifact_ref', 'sheet_artifact_ref', 'calculations_artifact_ref')}
        def compact_only(reference):
            assert reference not in numerical, 'Host hydrated a full numerical artifact'
            return full(reference)
        monkeypatch.setattr(store, 'get_artifact', compact_only)
        proof = case.results.completion(child)
        assert proof['operation_key'] == body['operation_key']
        selection = {'known_record_refs': body['record_refs'], 'initial_known_record_refs': []}
        assert case.results.credit_view(child, selection)['credit'] == 2
        assert case.results.credit_view(child, {'known_record_refs': body['record_refs'],
            'initial_known_record_refs': [body['source_ref']]})['credit'] == 0
        form = case.returned(case.root, child)
        assert case.boundary.record_admission(case.root, form, case.schema, case.operation(case.root)) == body['record_refs']
        assert validate_form(form, case.schema, lambda ref, ns: case.boundary.resolve_received(case.root, ref, ns)) == form
        forbidden = no_new_work(monkeypatch)
        shutil.rmtree(case.native_root.parent)
        before = list(store.db.iterdump())
        replay = asyncio.run(case.results.execute(child, case.target, body['tool_name'], {}, body['operation_key']))
        assert replay == outcome and case.observations == 1
        assert case.results.read_result(body['source_ref'], child.scope) == body
        assert case.boundary.received_facts(case.root, case.schema)[ROWS] == body['rows']
        assert list(store.db.iterdump()) == before
        # Exact-zero estimator uses the existing practical proof path without
        # inventing a zero completed action. The controller itself is not run.
        estimator = PracticalYieldEstimator(lambda saved: saved == proof, base_estimate=forbidden)
        original = completion_context(run_id=case.run_id, episode_id=child.episode_id, action_index=0)
        original['practical_completion'].update(proof)
        estimate = estimator([2], YieldParameters(8, 4), [original])
        assert estimate.expected_next_gain == NumericBand.exact(0)
        assert store.count('observation') == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


def test_status_has_no_acquisition_or_credit_and_later_collect_remains_selected(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        case = NativeBoundaryFixture(store, tmp_path, monkeypatch)
        original = results_module.capture_local_bundle
        monkeypatch.setattr(results_module, 'capture_local_bundle', lambda *a, **k: pytest.fail('status captured data'))
        outcome = case.execute(tool='execution.results.status')
        assert outcome['result']['capture'] is None and not outcome['record_refs']
        assert case.results.completion(case.child_context) is None
        assert case.results.credit_view(case.child_context, {'known_record_refs': [], 'initial_known_record_refs': []})['credit'] == 0
        monkeypatch.setattr(results_module, 'capture_local_bundle', original)
        assert case.execute(1)['result']['complete']
        assert case.observations == 2


def test_duplicate_bundle_selections_have_one_acquisition_unit(tmp_path, monkeypatch):
    selected = selector('calculations', ('length',), keys=['unavailable-original-key'])
    with Store(tmp_path / 'store') as store:
        case = NativeBoundaryFixture(store, tmp_path, monkeypatch, selected=selected)
        first, second = case.execute(), case.execute(1)
        assert not first['result']['complete'] and not second['result']['complete']
        assert first['result']['capture']['bundle_artifact_ref'] == second['result']['capture']['bundle_artifact_ref']
        known = list(dict.fromkeys(first['record_refs'] + second['record_refs']))
        assert case.results.credit_view(case.child_context, {'known_record_refs': known,
            'initial_known_record_refs': []})['new_acquired_record_count'] == 1
        assert len(case.results.facts(case.child_context)[POPULATION]) == 1


@pytest.mark.parametrize('numerical_requested', [False, True])
def test_artifact_only_endpoint_does_not_depend_on_unrequested_grading(tmp_path, monkeypatch, numerical_requested):
    selected = selector('calculations', ('length',), projection=numerical_requested,
        artifacts=[{'direction': 'output', 'role': 'generated_sequences', 'ordinal': 0}])
    worker = publication._execute_worker
    def injected_grading_failure(store, directory, plan, policy):
        if plan['task'] == 'grade':
            return {}, [{'stage': 'grading', 'code': 'native_hmmer_preparation_fixture_grading_failed', 'record_key': None}], False, {
                'worker_receipt_artifact_ref': store.artifact(canonical({'fixture_failure': 'grade'})), 'artifacts': []}
        return worker(store, directory, plan, policy)
    monkeypatch.setattr(publication, '_execute_worker', injected_grading_failure)
    with Store(tmp_path / 'store') as store:
        case = NativeBoundaryFixture(store, tmp_path, monkeypatch, selected=selected)
        body = case.execute()['result']
        assert body['complete'] is (not numerical_requested)
        assert not body['prepared']['graded']
        assert any(r['code'] == 'native_hmmer_preparation_fixture_grading_failed' for r in body['failures'])
        if not numerical_requested:
            assert len(body['artifacts']) == 1 and body['population']['missing_artifacts'] == []
            assert case.results.completion(case.child_context)
        else:
            assert case.results.completion(case.child_context) is None
        no_new_work(monkeypatch)
        assert case.results.read_result(body['source_ref'], case.scope) == body


def test_actual_native_partial_conversion_preserves_output_and_failure(tmp_path, monkeypatch):
    choice = selector('output_records', ('length',), artifacts=[{'direction': 'output', 'role': 'converted_models', 'ordinal': 0}])
    with Store(tmp_path / 'store') as store:
        case = NativeBoundaryFixture(store, tmp_path, monkeypatch, selected=choice,
            retained_plan=RETAINED / 'test_actual_conversion_failure0/plan.json')
        body = case.execute()['result']
        assert case.bundle['returncode'] == 1 and not body['complete']
        assert len(body['rows']) == 1 and body['rows'][0]['quantities'][0]['value'] == 12
        assert body['artifacts']
        facts = case.results.facts(case.child_context)
        native = [r for r in facts[FAILURES] if r['code'] == 'native_hmmer_preparation_nonzero_returncode']
        assert len(native) == 1 and native[0]['stage'] == 'execution' and native[0]['affected'] is None
        form = case.returned(case.root, case.child_context)
        case.boundary.record_admission(case.root, form, case.schema, case.operation(case.root))
        assert case.boundary.received_facts(case.root, case.schema)[ROWS] == body['rows']


@pytest.mark.parametrize('change', ['scope', 'assignment', 'operation', 'quantity', 'population', 'source', 'failure', 'completion'])
def test_changed_result_receipts_and_source_records_reject(tmp_path, monkeypatch, change):
    with Store(tmp_path / 'store') as store:
        case = NativeBoundaryFixture(store, tmp_path, monkeypatch)
        outcome = case.execute()
        original, body = outcome['result'], deepcopy(outcome['result'])
        if change == 'scope': body['scope'] = {'subject_refs': []}
        elif change == 'assignment': body['assignment']['selector']['projection']['rows']['limit'] += 1
        elif change == 'operation': body['tool_name'] = 'execution.results.status'
        elif change == 'quantity': body['rows'][0]['quantities'][0]['value'] = 999
        elif change == 'population': body['population']['total_records'] += 1
        elif change == 'failure': body['failures'].append({'stage': 'grading', 'code': 'forged', 'record_key': None})
        elif change == 'completion': body['complete'] = False
        else:
            source = store.get(body['source_ref'])
            source['text_ref'] = source['artifact_ref']
            store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(source), body['source_ref']))
        case.record_path(original).write_text(canonical(body))
        outcome['result'] = body
        store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0',
            (canonical(outcome), case.run_id, case.child_context.episode_id))
        no_new_work(monkeypatch)
        with pytest.raises(ValueError):
            case.results.read_result(original['source_ref'], case.scope)


def test_unrequested_auxiliary_artifact_denied_without_full_data_read(tmp_path, monkeypatch):
    selected = selector(projection=False, artifacts=[{'direction': 'output', 'role': 'converted_models', 'ordinal': 0}])
    with Store(tmp_path / 'store') as store:
        case = NativeBoundaryFixture(store, tmp_path, monkeypatch, selected=selected,
            program='hmmconvert', mode='binary', sources=(REFERENCE_SOURCE,))
        body = case.execute()['result']
        case.returned(case.root, case.child_context)
        source = store.get(body['source_ref'])
        hidden = next(ref for ref in source['auxiliary_artifact_refs'] if ref not in body['record_refs'])
        monkeypatch.setattr(store, 'get_artifact', lambda *a: pytest.fail('membership hydrated an artifact'))
        for context in (case.root, case.child_context):
            assert case.results.retained_reference_access(context, hidden, 'artifact') is False
            assert case.results.retained_reference_access(context, body['artifacts'][0]['artifact_ref'], 'artifact') is True
        assert source['text_ref'] is None


def test_arbitrary_grading_exception_text_stays_separate_and_native_failure_survives(tmp_path, monkeypatch):
    selected = selector('output_records', ('length',))
    def failed(*a, **kw):
        raise OSError('Cannot read private /tmp/sensitive/result file')
    monkeypatch.setattr(results_module, 'prepare_native_hmmer_preparation_grading', failed)
    with Store(tmp_path / 'store') as store:
        case = NativeBoundaryFixture(store, tmp_path, monkeypatch, selected=selected,
            retained_plan=RETAINED / 'test_actual_conversion_failure0/plan.json')
        body = case.execute()['result']
        facts = case.results.facts(case.child_context)[FAILURES]
        assert any(r['code'] == 'native_hmmer_preparation_retained_grading_unavailable' for r in facts)
        assert any(r['code'] == 'native_hmmer_preparation_nonzero_returncode' for r in facts)
        assert 'sensitive' not in canonical(body)
        assert 'sensitive' in case.record_path(body, 'operational-diagnostics.json').read_text()
        no_new_work(monkeypatch)
        assert case.results.read_result(body['source_ref'], case.scope) == body


def test_initial_facts_allow_unsaved_construction_but_execute_requires_original(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        case = NativeBoundaryFixture(store, tmp_path, monkeypatch)
        child = case.child_context
        store.db.execute('DELETE FROM runtime_episodes WHERE run_id=? AND episode_id=?', (case.run_id, child.episode_id))
        assert case.results.facts(child)[GENERIC] == []
        assert case.results.credit_view(child, {'known_record_refs': [], 'initial_known_record_refs': []})['credit'] == 0
        with pytest.raises(ValueError, match='saved_context_required'):
            case.execute()
        request = plain(child.request)
        request['message']['episode_assignment'] = {}
        with pytest.raises(ValueError, match='context_conflict'):
            case.results.facts(replace(child, request=request))


def test_unavailable_manifest_is_a_typed_source_less_partial_acquisition(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        case = NativeBoundaryFixture(store, tmp_path, monkeypatch)
        (case.native_root / 'bundle.json').unlink()
        outcome = case.execute()
        body = outcome['result']
        assert not body['complete'] and body['source_ref'] is None and body['record_refs'] == []
        assert not body['capture']['bundle_validated'] and body['capture']['bundle_artifact_ref'] is None
        facts = case.results.facts(case.child_context)
        assert facts[FAILURES] == [{'handoff_ref': case.target['handle'], 'source_ref': None,
            'stage': 'capture', 'code': 'native_hmmer_preparation_sealed_bundle_unavailable',
            'record_key': None, 'affected': None}]
        form = case.returned(case.root, case.child_context)
        assert case.boundary.record_admission(case.root, form, case.schema, case.operation(case.root)) == [case.target['handle']]
        no_new_work(monkeypatch)
        assert asyncio.run(case.results.execute(case.child_context, case.target, body['tool_name'], {}, body['operation_key'])) == outcome
