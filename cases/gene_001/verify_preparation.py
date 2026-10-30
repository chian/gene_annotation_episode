"""Verify retained case preparation; no model/native launch or scientific score."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sqlite3
from unittest.mock import patch

from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.run_statistics import ExecutionClass
from gene_annotation_episode.sequence_mapping import map_interval
from gene_annotation_episode.state import Store
import register_evidence
import register_run_statistics


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(store):
    return dict(store.db.execute('SELECT record_type,count(*) FROM records GROUP BY record_type'))


def main():
    with Store(ROOT / 'workspace') as store:
        before = counts(store)
    with patch('subprocess.Popen', side_effect=AssertionError('Preparation replay must not launch native work')):
        with redirect_stdout(io.StringIO()):
            register_evidence.main()
    refs = json.loads((ROOT / 'evidence-refs.json').read_text())
    scope = {'subject_refs': [refs['target_ref']]}
    with Store(ROOT / 'workspace') as store:
        after = counts(store)
        assert before == after
        assert [row['id'] for row in store.targets()] == scope['subject_refs']
        def resolve(ref, namespace):
            return bool(store.reference_subset([ref], scope)) and store.get(ref)['record_type'] == namespace
        schema = {'type': 'object', 'properties': {'comparisons': {'type': 'array', 'items': {
            'type': 'string', 'format': 'reference', 'x-reference-namespace': 'observation'}}},
            'required': ['comparisons'], 'additionalProperties': False}
        validate_form({'comparisons': refs['comparison_refs']}, schema, resolve)
        mapping = store.sequence_mapping(refs['product_ref'])
        for ref in refs['comparison_refs']:
            for operand in store.get(ref)['operand_intervals']:
                if operand['role'] != 'query':
                    continue
                assert operand['subject_ref'] == refs['product_ref']
                for span in map_interval(mapping, operand['start'], operand['end']):
                    assert span['subject_ref'] == refs['target_ref']
                    assert 0 <= span['start'] < span['end'] <= 759
        polymer = store.get(refs['source_refs']['4RUW.polymer_entity.1'])
        assert polymer['parent_source_refs'] == [refs['source_refs']['4RUW']]
        assert hashlib.sha256(store.get_artifact(polymer['artifact_ref'])).hexdigest() == digest(
            ROOT / 'acquisition/rcsb-4RUW-polymer1.json')
        article = store.get(refs['source_refs']['PMC7055658.full_text'])
        assert article['parent_source_refs'] == [refs['source_refs']['PubMed.32127419']]
        assert hashlib.sha256(store.get_artifact(article['artifact_ref'])).hexdigest() == digest(
            ROOT / 'acquisition/europepmc-7055658-response.body')
        failed_response = store.get(refs['source_refs']['PMC7055658.supplement_response'])
        assert failed_response['provider'] == 'transport.http_response'
        assert json.loads(store.get_artifact(failed_response['request_ref']))['http_status'] == 404
        assert failed_response['parent_source_refs'] == [article['id']]
        neighborhood = store.get(refs['source_refs']['NCBI.neighborhood_features'])
        assert neighborhood['parent_source_refs'] == [refs['source_refs']['NCBI.neighborhood']]
        assert after.get('annotation', 0) == after.get('assessment', 0) == 0
    (ROOT / 'evidence-verification.json').write_text(json.dumps({
        'kind': 'actual_case_preparation_verification', 'verified_at': datetime.now(timezone.utc).isoformat(),
        'idempotent_record_counts': True, 'record_counts': after,
        'typed_form_comparison_refs': len(refs['comparison_refs']),
        'query_extents_map_to_one_gene': True, 'omitted_stop_not_aligned': True,
        'structure_polymer_source_bytes_and_lineage_verified': True,
        'background_source_bytes_and_lineage_verified': True,
        'supplement_http_failure_preserved_as_transport_response': True,
        'model_driven_episode_evidence': False, 'numerical_credit_tested': False}, indent=2) + '\n')

    state_path = ROOT / 'workspace/state.sqlite3'
    state_before = digest(state_path)
    manifest = ROOT / 'jobs/homology_001/job.json'
    manifest_before = digest(manifest)
    saved = json.loads((ROOT / 'run-expectations.json').read_text())
    history_path = Path(saved['shared_history_path'])
    with patch('subprocess.Popen', side_effect=AssertionError('Statistics replay must not launch native work')):
        replayed = register_run_statistics.register(history_path, 'local-development')
        assert saved == replayed
        binding = ExecutionExpectations(history_path, by_grain={'improvement': [
            ExecutionClass(**item['execution_class']) for item in saved['bindings'].values()]})
        captured = binding.capture('improvement')
        assert captured['status'] == 'available'
        assert [item['ref'] for item in captured['snapshots']] == [
            item['expectation_ref'] for item in saved['bindings'].values()]
    assert digest(state_path) == state_before and digest(manifest) == manifest_before
    with sqlite3.connect(history_path) as db:
        totals = {table: db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in (
            'execution_classes', 'execution_conditions', 'run_statistics', 'expectation_snapshots')}
    assert totals == dict(execution_classes=2, execution_conditions=0, run_statistics=2, expectation_snapshots=2)
    (ROOT / 'run-expectations-verification.json').write_text(json.dumps({
        'kind': 'actual_probe_statistics_import_verification', 'verified_at': datetime.now(timezone.utc).isoformat(),
        'history_path': str(history_path), 'record_counts': totals,
        'import_replay_preserves_snapshot_bindings': True,
        'native_process_creation_forbidden_during_replay': True,
        'canonical_scientific_state_unchanged': True, 'scientific_state_sha256': state_before,
        'native_receipt_unchanged': True, 'native_receipt_sha256': manifest_before,
        'runtime_input_binding_reads_actual_statistics': True,
        'runtime_expectation_binding': binding.as_record(),
        'implementation_sha256': {name: digest(PROJECT / 'gene_annotation_episode' / name) for name in (
            'run_statistics.py', 'execution_expectations.py', 'runtime.py', 'numerical.py')},
        'model_driven_episode_evidence': False,
        'child_estimator_integration_verified': False,
        'child_estimator_integration_evidence': 'synthetic_runtime_tests'}, indent=2) + '\n')
    print(json.dumps({'case_preparation_replay': 'passed', 'registered_comparisons': len(refs['comparison_refs']),
        'global_timing_measurements': totals['run_statistics'], 'native_or_model_jobs_launched': 0,
        'annotation_count': after.get('annotation', 0)}))


if __name__ == '__main__':
    main()
