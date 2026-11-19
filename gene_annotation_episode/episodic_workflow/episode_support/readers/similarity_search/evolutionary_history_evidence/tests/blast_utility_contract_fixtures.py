"""Synthetic relationship cases for pure 624 contracts; no native execution."""
from copy import deepcopy
import hashlib
import json
import jsonschema
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.evolutionary_history_evidence.blast_utility_contracts import SCHEMAS, validate_blast_utility_operation, validate_blast_utility_record, validate_blast_utility_result
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import ContractError

def occurrence(key='out', *, role='stdout', direction='output', fmt='text', data=b'synthetic\n'):
    return {'occurrence_id': key, 'direction': direction, 'role': role, 'ordinal': 0, 'artifact_ref': 'synthetic:' + key, 'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data), 'native_format': fmt, 'completeness': 'complete', 'native_path': '/retained/' + key}

def outcome(**updates):
    return {'started': True, 'returncode': 0, 'state': 'succeeded', 'writer_closed': True, 'inventory_complete': True, **updates}

def failure(code='native_row_invalid', **updates):
    return {'stage': 'parse', 'code': code, 'occurrence_id': 'out', 'record_key': None, 'line_number': 1, 'native_returncode': None, **updates}

def observation(**updates):
    return {'name': 'syntax', 'status': 'pass', 'subject_refs': ['out'], 'method': 'native_format_parser', 'reason': None, 'evidence_occurrence_ids': ['out'], **updates}

def operation(mode='extract_sequences', *, molecule='dna', **parameters):
    variants = {'create_sequence_database': ('makeblastdb', {'input_type': 'fasta', 'database_format_version': 5, 'output_prefix': 'db/tiny', 'title': 'synthetic', 'parse_seqids': True, 'hash_index': False, 'max_file_size': None, 'taxid': None, 'taxid_map_occurrence_id': None, 'mask_occurrence_ids': []}), 'extract_sequences': ('blastdbcmd', {'selectors': [{'ordinal': 0, 'value': 'ALPHA'}], 'output_format': 'blastdbcmd_tabular_v1', 'range': None, 'strand': 'plus', 'get_dups': False, 'target_only': False}), 'info': ('blastdbcmd', {'exact_length': True}), 'metadata': ('blastdbcmd', {}), 'integrity': ('blastdbcheck', {'full': True, 'stride': None, 'random_count': None, 'ends_count': None, 'no_isam': False, 'legacy_file_checks': False, 'require_taxids': False, 'cdd_delta': False})}
    program, selected = variants[mode]
    return {'version': 'blast_utility_operation_v1', 'program': program, 'mode': mode, 'input_occurrence_ids': ['source'] if program == 'makeblastdb' else [], 'database_key': None if program == 'makeblastdb' else 'tiny', 'molecule': molecule, 'parameters': {**selected, **parameters}}

def binding(*, molecule='dna'):
    return {'database_key': 'tiny', 'kind': 'blast_nucleotide_sequence' if molecule == 'dna' else 'blast_protein_sequence', 'molecule': molecule, 'identity': {'namespace': 'fixture', 'value': 'tiny', 'version': None, 'release': None}, 'source_ref': 'synthetic:manifest', 'native_paths': ['/retained/tiny'], 'occurrence_ids': ['db-file'], 'inventory_complete': True}

def field(**updates):
    return {'field_name': 'database_sequence_count', 'value': 2, 'unit': 'sequences', 'value_basis': 'native_reported_exact', 'native_lexeme': '2', 'occurrence_id': 'out', 'line_number': 1, 'json_pointer': None, 'missing_reason': None, **updates}

def extraction():
    return {'version': 'blast_sequence_extraction_v1', 'operation': operation(), 'database_binding': binding(), 'original_outcome': outcome(), 'output_occurrence': occurrence(fmt='blastdbcmd_tabular_v1', data=b'7\tALPHA\tALPHA.1\t4\tacgt\n'), 'records': [{'record_key': 'out#/records/2', 'native_row_ordinal': 2, 'line_number': 4, 'matched_selector_ordinals': [0], 'association': 'exact', 'native_oid': 7, 'native_identifier': 'ALPHA', 'native_accession': 'ALPHA.1', 'native_reported_length': 4, 'native_length_basis': 'full_sequence', 'original_sequence': 'acgt', 'normalized_sequence': 'ACGT', 'returned_symbol_count': 4, 'molecule': 'dna', 'requested_range': None, 'effective_range': {'start_0based': 0, 'end_exclusive': 4, 'strand': 'plus'}, 'completeness': 'complete', 'checks': [], 'failures': []}], 'missing_selector_ordinals': [], 'unexpected_record_keys': [], 'population_completeness': 'complete_selection', 'checks': [], 'failures': []}

def inspection():
    return {'version': 'blast_database_inspection_v1', 'operation': operation('info'), 'database_binding': binding(), 'output_occurrence': occurrence(fmt='blastdb_info_text'), 'original_outcome': outcome(), 'native_fields': [field()], 'completeness': 'complete', 'checks': [observation()], 'failures': []}

def integrity():
    return {'version': 'blast_database_integrity_v1', 'operation': operation('integrity'), 'database_binding': binding(), 'stdout_occurrence': occurrence(fmt='blastdbcheck_text'), 'stderr_occurrence': occurrence('err', role='stderr'), 'original_outcome': outcome(), 'scope': 'unknown', 'observed_checked_count': None, 'observed_population_count': None, 'observed_sampled_oids': None, 'realized_seed': None, 'diagnostics': [], 'checks': [], 'failures': []}

def artifact_set(version=5):
    op = operation('create_sequence_database', database_format_version=version)
    outputs = [occurrence('tiny.' + ext, role='database_file', fmt='blastdb_binary', data=ext.encode()) for ext in ('nhr', 'nin', 'nsq', 'ndb', 'not', 'ntf', 'nto')]
    return {'version': 'blast_database_artifact_set_v1', 'kind': 'sequence_database', 'operation': op, 'original_outcome': outcome(), 'database_key': 'tiny', 'identity': {'namespace': 'fixture', 'value': 'tiny', 'version': None, 'release': None, 'scope': None, 'preparation_type': 'sequence_database', 'source': {'source_ref': 'synthetic:manifest', 'pointer': ''}}, 'software': {'name': 'makeblastdb', 'version': None, 'executable_sha256': None}, 'argv': ['makeblastdb', '-in', '/retained/source'], 'native_paths': ['/retained/tiny'], 'inputs': [occurrence('source', role='sequence_input', direction='input', fmt='fasta')], 'outputs': outputs, 'dependencies': [], 'inventory_complete': True, 'native_metadata': [], 'detail': {k: op['parameters'][k] for k in ('input_type', 'database_format_version', 'parse_seqids', 'hash_index', 'taxid', 'taxid_map_occurrence_id', 'mask_occurrence_ids')}, 'compatibility': 'unverified', 'checks': [], 'failures': []}

def prepared_manifest():
    artifacts = artifact_set()
    receipt = {'path': '/retained/receipt.json', 'sha256': 'a' * 64, 'size_bytes': 2, 'artifact_ref': None}
    return {'version': 'native_blast_standard_prepared_database_manifest_v1', 'database_key': 'tiny', 'kind': 'blast_nucleotide_sequence', 'identity': artifacts['identity'], 'native_paths': artifacts['native_paths'], 'files': [{'path': r['native_path'], 'sha256': r['sha256'], 'size_bytes': r['size_bytes']} for r in artifacts['outputs']], 'preparation': {'method': 'makeblastdb', 'preparation_type': 'sequence_database', 'software': artifacts['software'], 'argv': artifacts['argv'], 'source': artifacts['identity']['source'], 'input_manifest': None, 'receipt': receipt}, 'metadata_manifests': [], 'access': {'mode': 'prepared_local', 'offline_configuration': None}, 'inventory_complete': True}

def assert_invalid(kind, value, code=None):
    with pytest.raises(ContractError, match='^blast_utility_' + (code or '')):
        validate_blast_utility_record(kind, value)
