"""Masking host/return contracts over saved native bytes and controlled custody.

Native fixtures are612's retained outputs. Their new owner/plan/observations here
are explicitly synthetic protocol fixtures, not a new native run or Workflow.
Deterministic preparation/projection use the actual bounded worker publisher.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
from types import MethodType, SimpleNamespace

import pytest

from gene_annotation_episode import native_blast_masking_acquisition as acquisition
from gene_annotation_episode import native_blast_masking_results as host
from gene_annotation_episode import native_blast_masking_result_publication as publication
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.native_blast_masking_contracts import (
    BUNDLE_VERSION, OWNER_NAME, compile_native_blast_masking_job, generated_statistics_binding,
    native_environment, producer_failure, requested_job_from_native_blast_masking, staged_relative,
    validate_original_bundle,
)
from gene_annotation_episode.native_blast_masking_returns import NativeBLASTMaskingReturns
from gene_annotation_episode.sequence_masking_result_views import FACT_SOURCES, masking_fact_sources
from gene_annotation_episode.state import Store
from test_native_blast_masking_invocation import FIXTURES, job_for, pin, plan_for, target_for
from test_native_hmmer_preparation_returns import SavedReturns


def selector(*, quantities=('masked_positions', 'masked_fraction'), artifacts=(), saved_data=(), records=None):
    return {'version': 'native_blast_masking_result_selector_v1', 'mode': 'native_result',
        'records': {'mode': 'all'} if records is None else {'mode': 'selected', 'entries': [
            {'operand_role': 'sequences', 'operand_ordinal': 0, 'record_ordinal': r} for r in records]},
        'quantities': list(quantities), 'statistics_fields': [], 'statistics_unit_codes': [],
        'include_checks': True, 'artifacts': list(artifacts), 'saved_sheet_ref': None,
        'saved_data': list(saved_data)}


def schema_for(*sources):
    descriptors, properties = masking_fact_sources(), {}
    for index, source in enumerate(sources):
        value = (deepcopy(descriptors[source]['report_schema']) if source in descriptors else
            {'type': 'boolean', 'x-source': source} if source == 'execution_completed' else
            {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference',
                'x-reference-namespace': 'execution_result'}, 'x-source': source})
        properties['selected_' + str(index)] = value
    return {'type': 'object', 'additionalProperties': False, 'properties': properties, 'required': list(properties)}


def retained_protocol_fixture(tmp_path, program, mode, *, failure=False):
    """Create synthetic owner/plan custody around byte-identical612 originals."""
    plan = plan_for(tmp_path, program, mode)
    job = plan['requested_job']['native_blast_masking']
    root = Path(plan['attempt_directory'])
    root.mkdir(parents=True)
    inputs = []
    for operand in job['operands']:
        relative = staged_relative(operand)
        destination = root / relative
        destination.parent.mkdir(exist_ok=True)
        destination.write_bytes(Path(operand['path']).read_bytes())
        inputs.append({key: operand[key] for key in ('role', 'ordinal', 'format', 'artifact_ref')} | {
            'original_path': operand['path'], 'relative_path': relative,
            **{prefix + key: operand[key] for prefix in ('expected_', 'staged_', 'final_')
                for key in ('sha256', 'size_bytes')}})
    filename = 'windowmasker_counts.ascii' if mode == 'create_counts' else program + '_interval.txt'
    artifacts = []
    for selected in job['outputs']:
        path = root / selected['relative_path']
        path.write_bytes((FIXTURES / 'outputs' / filename).read_bytes() if selected['role'] in {'mask', 'statistics'}
            else b'synthetic protocol stdout\n' if selected['role'] == 'stdout' else b'synthetic protocol stderr\n')
        artifacts.append({**selected, 'ordinal': 0, **pin(path)})
    bundle = {'version': BUNDLE_VERSION, 'identity': deepcopy(plan['identity']),
        'requested_job': deepcopy(plan['requested_job']), 'operation': deepcopy(job['operation']),
        'software': {'executable': job['software']['executable'], 'expected_sha256': job['software']['sha256'],
            'actual_sha256': job['software']['sha256'], 'declared_engine_version': job['software']['engine_version']},
        'realized_argv': compile_native_blast_masking_job(job,
            input_paths={r['role']: str(root / staged_relative(r)) for r in job['operands']}, output_directory=str(root)),
        'environment': native_environment(job, root), 'inputs': inputs, 'operand_bindings': [],
        'statistics_binding': deepcopy(job['statistics_binding']), 'returncode': 1 if failure else 0,
        'artifacts': artifacts, 'failures': [producer_failure('nonzero_returncode')] if failure else [],
        'started_at': '2026-10-28T00:00:00+00:00', 'finished_at': '2026-10-28T00:00:01+00:00'}
    if mode == 'create_counts' and not failure:
        bundle['statistics_binding'] = generated_statistics_binding(bundle)
    validate_original_bundle(bundle, plan)
    (root / OWNER_NAME).write_text(canonical(plan))
    (root / 'bundle.json').write_text(canonical(bundle))
    return plan, bundle, target_for(plan)


class HostCase(SavedReturns):
    def __init__(self, store, tmp_path, monkeypatch, *, selected=None, sources=None,
                 program='dustmasker', mode='mask', failure=False):
        self.store, self.run_id = store, 'invocation615'
        self.journal, self.receipts = Journal(store, self.run_id), EpisodeReceipts(store, self.run_id)
        self.scope = {'subject_refs': store.create_problem(raw_sequence='ACGTACGT', molecule='dna')['subject_refs']}
        self.plan, self.bundle, target = retained_protocol_fixture(tmp_path, program, mode, failure=failure)
        self.native_root = Path(self.plan['attempt_directory'])
        monkeypatch.setattr(acquisition, 'local_blast_masking_plan', lambda *a: deepcopy(self.plan))
        data = store.artifact(canonical({'synthetic_handoff': self.plan['identity']}))
        handoff = store.put('source', {'provider': 'explicit_protocol_fixture', 'accession': None,
            'uri': None, 'artifact_ref': data, 'text_ref': None, 'request_ref': None,
            'version': 'fixture_v1', 'retrieved_at': '2026-10-28T00:00:00+00:00'}, origin='tool')['id']
        target.update(handle=handoff, scope=deepcopy(self.scope))
        self.target, self.observations = target, 0

        def read_target(reference, scope):
            assert reference == handoff
            store.validate_scope(target['scope'], parent_scope=plain(scope))
            return deepcopy(target)

        def observe_target(received, *, operation_key):
            assert received == target
            self.observations += 1
            return {'state': 'failed' if failure else 'completed', 'returncode': self.bundle['returncode'],
                'observed_at': '2026-10-28T00:00:02+00:00'}

        self.owner = SimpleNamespace(store=store, run_id=self.run_id, directory=tmp_path / 'run',
            resources={target['resource_id']: {'policy': self.plan['policy']}}, acquired_record_unit=2, handoff_unit=3,
            job_progress_provider=SimpleNamespace(targets=SimpleNamespace(read_target=read_target, observe_target=observe_target)))
        self.owner._target = lambda context: read_target(context.assignment['handoff_ref'], context.scope)
        self.owner._result_directory = MethodType(ExecutionEpisodes._result_directory, self.owner)
        self.owner._selected_result_action = MethodType(ExecutionEpisodes._selected_result_action, self.owner)
        self.results = host.NativeBLASTMaskingResults(self.owner)
        self.owner.native_blast_masking_results = self.results
        self.boundary = NativeBLASTMaskingReturns(self.owner)
        self.owner.native_blast_masking_returns = self.boundary
        self.root = self.context((('annotation', 'root'),), {}, None)
        self.receipts.receive(self.root.episode_id, [handoff, *self.scope['subject_refs']], kind='initial')
        self.schema = schema_for(*(sources or (*FACT_SOURCES, 'execution_result_refs', 'execution_completed')))
        self.child_context = self.result_child(selected or selector())

    def result_child(self, selected, *, parent=None, index=0, schema=None):
        parent = self.root if parent is None else parent
        schema = self.schema if schema is None else schema
        child = self.child(parent, schema, index=index)
        assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': self.target['handle'], 'selector': selected}
        request = plain(child.request)
        request['message']['episode_assignment'] = assignment
        child = replace(child, assignment=assignment, request=request)
        self.store.db.execute('UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?',
            (canonical(request), self.run_id, child.episode_id))
        action = json.loads(self.journal.row('runtime_actions', parent.episode_id, index)['action'])
        action['assignment'] = assignment
        self.store.db.execute('UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=?',
            (canonical(action), self.run_id, parent.episode_id, index))
        return child

    def execute(self, *, child=None, index=0, tool='execution.results.collect'):
        child = self.child_context if child is None else child
        self.journal.save('runtime_actions', {'episode_id': child.episode_id, 'decision_index': index,
            'action': canonical({'kind': 'tool', 'tool': tool, 'arguments': {}}), 'result': None, 'credit': None})
        key = f'{self.run_id}:{child.episode_id}:{index}'
        outcome = asyncio.run(self.results.execute(child, self.target, tool, {}, key))
        self.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
            (canonical(outcome), self.run_id, child.episode_id, index))
        self.receipts.receive(child.episode_id, outcome['record_refs'], kind='own_action', source_index=index)
        return outcome

    def admit(self, child=None, parent=None):
        child, parent = child or self.child_context, parent or self.root
        form = self.returned(parent, child)
        index = int(child.path[-1][1].removeprefix('child_'))
        schema = plain(child.request)['report_contract']['measurements']['schema']
        refs = self.boundary.record_admission(parent, form, schema,
            f'{self.run_id}:{parent.episode_id}:{index}:typed_form')
        self.receipts.receive(parent.episode_id, refs, kind='child_form', source_index=index)
        return form, refs


def forbidden(*args, **kwargs):
    raise AssertionError('saved replay started new native/worker/acquisition work')


def test_exact_numerical_returns_custody_credit_and_frozen_replay(tmp_path, monkeypatch):
    choice = selector(artifacts=[{'direction': 'output', 'role': 'mask', 'ordinal': 0}], saved_data=['sheet'])
    with Store(tmp_path / 'store') as store:
        case = HostCase(store, tmp_path, monkeypatch, selected=choice)
        outcome = case.execute()
        body = outcome['result']
        assert body['complete'], body['failures']
        assert [row['value']['value'] for row in body['quantities'] if row['quantity'] == 'masked_positions'] == [80, 0, 72]
        components = json.loads(store.get_artifact(body['prepared']['calculations_artifact_ref']))
        by_key = {row['record_key']: row for row in components['records']}
        assert all(row['value'] == by_key[row['record_key']][row['quantity']] for row in body['quantities'])
        assert case.results.credit_view(case.child_context, {'known_record_refs': body['record_refs'],
            'initial_known_record_refs': []})['credit'] == 2
        proof = case.results.completion(case.child_context)
        assert proof['operation_key'] == body['operation_key']
        form, refs = case.admit()
        assert refs == body['record_refs']
        assert validate_form(form, case.schema,
            lambda ref, ns: case.boundary.resolve_received(case.root, ref, ns)) == form
        assert case.boundary.received_facts(case.root, case.schema)['execution.masking_status'] == [body['status']]
        monkeypatch.setattr(publication, 'run_local_job', forbidden)
        monkeypatch.setattr(acquisition, 'local_blast_masking_plan', forbidden)
        monkeypatch.setattr(acquisition, '_capture_file', forbidden)
        shutil.rmtree(case.native_root.parent)
        before = list(store.db.iterdump())
        replay = asyncio.run(case.results.execute(case.child_context, case.target, body['tool_name'], {}, body['operation_key']))
        assert replay == outcome and case.observations == 1
        assert case.results.read_result(body['source_ref'], case.scope) == body
        assert case.results.retained_target(case.child_context) == case.target
        assert case.boundary.received_facts(case.root, case.schema)['execution.masking_quantities'] == body['quantities']
        assert list(store.db.iterdump()) == before
        assert store.count('observation') == 0


def test_source_only_return_does_not_grant_auxiliary_or_derived_data(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        case = HostCase(store, tmp_path, monkeypatch, selected=selector(quantities=()), sources=['execution_result_refs'])
        body = case.execute()['result']
        form, refs = case.admit()
        assert refs == [body['source_ref']]
        hidden = [body['prepared'][key] for key in ('sheet_artifact_ref', 'source_grading_artifact_ref', 'calculations_artifact_ref')]
        hidden += [row['artifact_ref'] for row in body['prepared']['occurrences'] if row['role'] not in {'stdout', 'stderr'}]
        known = set(case.receipts.known(case.root.episode_id))
        for ref in hidden:
            assert ref not in known
            assert case.boundary.resolve_received(case.root, ref, 'artifact') is None
            assert case.results.retained_reference_access(case.root, ref, 'artifact') is not True
        assert case.boundary.received_facts(case.root, schema_for(*FACT_SOURCES)) == {s: [] for s in FACT_SOURCES}


def test_requested_saved_sheet_authorizes_next_child_recalculation_without_acquisition(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        case = HostCase(store, tmp_path, monkeypatch, selected=selector(saved_data=['sheet']))
        original = case.execute()['result']
        case.admit()
        sheet = original['prepared']['sheet_artifact_ref']
        choice = selector(records=[1], saved_data=['calculations'])
        choice.update(mode='saved_recalculation', saved_sheet_ref=sheet)
        assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': case.target['handle'], 'selector': choice}
        assert case.results.validate_selected_inputs(case.root, assignment) == [case.target['handle'], sheet]
        assert case.results.retained_target(case.root, assignment=assignment, scope=case.scope) == case.target
        child = case.result_child(choice, index=1)
        assert case.results.validate_selected_inputs(child, assignment) == [case.target['handle'], sheet]
        monkeypatch.setattr(host, 'prepare_native_blast_masking_result', forbidden)
        monkeypatch.setattr(acquisition, 'local_blast_masking_plan', forbidden)
        monkeypatch.setattr(acquisition, '_capture_file', forbidden)
        case.owner.job_progress_provider.targets.observe_target = forbidden
        shutil.rmtree(case.native_root.parent)
        outcome = case.execute(child=child)
        body = outcome['result']
        assert body['complete'] and body['reused_from']['operation_key'] == original['operation_key']
        assert [row['value']['value'] for row in body['quantities']] == [0, 0.0]
        assert case.results.credit_view(child, {'known_record_refs': body['record_refs'],
            'initial_known_record_refs': []})['new_acquired_record_count'] == 0
        case.admit(child)
        assert case.observations == 1


def test_failed_native_diagnostic_request_can_complete_without_mask_quality_gate(tmp_path, monkeypatch):
    choice = selector(quantities=(), artifacts=[{'direction': 'output', 'role': 'stderr', 'ordinal': 0}])
    with Store(tmp_path / 'store') as store:
        case = HostCase(store, tmp_path, monkeypatch, selected=choice, failure=True)
        body = case.execute()['result']
        assert body['status']['native_state'] == 'failed' and not body['status']['output_complete']
        assert body['status']['state'] == 'complete' and body['complete']
        assert body['failures'] and len(body['artifacts']) == 1
        assert case.results.completion(case.child_context)
        case.admit()


def test_missing_original_ordinal_is_partial_and_no_repeat_acquisition_credit(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        case = HostCase(store, tmp_path, monkeypatch, selected=selector(records=[999]))
        first, second = case.execute()['result'], case.execute(index=1)['result']
        assert not first['complete'] and not second['complete']
        assert first['quantities'] == [] and first['failures']
        assert second['reused_from']['operation_key'] == first['operation_key']
        assert case.observations == 1
        assert case.results.credit_view(case.child_context, {'known_record_refs': second['record_refs'],
            'initial_known_record_refs': []})['new_acquired_record_count'] == 1


def test_original_forms_reject_changed_number_and_sibling_context(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        case = HostCase(store, tmp_path, monkeypatch)
        body = case.execute()['result']
        form, _ = case.admit()
        changed = deepcopy(form)
        field = next(k for k, v in case.schema['properties'].items() if v['x-source'] == 'execution.masking_quantities')
        changed[field][0]['value']['value'] += 1
        with pytest.raises(ValueError, match='conflict'):
            case.boundary.validate_received_report(case.child_context, changed, case.schema)
        sibling = case.child(case.root, case.schema, index=1, role='scientific_process')
        assert case.boundary.received_facts(sibling, case.schema)['execution.masking_quantities'] == []
        assert case.boundary.resolve_received(sibling, body['quantities'][0]['record_key'], 'native_blast_masking_record') is False


def test_input_references_need_actual_receipts_and_generated_statistics_match(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        choice = selector(quantities=(), artifacts=[{'direction': 'output', 'role': 'statistics', 'ordinal': 0}])
        case = HostCase(store, tmp_path, monkeypatch, program='windowmasker', mode='create_counts', selected=choice)
        body = case.execute()['result']
        case.admit()
        job = job_for(tmp_path / 'later-mask', 'windowmasker')
        stats = next(row for row in job['operands'] if row['role'] == 'statistics')
        occurrence = next(row for row in body['artifacts'] if row['role'] == 'statistics')
        stats.update({key: occurrence[key] for key in ('artifact_ref', 'sha256', 'size_bytes')})
        job['statistics_binding'] = {**case.bundle['statistics_binding'], 'producer_source_ref': body['source_ref']}
        assignment = {'requested_job': requested_job_from_native_blast_masking(job)}
        assert case.results.validate_job_inputs(case.root, assignment) == [stats['artifact_ref'], body['source_ref']]
        changed = deepcopy(job)
        changed['statistics_binding']['reference_occurrence_ids'] = ['wrong-original-reference']
        with pytest.raises(ValueError, match='provenance_conflict'):
            case.results.validate_job_inputs(case.root, {'requested_job': requested_job_from_native_blast_masking(changed)})
        other = store.artifact(b'not supplied to this episode')
        changed = deepcopy(job)
        changed['operands'][0]['artifact_ref'] = other
        with pytest.raises(ValueError, match='not_received'):
            case.results.validate_job_inputs(case.root, {'requested_job': requested_job_from_native_blast_masking(changed)})
        raw = job_for(tmp_path / 'raw')
        assert case.results.validate_job_inputs(case.root, {'requested_job': requested_job_from_native_blast_masking(raw)}) == []


def test_status_does_not_capture_or_complete(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        case = HostCase(store, tmp_path, monkeypatch)
        monkeypatch.setattr(host, 'capture_local_bundle', forbidden)
        body = case.execute(tool='execution.results.status')['result']
        assert body['capture'] is None and not body['record_refs'] and not body['complete']
        assert case.results.completion(case.child_context) is None
        assert case.results.credit_view(case.child_context, {'known_record_refs': [],
            'initial_known_record_refs': []})['credit'] == 0
