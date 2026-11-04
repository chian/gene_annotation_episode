"""Actual ordinary alignments; explicit fixture credits, no model launches."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import sqlite3

from gene_annotation_episode.execution_recording import NativeMeasurement
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, project_finding_progress
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.ordinary_execution import OrdinaryExecutionStatistics
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from gene_annotation_episode.tools import ToolRegistry
from test_scientific_hypervolume_runtime import assessment


def test_actual_tool_measurements_update_history_without_duplicate_scientific_findings(tmp_path):
    history_path = tmp_path/'history.sqlite'
    history = RunHistory(history_path); history.close()
    with Store(tmp_path/'workspace') as store:
        target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
        binding = OrdinaryExecutionStatistics(history_path, 'fixture-host', tmp_path/'receipts')
        tools = ToolRegistry(store, native_statistics=binding)
        arguments = {'query_ref': target, 'reference_ref': target, 'molecule': 'protein', 'mode': 'global'}
        hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'sequence_integrity',
            'value': {'type': 'enum', 'value': 'intact'}, 'context_refs': []}, origin='reasoning')
        sources, findings, attempts = [], [], []
        for key in ('first-physical-alignment', 'second-physical-alignment'):
            result = tools.execute('sequence.align', arguments, operation_key=key)
            assert result['status'] == 'completed', result
            body = result['result']
            source = store.get(body['source_ref'])
            sources.append(source['artifact_ref'])
            assert 'local_job' not in json.loads(store.get_artifact(source['artifact_ref']))
            exported = body['local_job']['statistics_export']
            assert exported['state'] == 'recorded' and exported['recovery_state'] == 'retained'
            measured = NativeMeasurement.from_record(exported['measurement'])
            assert measured.statistic.elapsed_seconds == body['local_job']['elapsed_seconds'] > 0
            assert measured.execution_class.cpu_threads is None
            attempts.append(measured.statistic.attempt_sha256)
            assert store.db.execute("SELECT count(*) FROM sqlite_master WHERE name='runtime_observations'").fetchone()[0] == 0
            # An actual self-alignment does not independently establish that
            # the underlying biological sequence is intact. Record that same
            # qualification twice to test information identity, not biology.
            payload = assessment(hypothesis['id'], body['observation_ref'], 'scope_limited')
            payload['relation'] = 'does_not_discriminate'
            payload['investigation_finding'] = {
                'source_claim': {'subject_refs': [target], 'predicate': 'sequence_integrity',
                    'value': {'type': 'enum', 'value': 'intact'}, 'context_refs': []},
                'qualification': {'kind': 'measurement_does_not_establish_claim',
                    'context_refs': [], 'assumption_refs': []},
                'status': 'retained', 'withdrawal_reason': 'not_withdrawn',
                'same_source_claim_as_ref': None, 'replaces_refs': []}
            findings.append(store.put('assessment', payload, origin='reasoning')['id'])
            credit = project_finding_progress(store, {'subject_refs': [target]}, FindingProgressPolicy(7),
                known_assessment_refs=findings)
            assert credit['credit'] == 7 and credit['retained_finding_count'] == 1
            assert tools.execute('sequence.align', arguments, operation_key=key) == result
        assert sources[0] == sources[1] and attempts[0] != attempts[1]
        with sqlite3.connect(history_path) as db:
            assert db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 2
            payload = json.dumps(db.execute('SELECT data FROM execution_classes').fetchall())
            payload += json.dumps(db.execute('SELECT data FROM run_statistics').fetchall())
            assert target not in payload and 'MARGKKIGYS' not in payload
        native_arguments = {'query': 'MARGKKIGYS', 'reference': 'MARGKKIGYS',
                            'molecule': 'protein', 'mode': 'global'}
        scope = binding.alignment_class(native_arguments, tools.local_job_policy)
        history = RunHistory(history_path, create=False)
        snapshot = history.capture(scope)
        reader = history.reader(snapshot)
        forecast, = ResourceToolEstimator().estimate_context({'status': 'available',
            'execution_classes': [asdict(scope)], 'snapshots': [{'ref': snapshot, 'data': reader.get(snapshot)}]})
        assert forecast['status'] == 'available' and forecast['successful_duration_samples'] == 2
        assert forecast['cpu_threads'] is None
        reader.close(); history.close()
        assert not list(store.path.glob('.native-sequence-*'))


def test_alignment_classes_follow_actual_defaults_and_keep_incompatible_work_separate(tmp_path):
    binding = OrdinaryExecutionStatistics(tmp_path/'history.sqlite', 'fixture-host', tmp_path/'receipts')
    policy = LocalJobPolicy.from_config()
    args = {'query': 'ACGT', 'reference': 'ACCT', 'molecule': 'dna', 'mode': 'local'}
    first = binding.alignment_class(args, policy)
    assert binding.alignment_class({**args, 'query': 'TCGA'}, policy) == first
    assert binding.alignment_class({**args, 'gap_open': -10.0, 'gap_extend': -.5}, policy) == first
    for changed in ({'reference': 'ACCTA'}, {'mode': 'global'}, {'molecule': 'protein'}, {'gap_open': -9}):
        assert binding.alignment_class({**args, **changed}, policy).ref != first.ref
    assert binding.alignment_class(args, replace(policy, memory_bytes=policy.memory_bytes*2)).ref != first.ref
    assert replace(binding, resource_id='different-host').alignment_class(args, policy).ref != first.ref
    assert first.cpu_threads is None
    assert not binding.history_path.exists() and not binding.recovery_directory.exists()


def test_case_tool_configuration_binds_caller_history_resource_and_receipt_location(tmp_path):
    with Store(tmp_path/'workspace') as store:
        configured = {'history': str(tmp_path/'global.sqlite'), 'resource_id': 'caller-host',
                      'local_tools': {'native_receipts_dir': str(tmp_path/'caller-receipts')}}
        tools = build_tools(store, configured)
        assert tools.native_statistics == OrdinaryExecutionStatistics(configured['history'], 'caller-host',
                                                                     tmp_path/'caller-receipts')
        assert tools.resource_binding()['ordinary_execution_statistics'] == tools.native_statistics.as_record()
        assert tools.catalog()['sequence.align']['configuration']['timing_statistics'] == tools.native_statistics.as_record()
        assert 'timing_statistics' not in tools.catalog()['genes.predict']['configuration']
        assert not tools.native_statistics.history_path.exists()


def test_recovery_scan_failure_remains_informational_without_creating_history(tmp_path, monkeypatch):
    binding = OrdinaryExecutionStatistics(tmp_path/'absent.sqlite', 'fixture-host', tmp_path/'receipts')
    def unavailable(self, pattern):
        # Match an I/O error during lazy directory iteration, rather than only
        # at construction of the iterator returned by glob.
        if self == binding.recovery_directory:
            raise PermissionError('fixture receipt directory unavailable')
        yield from ()
    monkeypatch.setattr(Path, 'glob', unavailable)
    result = binding.recover_pending_statistics()
    assert result['scan_state'] == 'unavailable'
    assert result['pending'] == result['recorded'] == 0
    assert result['failures']['receipt_unavailable'] == 1
    assert not binding.history_path.exists()
