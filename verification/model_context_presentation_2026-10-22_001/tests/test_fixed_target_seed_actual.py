"""One actual fixed-input preparation; no configured-model or native work."""
import json
import os
from pathlib import Path

from gene_annotation_episode.fixed_target_seed import prepare_fixed_target_seed
from gene_annotation_episode.state import Store
from test_fixed_target_seed_runtime import assert_seed_matches, assert_source_preserved, digest, emit_evidence, file_inventory, input_file_inventory, intake_witness, sql_inventory


def test_actual_original_fixed_target_reproduces_in_new_verification_custody(tmp_path, monkeypatch):
    case = Path(__file__).resolve().parents[1] / 'cases' / 'gene_001'
    source = case / 'workspace'
    evidence_directory = os.environ.get('FIXED_TARGET_SEED_VERIFICATION_DIR')
    destination = (Path(evidence_directory) / 'actual-seed-workspace') if evidence_directory else tmp_path / 'actual-seed-workspace'
    assert not destination.exists() and not destination.is_symlink()
    source_files = file_inventory(source)
    original_inputs = input_file_inventory(case)
    source_rows = sql_inventory(source)
    original = intake_witness(source)
    before_helper_files = file_inventory(source)
    witness_bookkeeping = assert_source_preserved(source_files, before_helper_files)
    original_init, constructed = Store.__init__, []

    def destination_only(self, path):
        resolved = Path(path).resolve()
        assert resolved != source.resolve(), 'canonical source Store construction is forbidden'
        assert 'investigation_005' not in resolved.parts and 'investigation_009' not in resolved.parts
        constructed.append(str(resolved))
        return original_init(self, path)

    monkeypatch.setattr(Store, '__init__', destination_only)
    receipt = prepare_fixed_target_seed(case_directory=case, source_workspace=source, destination_workspace=destination)
    after_helper_files = file_inventory(source)
    helper_bookkeeping = assert_source_preserved(before_helper_files, after_helper_files)
    assert receipt['verification']['sqlite_reader_bookkeeping'] == helper_bookkeeping
    assert_seed_matches(receipt, original, destination)
    identity = receipt['fixed_identity']
    assert identity == {'case_ref': 'gene_001', 'problem_ref': 'problem_9d89f9abcb43930a1bb557f1', 'target_ref': 'input_a5c60b96717424cdf5138420', 'dna_length_nt': 762, 'protein_length_aa': 253, 'source_protein': 'P0AAW1', 'dna_sequence_sha256': '62930707904f67975532ff43f609f98f64700a9afbbc3c5eb446e02f3a513f26', 'protein_sequence_sha256': 'f0cdd3744b5bc986fd574175ecb7155c0ed57c7749098f20300735a3c849560a'}
    assert receipt['input_files']['target_fna']['sha256'] == '9638349ddf7c8198f29b8aa69d7f7fe50215ca4bb17f891d8a5f14d024f5b5d8'
    assert receipt['input_files']['target_faa']['sha256'] == 'ccdcdb50cfb0a7f24498c807adbbf38ae504c88b7437a01fc78fdc6ba213288b'
    assert source_rows == sql_inventory(source)
    assert input_file_inventory(case) == original_inputs
    complete_bookkeeping = assert_source_preserved(source_files, file_inventory(source))
    assert constructed
    assert constructed[-1] == str(destination.resolve())
    emit_evidence('actual-input-custody', {'receipt': receipt, 'canonical_source_workspace': str(source.resolve()), 'source_sql_snapshot_before': source_rows, 'source_sql_snapshot_after': sql_inventory(source), 'source_file_count': len(source_files), 'source_files_sha256': digest(source_files), 'input_file_pins': original_inputs, 'source_preservation': complete_bookkeeping, 'independent_witness_reader_bookkeeping': witness_bookkeeping, 'helper_reader_bookkeeping': helper_bookkeeping, 'complete_intake_equal': True, 'parser_indexes_sha256': digest(original['indexes']), 'constructed_destination_stores': constructed, 'runtime_actions': 0, 'scientific_findings_imported': 0, 'model_calls': 0, 'native_jobs': 0})
