"""Episode-selected saved recalculation with exact receipts and purity probes."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.native_blast_database_result_publication import _json
from gene_annotation_episode.native_blast_database_result_views import SAVED_INPUT_SOURCE, FUNCTION_FAMILIES
from test_native_blast_vdb_function_integration import (
    connected_fixture, capture, selection, results_child, metric)


def forbid_acquisition(h, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('saved calculation attempted native observation, transfer or acquisition')
    monkeypatch.setattr(h.family.job_progress_provider.targets, 'observe_target', forbidden)
    monkeypatch.setattr(h.family.job_progress_provider.targets, 'read_file', forbidden)
    from gene_annotation_episode import native_blast_database_results as results
    monkeypatch.setattr(results, 'capture_native_blast_database_bundle', forbidden)
    from gene_annotation_episode.practical_pbs_operations import PBSPracticalOperations
    monkeypatch.setattr(PBSPracticalOperations, '_invoke', forbidden)


def enforce_worker_purity(monkeypatch):
    """Install failure probes inside the real bounded worker subprocess."""
    from gene_annotation_episode import native_blast_database_result_publication as publication
    runner = publication.run_local_job
    calls = []
    script = '''import importlib,json,pathlib,sys
from gene_annotation_episode import native_blast_database_result_worker as worker
def forbidden(*a, **k): raise AssertionError('saved worker attempted native parsing, population, base calculation or external work')
ports = {
 'native_blast_database_result_worker': ['parse_blast_report_collection','populate_native_blast_database_search_facts','alignment_components','_catalog','_metadata_payloads'],
 'blast_report_collection':['parse_blast_report_collection'],
 'native_blast_database_metadata':['prepare_native_blast_database_inputs','populate_native_blast_database_sheets'],
 'native_blast_vdb_function_metadata':['populate_native_blast_vdb_function_sheets'],
 'blast_vdb_function_inputs':['populate_blast_vdb_function_sheet'],
 'blast_vdb_inputs':['populate_blast_vdb_sheet','parse_ncbi_sra_runinfo','parse_blast_vdb_member_sequences','parse_ncbi_gbseq_vdb_metadata','bind_blast_vdb_metadata'],
 'blast_vdb_calculators':['calculate_blast_vdb_components'],
 'blast_profile_calculators':['calculate_blast_profile_components'],
 'blast_pssm_calculators':['calculate_blast_pssm_components'],
 'blast_iteration_calculators':['calculate_blast_iteration_components']}
for name,names in ports.items():
 module=importlib.import_module('gene_annotation_episode.'+name)
 for field in names: setattr(module,field,forbidden)
import socket,subprocess
socket.socket=forbidden
subprocess.Popen=forbidden
from gene_annotation_episode import blast_vdb_function_calculators as calculator
real=calculator.calculate_blast_vdb_function_components
counts=[]
def calculate(sheet, *, model):
 counts.append(model)
 return real(sheet,model=model)
calculator.calculate_blast_vdb_function_components=calculate
manifest=worker.run_native_blast_database_result_worker(sys.argv[1])
pathlib.Path(sys.argv[1]).with_name('saved-purity.json').write_text(json.dumps({'forbidden_ports':ports,'function_calculations':counts,'status':manifest['status']}))
print(json.dumps(manifest))
'''
    def checked(command, **kwargs):
        if len(command) > 3 and command[2:4] == ['-m', 'gene_annotation_episode.native_blast_database_result_worker']:
            calls.append(command[-1])
            command = [*command[:2], '-c', script, command[-1]]
        return runner(command, **kwargs)
    monkeypatch.setattr(publication, 'run_local_job', checked)
    return calls


def test_exact_received_generation_recalculates_and_second_saved_generation_is_selectable(tmp_path, monkeypatch):
    h, selected = connected_fixture(tmp_path, monkeypatch)
    try:
        first, original = capture(h, selected)
        assert original['complete'], original['failures']
        old_form, old_schema = h.returned(first)
        descriptor = h.family.native_blast_database_results.facts(first)[SAVED_INPUT_SOURCE][0]
        original_receipt = canonical(original)
        original_files = {field: artifact_path(h.store, original['preparation'][field]).read_bytes()
            for field in ('collection_artifact_ref', 'sheets_artifact_ref', 'calculations_artifact_ref', 'full_rows_artifact_ref')}
        old_actions = [dict(row) for row in h.store.db.execute('SELECT * FROM runtime_actions WHERE episode_id=?', (first.episode_id,))]
        old_forms = [dict(row) for row in h.store.db.execute('SELECT * FROM runtime_forms WHERE episode_id=?', (first.episode_id,))]
        calls_before = deepcopy(h.calls)
        forbid_acquisition(h, monkeypatch)
        worker_calls = enforce_worker_purity(monkeypatch)
        second, reused = capture(h, selection(saved=descriptor, temperature=2), index=2)
        assert reused['complete'], reused['failures']
        assert reused['observation'] is reused['capture'] is None
        assert reused['reused_result_receipt'] == descriptor['original_result_receipt']
        assert h.calls == calls_before and len(worker_calls) == 1
        publication = reused['publication']
        assert publication['source_ref'] == original['publication']['source_ref']
        functions = {r['identity']['function']['value']: r for r in publication['rows_by_family']['vdb_function']}
        assert {k: metric(r, 'conditional_function_weight')['value'] for k, r in functions.items()} == pytest.approx({'A': 2/3, 'B': 1/3})
        assert {k: metric(r, 'representation_adjusted_function_weight')['value'] for k, r in functions.items()} == pytest.approx({'A': 1/3, 'B': 2/3})
        assert reused['preparation']['sheets_artifact_ref'] == original['preparation']['sheets_artifact_ref']
        assert reused['preparation']['collection_artifact_ref'] == original['preparation']['collection_artifact_ref']
        assert reused['preparation']['calculation_id'] != original['preparation']['calculation_id']
        first_calc = _json(h.store, original['preparation']['calculations_artifact_ref'])
        second_calc = _json(h.store, reused['preparation']['calculations_artifact_ref'])
        assert {k:v for k,v in first_calc.items() if k not in ('vdb_function_model','vdb_function')} == {
            k:v for k,v in second_calc.items() if k not in ('vdb_function_model','vdb_function')}
        proof = h.family.completion_for_action(second, reused['operation_key'])
        assert proof['validation_keys'] == ['original_native_attempt', 'authenticated_saved_function_sheet', 'requested_native_numerical_projection']
        assert h.family.verify_completion(second, proof)
        from gene_annotation_episode.numerical import YieldParameters
        from test_practical_yield import completion_context
        expectation = completion_context(run_id=h.run_id, episode_id=second.episode_id, unit_index=0, action_index=0)
        runtime = {k: expectation['practical_completion'][k] for k in ('unit_ref', 'action_index')}
        expectation['practical_completion'] = {**proof, **runtime}
        expected_before = deepcopy(expectation)
        estimate = h.family.practical_estimator(second)((0.0,), YieldParameters(), (expectation,))
        assert estimate.expected_next_gain.lower == estimate.expected_next_gain.upper == 0
        assert expectation == expected_before
        form, schema = h.returned(second)
        received = h.family.native_blast_database_returns.received_facts(h.root, schema)
        assert len(received[SAVED_INPUT_SOURCE]) == 2
        descriptor2 = h.family.native_blast_database_results.facts(second)[SAVED_INPUT_SOURCE][0]
        assert descriptor2['original_result_receipt']['operation_key'] == reused['operation_key']
        assert descriptor2['input_interpretation_id'] == descriptor['input_interpretation_id']
        third, again = capture(h, selection(saved=descriptor2, temperature=4), index=3)
        assert again['complete'], again['failures']
        h.returned(third)
        assert len(worker_calls) == 2 and h.calls == calls_before
        assert h.family.native_blast_database_results.result_identity(original['publication']['source_ref'], h.scope) == h.family.native_blast_database_results.result_identity(again['publication']['source_ref'], h.scope)
        for child, body in ((second,reused),(third,again)):
            view = h.family.native_blast_database_results.credit_view(child, dict(known_record_refs=body['record_refs'],
                initial_known_record_refs=original['record_refs']))
            assert view['credit'] == 0 and view['new_acquired_record_count'] == 0
            assert h.store.db.execute('SELECT COUNT(*) FROM runtime_actions WHERE episode_id=?', (child.episode_id,)).fetchone()[0] == 1
        assert h.store.query_records('observation')['total'] == 0
        assert canonical(original) == original_receipt
        for field, raw in original_files.items():
            assert artifact_path(h.store, original['preparation'][field]).read_bytes() == raw
        assert [dict(r) for r in h.store.db.execute('SELECT * FROM runtime_actions WHERE episode_id=?', (first.episode_id,))] == old_actions
        assert [dict(r) for r in h.store.db.execute('SELECT * FROM runtime_forms WHERE episode_id=?', (first.episode_id,))] == old_forms
        assert h.returned(first)[0] == old_form
        for request in worker_calls:
            audit = json.loads(Path(request).with_name('saved-purity.json').read_text())
            assert audit['status'] == 'complete' and len(audit['function_calculations']) == 1
        (tmp_path / 'saved-typed-return.json').write_text(canonical(dict(form=form,schema=schema,received=received,
            original=original,second=reused,third=again,completion=proof)))
    finally:
        h.store.close()
