"""Write unimplemented custody contract documents; never open application data."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
IMPLEMENTATION = Path('/tmp/gene-annotation-hmmer-api-20261022-004')
P = Path('/tmp/scientific-context-proposal002-xmmw8Rca')

def write(name, value):
    target = ROOT/name
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode() if not isinstance(value, str) else value.encode()
    with target.open('xb') as output:
        output.write(raw)

def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def arr(item, **extra):
    return {'type': 'array', 'items': item, **extra}

def const(value):
    return {'const': value}

S = {'type': 'string', 'minLength': 1}
N = {'type': 'integer', 'minimum': 0}
H = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
REF = {'type': 'string', 'pattern': '^[a-z][a-z_]*_[a-f0-9]{24,64}$'}
ART = {'type': 'string', 'pattern': '^artifact_[a-f0-9]{64}$'}
REFS = arr(REF, uniqueItems=True)
PATH = {'type': 'string', 'pattern': '^/[^\u0000]*$'}
RUN = {'type': 'string', 'pattern': '^run_[a-f0-9]{32}$'}
FILE = obj({'path': S, 'sha256': H, 'bytes': N})
NULL_FILE = {'anyOf': [FILE, {'type': 'null'}]}
TIME = {'type': 'string', 'format': 'date-time'}

request = obj({
    'source_workspace': PATH, 'source_run_directory': PATH,
    'source_implementation_root': PATH, 'source_run_id': RUN,
    'expected_source_implementation_sha256': H,
    'expected_pending_request_sha256': H,
    'destination_workspace': PATH,
    'initial_known_record_refs': {**REFS, 'minItems': 1},
})

inventory = obj({
    'version': const('stopped_fixed_science_execution_inventory_v1'),
    'workspace_empty_tables': arr(obj({'table': {'enum': [
        'provider_jobs', 'provider_job_failures', 'runtime_commission_intents',
        'runtime_timed_commissions', 'runtime_forms', 'runtime_report_attempts']}, 'count': const(0)}), uniqueItems=True),
    'forbidden_workspace_table_prefixes_absent': const(['api_', 'public_search_']),
    'native_registry_database': FILE,
    'native_registry_configuration': FILE,
    'native_registry_empty_tables': const([
        {'table': 'handoffs', 'count': 0}, {'table': 'orders', 'count': 0}, {'table': 'samples', 'count': 0}]),
    'run_count': const(1), 'episode_count': const(1),
    'pending_call_count': const(1),
})

unit = obj({'episode_id': S, 'unit_index': N, 'unit_id': S})
index_row = obj({
    'run_id': RUN, 'episode_id': S, 'unit_index': N,
    'decision_index_present': {'type': 'boolean'},
    'decision_index': {'type': ['integer', 'null'], 'minimum': 0},
    'unit_ref': unit, 'raw_text_utf8_offset': N, 'raw_text_utf8_bytes': N,
    'raw_text_utf8_sha256': H, 'delimiter_bytes': const(1), 'delimiter_hex': const('0a'),
})
index = obj({
    'version': const('scientific_checkpoint_observation_index_v1'),
    'meaning': const('prior_run_lineage_not_new_local_observations'),
    'stream_representation': const('original_sqlite_text_utf8_with_separate_lf_delimiters'),
    'source_run_id': RUN, 'source_episode_id': S,
    'observation_source_ref': REF, 'observation_artifact_ref': ART,
    'observation_artifact_sha256': H, 'observation_artifact_bytes': N,
    'record_count': N, 'rows': arr(index_row),
})

lineage_metadata = obj({
    'version': const('scientific_checkpoint_lineage_source_v1'),
    'kind': {'enum': ['original_observations', 'observation_index']},
    'meaning': const('prior_run_lineage_not_new_local_observations'),
    'source_run_id': RUN, 'source_episode_id': S,
    'source_implementation_sha256': H, 'source_settings_raw_utf8_sha256': H,
    'source_pending_request_raw_utf8_sha256': H,
    'source_table_manifest_sha256': H, 'source_artifact_manifest_sha256': H,
    'original_observation_count': N,
    'fixed_target_ref': REF,
})
source_input = obj({
    'provider': const('caller.scientific_checkpoint_fork'), 'accession': S,
    'uri': {'type': 'null'}, 'artifact_ref': ART, 'text_ref': ART,
    'request_ref': ART, 'version': const('scientific_checkpoint_fork_v1'),
    'retrieved_at': {'type': 'null'}, 'operand_refs': arr(REF, minItems=1, maxItems=1),
    'parent_source_refs': arr(REF, maxItems=1),
})
source_output = obj({**source_input['properties'], 'id': REF, 'record_type': const('source'), 'origin': const('caller')})

table = obj({'name': S, 'column_names': arr(S), 'row_count': N, 'typed_rows_sha256': H})
schema_object = obj({'type': {'enum': ['table', 'index', 'trigger', 'view']},
    'name': S, 'table_name': S, 'sql': {'type': ['string', 'null']}})
tables = obj({'version': const('sqlite_typed_row_inventory_v1'),
    'encoding': const('sqlite_storage_class_frame_v1'),
    'database_encoding': {'enum': ['UTF-8', 'UTF-16le', 'UTF-16be']},
    'schema_objects': arr(schema_object), 'tables': arr(table)})
artifact_row = obj({'id': ART, 'sha256': H, 'media_type': S, 'bytes': N,
    'relative_path': S})
artifacts = obj({'version': const('scientific_checkpoint_artifact_inventory_v1'),
    'count': N, 'total_bytes': N, 'artifacts': arr(artifact_row)})
preservation = obj({
    'mode': const('read_only_immutable_database_absent_or_empty_wal'),
    'database_before': FILE, 'database_after': FILE,
    'wal_before': NULL_FILE, 'wal_after': NULL_FILE,
    'shm_before': NULL_FILE, 'shm_after': NULL_FILE,
    'source_files_equal': const(True), 'registered_artifact_files_equal': const(True),
    'source_authority_files_equal': const(True),
    'reader_bookkeeping_changes': const([]),
})

receipt = obj({
    'version': const('scientific_checkpoint_fork_v1'),
    'status': const('custody_prepared_no_new_run'), 'fork_id': S, 'captured_at': TIME,
    'destination_workspace': PATH,
    'source': obj({
        'workspace': PATH, 'run_directory': PATH, 'implementation_root': PATH,
        'run_id': RUN, 'episode_id': S, 'implementation_sha256': H,
        'implementation_file_manifest': FILE,
        'authority_files': arr(FILE, minItems=5),
        'settings_raw_utf8_sha256': H,
        'pending': obj({'call_index': N, 'purpose': S,
            'request_raw_utf8_sha256': H, 'request_raw_utf8_bytes': N,
            'response': {'type': 'null'}, 'selected_action_at_call': const(False)}),
        'counts': obj({'model_calls': N, 'actions': N, 'observations': N, 'episodes': const(1)}),
        'execution_inventory': inventory, 'preservation': preservation,
    }),
    'fixed_identity': obj({'case_ref': S, 'problem_ref': REF, 'target_ref': REF,
        'target_sequence_artifact_ref': ART, 'target_sequence_sha256': H}),
    'checkpoint': obj({'database': FILE, 'table_manifest': FILE, 'artifact_manifest': FILE,
        'committed_reference_manifest': FILE}),
    'workspace_database_at_publication': FILE,
    'preserved_counts': obj({'tables': N, 'artifacts': N, 'artifact_bytes': N,
        'input_records': N, 'committed_records': N, 'staged_proposals': N}),
    'lineage': obj({'observation_source_ref': REF, 'index_source_ref': REF,
        'observation_artifact_ref': ART, 'index_artifact_ref': ART,
        'original_observation_count': N}),
    'caller_initial_known_record_refs': REFS,
    'initial_known_record_refs': REFS, 'initial_known_record_refs_sha256': H,
    'verification': obj({key: const(True) for key in (
        'snapshot_database_bytes_equal_source_main', 'snapshot_schema_and_rows_equal',
        'all_source_rows_preserved_after_destination_additions',
        'registered_artifact_bytes_equal', 'packed_material_components_equal',
        'all_committed_input_and_record_refs_explicitly_selected',
        'all_selected_refs_resolve_through_actual_destination_store',
        'new_lineage_sources_validate_through_actual_store',
        'lineage_windows_match_original_raw_text',
        'old_run_authority_unchanged', 'no_new_run_or_observation_created')}),
    'limitations': const([
        'new_workspace_not_same_episode_migration', 'no_old_job_adoption',
        'no_relocated_old_run_resumability', 'no_new_scientific_or_monitoring_credit',
        'external_paths_retained_as_original_provenance',
        'source_run_and_policy_parameters_not_rebound',
        'later_new_caller_configuration_and_execution_separately_authorized']),
})
result = obj({'version': const('scientific_checkpoint_fork_result_v1'),
    'status': const('published'), 'destination_workspace': PATH,
    'receipt': FILE, 'initial_known_record_refs': REFS,
    'lineage_source_refs': obj({'observations': REF, 'index': REF})})
codes = ['invalid_request', 'source_unavailable', 'source_identity_mismatch',
    'source_schema_unsupported', 'source_nonempty_wal_out_of_scope',
    'source_execution_inventory_out_of_scope', 'source_changed', 'baseline_incomplete',
    'reference_invalid', 'artifact_custody_failure', 'material_custody_failure',
    'snapshot_mismatch', 'destination_invalid', 'destination_overlap', 'destination_exists',
    'destination_lineage_failure', 'publication_failure', 'storage_failure']
failure = obj({'version': const('scientific_checkpoint_fork_failure_v1'),
    'code': {'enum': codes}, 'phase': {'enum': [
        'validate_request', 'capture_source', 'validate_inventory', 'snapshot',
        'copy_artifacts', 'validate_snapshot', 'build_lineage', 'verify_source', 'publish']},
    'affected_refs': arr(S, uniqueItems=True),
    'staging_workspace': {'type': ['string', 'null']},
    'published_workspace': {'type': ['string', 'null']},
    'publication_state': {'enum': ['not_created', 'retained_stage', 'published_durability_unconfirmed']},
    'source_unchanged': {'type': ['boolean', 'null']},
    'cause': {'enum': [None, 'contract_error', 'permission_denied', 'io_error',
        'sqlite_error', 'unsupported_platform', 'process_interrupted']},
    'errno': {'type': ['integer', 'null']}})

schema_names = {'request': request, 'receipt': receipt, 'result': result, 'failure': failure,
    'execution_inventory': inventory, 'table_manifest': tables, 'artifact_manifest': artifacts,
    'lineage_source_input': source_input, 'lineage_source_output': source_output,
    'lineage_source_metadata': lineage_metadata, 'observation_index': index}
write('SCHEMAS.json', {'$schema': 'https://json-schema.org/draft/2020-12/schema',
    '$id': 'urn:scientific-checkpoint-custody-contract:20261022:001',
    '$defs': schema_names,
    'description': 'PLANNING ONLY. Closed proposed shapes. Relationships and zero-write semantics in CONTRACT.md are also normative; no custody implementation exists.'})

readset = {
 'gene_annotation_episode/state.py': 'Complete constructor/read_snapshot/transaction/artifact/get_artifact/get/_require/_refs/source validation/_record_roots/put read; source read only, no object constructed.',
 'gene_annotation_episode/domain.py': 'Complete canonical/identity/schema helpers, full closed source schema including additive optional source fields and validation read.',
 'gene_annotation_episode/materials.py': 'Complete install_tables/artifact_file/artifact_path/is_text/source_for_artifact/source_window read; actual byte-window returns and error cuts.',
 'gene_annotation_episode/materials_packing.py': 'Complete module read; chunk artifact/span/component identities and materialization costs.',
 'gene_annotation_episode/fixed_target_seed.py': 'Complete module read; intake-only exclusion, read-only source, no-replace/fsync/error cuts; reader SHM allowances deliberately not adopted for this narrower contract.',
 'gene_annotation_episode/case_execution.py': 'Complete module read; old default caller shapes, explicit baseline parameter save/forward, fresh run and native registry.',
 'gene_annotation_episode/investigation_policy.py': 'Complete module read; actual existing received_findings parameters/controller preservation.',
 'gene_annotation_episode/investigation_progress.py': 'Complete projector path read; known current retained findings, old revisions/inactive dependencies, initial baseline meaning.',
 'gene_annotation_episode/native_timing_information.py': 'Complete module read; actual initial execution receipt baseline excludes old attempts from new monitoring credit.',
 'gene_annotation_episode/monitoring_credit.py': 'Complete module read; existing operational monitoring paths remain run/episode-owned and separate.',
 'gene_annotation_episode/episode_receipts.py': 'Complete module read; Store.get every input/record, forward reference closure, artifact rows, collection-member skip, run-keyed baseline.',
 'gene_annotation_episode/application_execution_binding.py': 'Complete module read; exact immutable known descriptor and caller pin source authority.',
 'gene_annotation_episode/independent_execution.py': 'Complete pin/settings/make_runtime_binding and current reconstruction paths previously read in004; hash algorithm/settings paths reread for custody.',
 'gene_annotation_episode/episode_journal.py': 'Complete relevant constructor/row/save paths reread; original TEXT stays opaque, no recovery invoked.',
 'gene_annotation_episode/runtime.py': 'Complete affected new-run _run_location/_run_bound_workflow caller path, Workflow.build/projection_arguments/source_credit_view/native_timing_arguments/record_selection read; complete full runtime inspected during004 ownership. No source-run object opened.',
 'gene_annotation_episode/tools.py': 'Complete source.read schema+selected dispatch read; complete affected registry previously inspected in004. No registry constructed.',
 'method_loop/identities.py': 'Complete module read; original UnitRef binds episode/unit, no run_id inside UnitRef.',
}
files=[]
for name, inspection in readset.items():
    path=IMPLEMENTATION/name
    raw=path.read_bytes()
    files.append({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'inspection':inspection})
for path in [Path('/home/chia/repos/gene_annotation_episode')/name for name in (
        'AGENTS.md','GOAL.md','docs/EPISODE_STRUCTURE.md','docs/TIME_AWARE_ESTIMATION.md')]:
    raw=path.read_bytes()
    files.append({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
        'inspection':'Complete instructions read in this task or preceding004 task; unchanged bytes verified. No application behavior changed.'})
factory=Path('/home/chia/repos/gene_annotation_episode/cases/gene_001/runs/configured_development_002/policy-787117fa5d397694ea1377413f6932401b5cfec9acd92af934517ea044e71dfc.py')
for path, inspection in [(factory,'Complete saved original source read without import/execute; baseline retained through replace.'),
 (Path('/home/chia/.codex/attachments/6c61440f-d223-4bea-91e3-6e4f7b2c5013/pasted-text-1.txt'),'Complete immutable goal read; no mutation.')]:
    raw=path.read_bytes()
    files.append({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'inspection':inspection})
write('READSET.json', {'status':'planning_only_no_application_imports_or_data_reads',
    'implementation_root':str(IMPLEMENTATION),'implementation_sha256':'16435877cddb566a9b802b6b3ce942595a9564b4cc10f8ca52b75f4007d9689d',
    'files':files})
inputs=[]
for name in ('EXECUTION_INVENTORY002.json','CHECKPOINT_FORK002.md','BASELINE_PARAMETERS002.md',
        'BASELINE_PARAMETER_CONTRACT.json','SOURCE_PINS002.json','R_READSET002.json','R_REVIEW002.md','MANIFEST002.json'):
    path=P/name; raw=path.read_bytes()
    inputs.append({'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
write('INPUT_PROVENANCE.json', {'status':'unadopted_custody_planning_only','source': 'P002 retained typed inventory; no new scientific SQLite opens',
    'files':inputs, 'root_additional_readonly_stat': {'source_database_bytes':211947520,'source_wal_bytes':0,
    'authority':'Root message in this task, independently observed by root; not rechecked here'},
    'adoption_choices_confirmed_by_root': [
        'Explicit baseline covers every committed Store-resolvable input/record ID.',
        'Native registry derives from and matches actual pinned case-launch authority.',
        'Zero-write source; absent/empty WAL only; immutable reader and exact before/after source sidecar identities.',
        'Separate immutable pre-addition snapshot and mutable destination working DB accepted; avoid unnecessary copies.']})
write('DISCOVERY_LIMITS.json', {'status':'planning_only', 'application_imports':0,'scientific_database_opens':0,
    'source_workspace_writes':0,'actual_forks':0,'model_calls':0,'public_calls':0,'native_jobs':0,'application_tests':0,
    'administrative_read_discoveries': [
        {'command':'rg for guessed case_bootstrap.py','result':'path absent; discovered actual case_execution.py; no application call'},
        {'command':'sed gene_annotation_episode/material_packing.py','result':'path absent; rg --files found actual materials_packing.py; full actual module then read'},
        {'command':'batched complete planning/source reads','result':'aggregate output truncated; required complete paths reread in bounded individual chunks'}],
    'limits': [
        'Source scientific DB/artifact bodies not reopened; actual execution counts are P002 retained facts.',
        'No implementation of any schema/constructor/publication contract; schemas alone do not prove custody.',
        'Original metadata/body text not printed; only saved factory code and retained typed planning metadata inspected.',
        'Root API004 independent verification is separate prior evidence, not custody verification.']})

