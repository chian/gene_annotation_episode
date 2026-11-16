from __future__ import annotations
from jsonschema import Draft202012Validator, validators
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_standard_database_calculators as calculators
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_standard_database_contracts as contracts
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_standard_database_metadata as metadata
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_standard_database_result_views as views
from gene_annotation_episode.episodic_workflow.root.a110.domain import validate_schema
PREFIX = views.PREFIX
_ABS = {'type': 'string', 'pattern': '^/[^\\x00]*$', 'minLength': 1}
_FILE_ID = dict(artifact_ref=views.REF, sha256=views.SHA, size_bytes=views.I0)
_ATTEMPT = views._object(dict(identity=contracts.IDENTITY_SCHEMA, attempt_directory=_ABS, plan_sha256=views.SHA))
_MODEL = {'anyOf': [{'type': 'null'}, {'type': 'object', 'properties': {'temperature_bits': {'type': 'number', 'exclusiveMinimum': 0}, 'function_priors': {'anyOf': [{'type': 'null'}, {'type': 'object', 'additionalProperties': {'type': 'number', 'minimum': 0}}]}}, 'additionalProperties': False}]}
_DESCRIPTOR = {'oneOf': [views._object(dict(input_key=views.TOKEN, consumer={'const': consumer}, schema_id={'const': schema_id}, **_FILE_ID, origin={'enum': ['original_job_input', 'selected_results_input']})) for consumer, schema_id in contracts._METADATA_TUPLES]}
_SNAPSHOT = dict(subject_ref=views.REF, record_type={'enum': ['input', 'feature', 'product', 'read_subject']}, molecule={'enum': ['dna', 'rna', 'protein']}, length={'type': 'integer', 'minimum': 1}, sequence_sha256=views.SHA, sequence_artifact_ref=views.REF)
_ROLES = {'inputs': ('inputs.json', metadata.PREPARED_INPUTS_SCHEMA), 'collection': ('collection.json', 'blast_report_collection_v1'), 'sheets': ('sheets.json', metadata.SHEET_SET_SCHEMA), 'calculations': ('calculations.json', calculators.CALCULATION_SCHEMA), 'rows': ('rows.ndjson', PREFIX + 'numeric_row_v1'), 'row_index': ('row-index.json', PREFIX + 'row_index_v1'), 'metric_definitions': ('metric-definitions.json', PREFIX + 'metric_definitions_v1'), 'diagnostics': ('diagnostics.json', PREFIX + 'diagnostics_v1')}
_MANIFEST_VERSION = PREFIX + 'result_worker_manifest_v2'
STANDARD_BLAST_DATABASE_WORKER_REQUEST_SCHEMA = views._object(dict(version={'const': PREFIX + 'result_worker_request_v1'}, calculation_id=views.SHA, bundle=contracts.NATIVE_BLAST_STANDARD_DATABASE_BUNDLE_SCHEMA, bundle_artifact_ref=views.REF, bundle_capture=views._object(dict(path=_ABS, sha256=views.SHA, size_bytes=views.I0)), authenticated_attempt=_ATTEMPT, artifacts=views._array(views._object(dict(artifact_key=views.TOKEN, path=_ABS, **_FILE_ID))), metadata_descriptors=views._array(_DESCRIPTOR), retained_sources=views._array(views._object(dict(source_ref=views.REF, path=_ABS, **_FILE_ID))), subject_snapshots=views._array(views._object(dict(**_SNAPSHOT, sequence_path=_ABS))), sequence_model=_MODEL, output_directory=_ABS, reuse=views._nullable(views._object(dict(manifest_path=_ABS, manifest_sha256=views.SHA, manifest_size_bytes=views.I0, collection_path=_ABS, sheets_path=_ABS)))))
STANDARD_BLAST_DATABASE_WORKER_MANIFEST_SCHEMA = views._object(dict(version={'const': _MANIFEST_VERSION}, calculation_id=views.SHA, request_sha256=views.SHA, status={'enum': ['complete', 'partial', 'failed']}, input_identity=views.SHA, input_interpretation_id=views.SHA, sequence_model=_MODEL, artifacts=views._array(views._object(dict(role={'enum': list(_ROLES)}, relative_path=views.TOKEN, sha256=views.SHA, size_bytes=views.I0, schema=views.TOKEN))), counts=views._object(dict(searches=views.I0, native_hsp_slots=views.I0, numerical_rows=views.I0)), failures=views._array(views.FAILURE_SCHEMA)))
_StrictValidator = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine('integer', lambda checker, value: type(value) is int))

def _shape(value, schema):
    validate_schema(value, schema)
    _StrictValidator(schema).validate(value)
    return value

def _absolute_path(value):
    if type(value) is not str or not value.startswith('/') or '\x00' in value or ('..' in value.split('/')):
        raise ValueError(PREFIX + 'absolute_path_required')
    return value

def standard_blast_database_input_identity(request: dict) -> str:
    """Hash selected inputs and original attempt, without local capture paths."""
    request = views._copy(request)
    value = dict(version=PREFIX + 'input_identity_v1', bundle=dict(artifact_ref=request['bundle_artifact_ref'], **{k: request['bundle_capture'][k] for k in ('sha256', 'size_bytes')}), authenticated_attempt=request['authenticated_attempt'], artifacts=[{k: r[k] for k in ('artifact_key', *_FILE_ID)} for r in request['artifacts']], metadata_descriptors=request['metadata_descriptors'], retained_sources=[{k: r[k] for k in ('source_ref', *_FILE_ID)} for r in request['retained_sources']], subject_snapshots=[{k: r[k] for k in _SNAPSHOT} for r in request['subject_snapshots']])
    _shape(value, views._object(dict(version={'const': PREFIX + 'input_identity_v1'}, bundle=views._object(_FILE_ID), authenticated_attempt=_ATTEMPT, artifacts=views._array(views._object(dict(artifact_key=views.TOKEN, **_FILE_ID))), metadata_descriptors=views._array(_DESCRIPTOR), retained_sources=views._array(views._object(dict(source_ref=views.REF, **_FILE_ID))), subject_snapshots=views._array(views._object(_SNAPSHOT)))))
    _absolute_path(value['authenticated_attempt']['attempt_directory'])
    return views._hash(value)

def standard_blast_database_calculation_identity(*, input_identity: str, sequence_model: dict | None) -> dict:
    _shape(input_identity, views.SHA)
    model = calculators.validate_sequence_model(sequence_model)
    interpretation = views._hash(dict(version=PREFIX + 'interpretation_identity_v1', input_identity=input_identity))
    return dict(input_interpretation_id=interpretation, calculation_id=views._hash(dict(version=PREFIX + 'calculation_identity_v1', input_interpretation_id=interpretation, sequence_model=model)))
