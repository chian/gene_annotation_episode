from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import math
from gene_annotation_episode.episodic_workflow.root.a110.domain import validate_schema
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_database_result_views as _views
import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_database_contracts as _contracts
_FUNCTION_REQUEST = 'native_blast_database_result_worker_request_vdb_function_v1'
_FUNCTION_MANIFEST = 'native_blast_database_result_worker_manifest_vdb_function_v1'
_FUNCTION_SHEETS = 'native_blast_database_sheet_set_vdb_function_v1'
_FUNCTION_CALCULATIONS = 'native_blast_database_calculations_vdb_function_v1'

def _number(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))

def _model(model):
    try:
        model = _views._copy(model)
    except ValueError as error:
        raise ValueError('native_blast_database_sequence_model_invalid') from error
    if model is None:
        return None
    if type(model) is not dict or set(model) - {'temperature_bits', 'function_priors'}:
        raise ValueError('native_blast_database_sequence_model_invalid')
    if 'temperature_bits' in model and (not _number(model['temperature_bits']) or model['temperature_bits'] <= 0):
        raise ValueError('native_blast_database_sequence_model_invalid')
    if 'function_priors' in model:
        priors = model['function_priors']
        if type(priors) is not dict or any((not isinstance(k, str) or not k or (not _number(v)) or (v < 0) for k, v in priors.items())):
            raise ValueError('native_blast_database_sequence_model_invalid')
        for token in priors:
            try:
                validate_schema(token, _views._TOKEN)
            except ValueError as error:
                raise ValueError('native_blast_database_sequence_model_invalid') from error
    return model

def _hash(value):
    return hashlib.sha256(json.dumps(_views._copy(value), sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()

def _shape(value, schema):
    """Use the producer's strict JSON type semantics, including true integers."""
    _contracts._schema(value, schema)
    return value

def _absolute_path(value):
    if type(value) is not str or not value.startswith('/') or '\x00' in value or ('..' in value.split('/')):
        raise ValueError('native_blast_database_absolute_path_required')
    return value
_ABS = {'type': 'string', 'minLength': 1}
_FILE_ID = dict(artifact_ref=_views._REF, sha256=_views._SHA, size_bytes=_views._I0)
_DESCRIPTOR = _views._object(dict(input_key=_views._TOKEN, consumer={'enum': ['query_identity', 'sequence_database', 'profile', 'iteration', 'vdb']}, schema_id=_views._TOKEN, **_FILE_ID, origin={'enum': ['original_job_input', 'selected_results_input']}))

def _descriptor(function_mode=False):
    value = deepcopy(_DESCRIPTOR)
    if function_mode:
        value['properties']['consumer']['enum'].append('vdb_function')
    return value
_ATTEMPT = _views._object(dict(identity=_contracts.IDENTITY_SCHEMA, attempt_directory=_ABS, plan_sha256=_views._SHA))
_SNAPSHOT_ID = dict(subject_ref=_views._REF, record_type={'enum': ['input', 'feature', 'product', 'read_subject']}, molecule={'enum': ['dna', 'rna', 'protein']}, length={'type': 'integer', 'minimum': 1}, sequence_sha256=_views._SHA, sequence_artifact_ref=_views._REF)

def native_blast_database_input_identity(request):
    """Identity of selected captured inputs; no path lookup or interpretation."""
    request = _views._copy(request)
    try:
        value = dict(version='native_blast_database_input_identity_v1', bundle=dict(artifact_ref=request['bundle_artifact_ref'], **{k: request['bundle_capture'][k] for k in ('sha256', 'size_bytes')}), authenticated_attempt=request['authenticated_attempt'], artifacts=[{k: r[k] for k in ('artifact_key', 'artifact_ref', 'sha256', 'size_bytes')} for r in request['artifacts']], metadata_descriptors=request['metadata_descriptors'], retained_sources=[{k: r[k] for k in ('source_ref', 'artifact_ref', 'sha256', 'size_bytes')} for r in request['retained_sources']], subject_snapshots=[{k: r[k] for k in _SNAPSHOT_ID} for r in request['subject_snapshots']])
        _shape(value, _views._object(dict(version={'const': 'native_blast_database_input_identity_v1'}, bundle=_views._object(_FILE_ID), authenticated_attempt=_ATTEMPT, artifacts=_views._array(_views._object(dict(artifact_key=_views._TOKEN, **_FILE_ID))), metadata_descriptors=_views._array(_descriptor(request.get('version') == _FUNCTION_REQUEST)), retained_sources=_views._array(_views._object(dict(source_ref=_views._REF, **_FILE_ID))), subject_snapshots=_views._array(_views._object(_SNAPSHOT_ID)))))
        _absolute_path(value['authenticated_attempt']['attempt_directory'])
    except (KeyError, TypeError) as error:
        raise ValueError('native_blast_database_input_identity_invalid') from error
    return _hash(value)

def native_blast_database_calculation_identity(*, input_identity, sequence_model, vdb_function_model=None):
    """Separate input interpretation from the selected numerical generation."""
    _shape(input_identity, _views._SHA)
    model = _model(sequence_model)
    interpretation = _hash(dict(version='native_blast_database_interpretation_identity_v1', input_identity=input_identity))
    if vdb_function_model is not None:
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.blast_vdb_function_calculators import validate_blast_vdb_function_model
        function_model = validate_blast_vdb_function_model(vdb_function_model)
        return dict(input_interpretation_id=interpretation, calculation_id=_hash(dict(version='native_blast_vdb_function_calculation_identity_v1', input_interpretation_id=interpretation, base_calculation_contract=dict(schema='native_blast_database_calculations_v1', sequence_model=model), model=function_model)))
    return dict(input_interpretation_id=interpretation, calculation_id=_hash(dict(version='native_blast_database_calculation_identity_v1', input_interpretation_id=interpretation, sequence_model=model)))
