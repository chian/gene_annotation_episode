"""Retained numerical generations and exact selected, frozen database views.

The worker owns interpretation/calculation. This host owns input authority,
bounded execution, immutable custody and projection. No native search occurs.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys

from .communication import plain
from .acquisition import AcquisitionError
from .domain import ContractError, identity, validate_schema
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .local_jobs import LocalJobPolicy, run_local_job
from .materials import artifact_file
from .native_blast_standard_database_acquisition import (_attempt, _decode, _retained, _source_payload, _validate_capture)
from .native_blast_standard_database_contracts import validate_standard_blast_database_bundle
from .native_blast_standard_database_result_views import (standard_blast_database_fact_sources,
    project_standard_blast_database_rows, validate_standard_blast_database_selector)
from .native_blast_standard_database_result_worker import (standard_blast_database_calculation_identity,
    standard_blast_database_implementation_identity, standard_blast_database_input_identity,
    STANDARD_BLAST_DATABASE_WORKER_REQUEST_SCHEMA, STANDARD_BLAST_DATABASE_WORKER_MANIFEST_SCHEMA)
from .practical_execution_state import _immutable, _read
from .tool_grading_artifacts import retain_tool_grading

PREPARATION_VERSION = 'native_blast_standard_database_preparation_v1'
PUBLICATION_VERSION = 'native_blast_standard_database_publication_v1'
_ARTIFACT_FIELDS = {'collection': 'collection_artifact_ref', 'sheets': 'sheets_artifact_ref',
    'calculations': 'calculations_artifact_ref', 'rows': 'full_rows_artifact_ref',
    'row_index': 'row_index_artifact_ref', 'diagnostics': 'diagnostics_artifact_ref'}
_ROLES_V1 = {'inputs': ('inputs.json', 'native_blast_standard_database_prepared_inputs_v1'),
    'collection': ('collection.json', 'blast_report_collection_v1'),
    'sheets': ('sheets.json', 'native_blast_standard_database_sheet_set_v1'),
    'calculations': ('calculations.json', 'native_blast_standard_database_calculations_v1'),
    'rows': ('rows.ndjson', 'native_blast_standard_database_numeric_row_v1'),
    'row_index': ('row-index.json', 'native_blast_standard_database_row_index_v1'),
    'metric_definitions': ('metric-definitions.json', 'native_blast_standard_database_metric_definitions_v1'),
    'diagnostics': ('diagnostics.json', 'native_blast_standard_database_diagnostics_v1')}
_ROLES_V2 = {**_ROLES_V1, 'calculations': ('calculations.json', 'native_blast_standard_database_calculations_v2')}
_MANIFEST_ROLES = {'native_blast_standard_database_result_worker_manifest_v1': _ROLES_V1,
    'native_blast_standard_database_result_worker_manifest_v2': _ROLES_V2}


def _failure(stage, code, detail_code, **fields):
    return dict(stage=stage, code=code, artifact_key=None, input_key=None, search_key=None,
        record_key=None, pointer='', detail_code=detail_code) | fields


def _local_job_failure(error):
    resource = isinstance(error, AcquisitionError) and error.code == 'local_job_resource_limit'
    return _failure('worker', 'native_blast_standard_database_worker_resource_limit' if resource
        else 'native_blast_standard_database_worker_failed', 'resource_limit' if resource else 'implementation_failure')


def _exception_diagnostic(error, failure_index=0):
    value = dict(failure_index=failure_index,
        exception_type=type(error).__module__ + '.' + type(error).__qualname__, message=str(error))
    if isinstance(error, AcquisitionError):
        value.update(code=error.code, phase=error.phase, operational=deepcopy(error.operational))
    return value


def _local_job_exception_receipt(error):
    return dict(version='native_blast_standard_database_local_job_failure_v1', code=error.code,
        phase=error.phase, operational=deepcopy(error.operational))


def _json_artifact(store, value):
    return store.artifact(canonical(value), 'application/json')


def _json(store, reference):
    return _decode(_retained(store, reference).read_bytes())


def _known(store, context):
    """Use the existing frozen receipt prefix; Store presence grants no authority."""
    EpisodeReturnRecords(store, context.run_id, failure_prefix='native_blast_standard_database_input_').authenticate(context, allow_unsaved=True)
    if not store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_receipt_inheritance'").fetchone():
        return set()
    if not store.db.execute('SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
            (context.run_id, context.episode_id)).fetchone():
        return set()
    # Read an already installed receipt index without its constructor's schema
    # transaction, since commissioning may already own a transaction.
    receipts = EpisodeReceipts.__new__(EpisodeReceipts)
    receipts.store, receipts.db, receipts.run_id = store, store.db, context.run_id
    return set(receipts.known(context.episode_id))


def _selected_input_refs(selector):
    return list(dict.fromkeys([r['artifact_ref'] for r in selector['metadata_inputs']]
        + [ref for r in selector['retained_sources'] for ref in (r['source_ref'], r['artifact_ref'])]))


def validate_standard_blast_selected_inputs(store, context, selector, *, handoff_ref=None):
    known = _known(store, context)
    if handoff_ref is not None and handoff_ref not in known:
        raise ContractError('native_blast_standard_database_original_handoff_not_received')
    if not set(_selected_input_refs(selector)) <= known:
        raise ContractError('native_blast_standard_database_selected_input_not_received')
    for row in [*selector['metadata_inputs'], *selector['retained_sources']]:
        _retained(store, row['artifact_ref'], sha256=row['sha256'], size_bytes=row['size_bytes'])
    for row in selector['retained_sources']:
        source = store.get(row['source_ref'])
        if source.get('record_type') != 'source' or source.get('artifact_ref') != row['artifact_ref']:
            raise ContractError('native_blast_standard_database_selected_source_artifact_conflict')
    return _selected_input_refs(selector)


def validate_standard_blast_job_inputs(store, context, assignment):
    """Non-null original input handles must belong to the actual parent scope."""
    job = assignment.get('requested_job', {}).get('native_blast_standard_database')
    if job is None:
        return []
    rows = [row for row in job['inputs'] if row['artifact_ref'] is not None]
    known = _known(store, context)
    if any(row['artifact_ref'] not in known for row in rows):
        raise ContractError('native_blast_standard_database_original_input_not_received')
    for row in rows:
        _retained(store, row['artifact_ref'], sha256=row['sha256'], size_bytes=row['size_bytes'])
    return list(dict.fromkeys(row['artifact_ref'] for row in rows))


def _original_commission(store, context):
    """Read the original parent selection through existing episode records."""
    from method_loop.identities import EpisodeRef
    authority = EpisodeReturnRecords(store, context.run_id, failure_prefix='native_blast_standard_database_preparation_')
    authority.authenticate(context)
    if context.role != 'results' or len(context.path) < 2:
        raise ContractError('native_blast_standard_database_original_results_commission_required')
    parent = authority.context(EpisodeRef(context.run_id, context.path[:-1]).episode_id)
    label = context.path[-1][1]
    index = label.removeprefix('child_')
    if not label.startswith('child_') or not index.isdecimal() or str(int(index)) != index:
        raise ContractError('native_blast_standard_database_original_results_commission_required')
    row = store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
        (context.run_id, parent.episode_id, int(index))).fetchone()
    selected = {} if row is None else json.loads(row['action'])
    contract = plain(context.request)['report_contract']
    if (selected.get('kind') != 'episode_child' or selected.get('role') != 'results'
            or selected.get('assignment') != plain(context.assignment) or selected.get('scope') != plain(context.scope)
            or selected.get('purpose') != contract['decision']
            or _decode(selected.get('schema_json', '{}')) != contract['measurements']['schema']):
        raise ContractError('native_blast_standard_database_original_results_commission_conflict')
    store.validate_scope(plain(context.scope), parent_scope=plain(parent.scope))


def _original_handoff(store, context, target, attempt):
    from .practical_receipt_information import PracticalReceiptInformation
    if target['handle'] != plain(context.assignment)['handoff_ref'] or target['handle'] not in _known(store, context):
        raise ContractError('native_blast_standard_database_original_handoff_not_received')
    body = PracticalReceiptInformation(store, context.run_id).read(target['handle'], context.scope)
    snapshot = _json(store, store.get(target['handle'])['request_ref'])
    assignment, receipt = snapshot['assignment'], body['receipt']
    detail = receipt['outcome']['native_outcome']
    expected = dict(version='execution_target_v1', handle=target['handle'], run_id=context.run_id,
        resource_id=assignment['resource_id'], resource_kind='hpc', execution_id=detail['pbs_job_id'],
        request_sha256=digest(assignment['requested_job']), origin_episode_id=body['episode_id'],
        assignment=assignment, scope=body['scope'])
    if (target != expected or detail['attempt_id'] != attempt['identity']['attempt_id']
            or detail['attempt_operation_key'] != attempt['identity']['operation_key']
            or detail['native_blast_standard_database_plan_sha256'] != attempt['plan_sha256']
            or detail['native_blast_standard_database_plan_path'] != str(Path(attempt['attempt_directory']) / 'native-blast-standard-database-plan.json')):
        raise ContractError('native_blast_standard_database_original_handoff_conflict')


def _policy(policy):
    if not isinstance(policy, LocalJobPolicy) or policy.to_dict() != {
            'memory_bytes': 20 * 1024**3, 'scratch_bytes': 4 * 1024**3, 'wall_seconds': None}:
        raise ContractError('native_blast_standard_database_explicit_grading_policy_required')
    return policy


def _environment(directory):
    for name in ('tmp', 'cache'):
        (directory / name).mkdir(exist_ok=True)
    return {'PYTHONPATH': str(Path(__file__).resolve().parents[1]), 'PYTHONDONTWRITEBYTECODE': '1',
        **{k: str(directory / 'tmp') for k in ('TMPDIR', 'TMP', 'TEMP')},
        'XDG_CACHE_HOME': str(directory / 'cache')}


def _implementation(directory, policy, *, execution_program):
    """Inventory a fresh import closure, excluding unrelated parent imports."""
    output = directory / 'implementation.json'
    if not output.exists():
        script = '''import hashlib, json, pathlib, sys
from gene_annotation_episode.native_blast_standard_database_result_worker import _implementation_modules, standard_blast_database_implementation_identity
modules = _implementation_modules()
files = []
for name, module in modules.items():
    path = pathlib.Path(module.__file__).resolve()
    files.append({'module':name,'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
with open(sys.argv[1], 'x') as out: out.write(json.dumps({'files':files,'manifest_sha256':standard_blast_database_implementation_identity(files)},sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+chr(10))
'''
        try:
            result = run_local_job([sys.executable, '-B', '-c', script, str(output)],
                cwd=directory, policy=policy, stdout_path=directory / 'implementation.stdout',
                stderr_path=directory / 'implementation.stderr', env=_environment(directory))
        except AcquisitionError as error:
            _immutable(directory / 'implementation-receipt.json', _local_job_exception_receipt(error))
            raise
        _immutable(directory / 'implementation-receipt.json', result.metadata)
        if result.returncode != 0:
            raise ContractError('native_blast_standard_database_implementation_inventory_failed')
    value = _read(output)
    if value['manifest_sha256'] != standard_blast_database_implementation_identity(value['files']):
        raise ContractError('standard_blast_database_implementation_identity_conflict')
    for row in value['files']:
        if hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() != row['sha256']:
            raise ContractError('native_blast_standard_database_implementation_changed')
    return value


def _snapshots(store, context, directory):
    from .native_hmmer_result_publication import _subject_chunks
    known, snapshots = _known(store, context), []
    for row in store.subjects(plain(context.scope)):
        if row['id'] not in known:
            continue
        length, molecule = store.subject_length(row['id']), store.subject_molecule(row['id'])
        if not length or molecule not in {'dna', 'rna', 'protein'}:
            continue
        path = directory / ('subject-' + digest(row['id']))
        if not path.exists():
            with path.open('xb') as stream:
                for chunk in _subject_chunks(store, row['id']):
                    stream.write(chunk.encode('ascii') if isinstance(chunk, str) else chunk)
        reference = artifact_file(store, path)
        record = store.get(reference)
        if record['size'] != length:
            raise ContractError('native_blast_standard_database_subject_snapshot_length_conflict')
        snapshots.append(dict(subject_ref=row['id'], record_type=row['record_type'], molecule=molecule,
            length=length, sequence_sha256=record['sha256'], sequence_artifact_ref=reference,
            sequence_path=str(_retained(store, reference))))
    return snapshots


def _metadata_descriptors(bundle, capture, selector):
    job = bundle['requested_job']['native_blast_standard_database']
    byinput = {r['input_key']: r for r in bundle['artifacts'] if r['input_key'] is not None}
    selected_inputs = {r['input_key']: r for r in job['inputs']}
    descriptors = []
    for descriptor in job['metadata_inputs']:
        item = byinput.get(descriptor['input_key'])
        original = selected_inputs[descriptor['input_key']]
        # A missing captured metadata sibling remains unavailable to R; its
        # declared content identity does not pretend that Store has its bytes.
        sha = original['sha256'] if item is None else item['sha256']
        size = original['size_bytes'] if item is None else item['size_bytes']
        ref = None if item is None else capture['artifact_refs'].get(item['artifact_key'])
        descriptors.append(dict(**descriptor, artifact_ref=ref or 'artifact_' + sha,
            sha256=sha, size_bytes=size, origin='original_job_input'))
    descriptors += [dict(**row, origin='selected_results_input') for row in selector['metadata_inputs']]
    return descriptors


def _retained_catalog(store, selector, artifacts, snapshots):
    retained = [dict(**row, path=str(_retained(store, row['artifact_ref']))) for row in selector['retained_sources']]
    present = {r['artifact_ref'] for r in artifacts + retained}
    for row in selector['metadata_inputs']:
        if row['artifact_ref'] not in present:
            retained.append(dict(source_ref=row['artifact_ref'], **{k: row[k] for k in ('artifact_ref', 'sha256', 'size_bytes')},
                path=str(_retained(store, row['artifact_ref']))))
            present.add(row['artifact_ref'])
    for row in snapshots:
        if row['sequence_artifact_ref'] not in present:
            retained.append(dict(source_ref=row['sequence_artifact_ref'], artifact_ref=row['sequence_artifact_ref'],
                sha256=row['sequence_sha256'], size_bytes=row['length'], path=row['sequence_path']))
            present.add(row['sequence_artifact_ref'])
    return retained


def _request(store, context, target, capture, selector, directory, implementation):
    _original_commission(store, context)
    validate_standard_blast_selected_inputs(store, context, selector)
    capture_directory = directory.parent / 'capture'
    _validate_capture(store, capture, target=target, directory=capture_directory)
    if capture['status'] not in {'complete', 'partial'}:
        raise ContractError('native_blast_standard_database_authenticated_bundle_required')
    witness = _read(capture_directory / 'authenticated-attempt.json')
    attempt = _attempt(target, witness)
    _original_handoff(store, context, target, attempt)
    bundle = _json(store, capture['bundle_artifact_ref'])
    job = bundle['requested_job']['native_blast_standard_database']
    artifacts = [dict(artifact_key=row['artifact_key'], artifact_ref=capture['artifact_refs'][row['artifact_key']],
        path=str(_retained(store, capture['artifact_refs'][row['artifact_key']])), sha256=row['sha256'], size_bytes=row['size_bytes'])
        for row in bundle['artifacts'] if row['artifact_key'] in capture['artifact_refs']]
    descriptors = _metadata_descriptors(bundle, capture, selector)
    snapshots = _snapshots(store, context, directory)
    retained = _retained_catalog(store, selector, artifacts, snapshots)
    bundle_record = store.get(capture['bundle_artifact_ref'])
    request = dict(version='native_blast_standard_database_result_worker_request_v1', bundle=bundle,
        bundle_artifact_ref=capture['bundle_artifact_ref'], bundle_capture=dict(path=str(_retained(store, capture['bundle_artifact_ref'])),
            sha256=bundle_record['sha256'], size_bytes=bundle_record['size']), authenticated_attempt=attempt,
        artifacts=artifacts, metadata_descriptors=descriptors, retained_sources=retained, subject_snapshots=snapshots,
        implementation=implementation, sequence_model=job['grading_parameters']['sequence_database_model'], reuse=None)
    # Save the real invalid request before propagating a contract error; never
    # invent a valid calculation generation or replace a selected model.
    try:
        ids = standard_blast_database_calculation_identity(input_identity=standard_blast_database_input_identity(request),
            input_implementation_sha256=implementation['manifest_sha256'], sequence_model=request['sequence_model'],
            implementation_manifest_sha256=implementation['manifest_sha256'])
    except (ValueError, TypeError, KeyError) as error:
        _immutable(directory / 'invalid-request.json', request)
        failure = _failure('calculation', 'native_blast_standard_database_calculation_failed', 'calculator_contract_invalid')
        _immutable(directory / 'invalid-request-diagnostics.json', {'schema': 'native_blast_standard_database_diagnostics_v1',
            'failures': [failure], 'metadata_issues': [], 'errors': [{'failure_index': 0,
                'exception_type': type(error).__module__ + '.' + type(error).__qualname__, 'message': str(error)}]})
        raise ContractError('native_blast_standard_database_calculator_contract_invalid') from error
    request['calculation_id'] = ids['calculation_id']
    return request, witness


def _manifest(store, reference, request, artifact_refs):
    value = _json(store, reference)
    validate_schema(request, STANDARD_BLAST_DATABASE_WORKER_REQUEST_SCHEMA)
    validate_schema(value, STANDARD_BLAST_DATABASE_WORKER_MANIFEST_SCHEMA)
    expected = {'version', 'calculation_id', 'request_sha256', 'status', 'input_identity', 'input_interpretation_id',
        'input_implementation_sha256', 'implementation_manifest_sha256', 'sequence_model', 'artifacts', 'counts', 'failures'}
    if (type(value) is not dict or set(value) != expected or value['version'] not in _MANIFEST_ROLES
            or value['status'] not in {'complete', 'partial', 'failed'} or value['calculation_id'] != request['calculation_id']
            or value['request_sha256'] != hashlib.sha256((canonical(request) + '\n').encode('utf-8')).hexdigest()
            or value['input_identity'] != standard_blast_database_input_identity(request)
            or value['implementation_manifest_sha256'] != request['implementation']['manifest_sha256']
            or value['sequence_model'] != request['sequence_model']
            or type(value['counts']) is not dict or set(value['counts']) != {'searches', 'native_hsp_slots', 'numerical_rows'}
            or any(type(n) is not int or n < 0 for n in value['counts'].values())
            or type(value['artifacts']) is not list):
        raise ContractError('native_blast_standard_database_worker_manifest_invalid')
    ids = standard_blast_database_calculation_identity(input_identity=value['input_identity'],
        input_implementation_sha256=value['input_implementation_sha256'], sequence_model=value['sequence_model'],
        implementation_manifest_sha256=value['implementation_manifest_sha256'])
    if any(value[k] != v for k, v in ids.items()):
        raise ContractError('native_blast_standard_database_worker_manifest_identity_conflict')
    roles, seen = _MANIFEST_ROLES[value['version']], set()
    for row in value['artifacts']:
        role = row['role']
        if (set(row) != {'role', 'relative_path', 'sha256', 'size_bytes', 'schema'} or role not in roles or role in seen
                or (row['relative_path'], row['schema']) != roles[role] or role not in artifact_refs):
            raise ContractError('native_blast_standard_database_worker_artifact_manifest_conflict')
        seen.add(role)
        _retained(store, artifact_refs[role], sha256=row['sha256'], size_bytes=row['size_bytes'])
    if seen != set(artifact_refs):
        raise ContractError('native_blast_standard_database_worker_artifact_manifest_conflict')
    if value['status'] != 'failed' and not set(_ROLES_V1) <= seen:
        raise ContractError('native_blast_standard_database_worker_artifact_manifest_incomplete')
    if 'sheets' in artifact_refs:
        sheets = _json(store, artifact_refs['sheets'])
        if sheets.get('schema') != roles['sheets'][1]:
            raise ContractError('native_blast_standard_database_frozen_sheet_schema_conflict')
        from .native_blast_standard_database_metadata import validate_standard_blast_database_sheet_set
        validate_standard_blast_database_sheet_set(sheets)
        if (sheets['collection'] != _json(store, artifact_refs['collection'])
                or sheets['prepared_inputs'] != _json(store, artifact_refs['inputs'])):
            raise ContractError('native_blast_standard_database_frozen_sheet_source_conflict')
        attempts = [r['value'] for r in sheets['prepared_inputs']['source_relations'] if r['kind'] == 'attempt']
        if attempts != [dict(bundle=request['bundle'], attempt_identity=request['authenticated_attempt'],
                bundle_source_ref=request['bundle_artifact_ref'], bundle_artifact_ref=request['bundle_artifact_ref'],
                bundle_sha256=request['bundle_capture']['sha256'])]:
            raise ContractError('native_blast_standard_database_frozen_sheet_attempt_conflict')
    if 'calculations' in artifact_refs:
        calculations = _json(store, artifact_refs['calculations'])
        if calculations.get('schema') != roles['calculations'][1]:
            raise ContractError('native_blast_standard_database_frozen_calculation_schema_conflict')
        if value['version'] == 'native_blast_standard_database_result_worker_manifest_v2':
            from .native_blast_standard_database_calculators import validate_standard_blast_correspondence
            try:
                validate_standard_blast_correspondence(calculations)
            except (ValueError, KeyError, TypeError, IndexError) as error:
                raise ContractError('native_blast_standard_database_frozen_correspondence_conflict') from error
    validate_schema(value['failures'], standard_blast_database_fact_sources()['execution_blast_standard_database_failures']['report_schema'])
    return value


def _preparation_failures(manifest, caller_failure, capture):
    failures = [] if manifest is None else deepcopy(manifest['failures'])
    if caller_failure is not None:
        failures.append(deepcopy(caller_failure))
    for index, failure in enumerate(capture['failures']):
        failures.append(_failure('capture', 'native_blast_standard_database_capture_incomplete',
            'artifact_digest_conflict' if failure['code'] in {'file_digest_mismatch', 'file_changed'} else 'artifact_bytes_unavailable',
            artifact_key=failure['artifact_key'], pointer='/capture/failures/' + str(index)))
    status = ('failed' if manifest is None or manifest['status'] == 'failed'
        else 'partial' if failures else manifest['status'])
    return failures, status


def prepare_standard_blast_database_grading(store, *, context, target, capture, selector, directory, policy):
    directory = Path(directory).resolve(); directory.mkdir(parents=True, exist_ok=True)
    _policy(policy)
    selector = validate_standard_blast_database_selector(selector,
        program=target['assignment']['requested_job']['native_blast_standard_database']['program'])
    intent = {'run_id': context.run_id, 'episode_id': context.episode_id, 'scope': plain(context.scope),
        'assignment': plain(context.assignment), 'target': target, 'capture': capture, 'selector': selector, 'policy': policy.to_dict()}
    _immutable(directory / 'intent.json', intent)
    if (directory / 'preparation.json').exists():
        prepared = _read(directory / 'preparation.json')
        _validate_preparation(store, context, prepared)
        return prepared
    implementation = _implementation(directory, policy,
        execution_program=target['assignment']['requested_job']['native_blast_standard_database']['program'])
    request, witness = _request(store, context, target, capture, selector, directory, implementation)
    generation = store.path.resolve() / 'native-blast-standard-database-generations' / request['calculation_id']
    request['output_directory'] = str(generation / 'output')
    validate_schema(request, STANDARD_BLAST_DATABASE_WORKER_REQUEST_SCHEMA)
    generation.mkdir(parents=True, exist_ok=True)
    # Only identical authorized inputs can reuse frozen rows. Selector fields
    # do not enter the generation; a projection never reruns a calculator.
    _immutable(generation / 'request.json', request)
    cache = generation / 'retained.json'
    if cache.exists():
        retained = _read(cache)
    else:
        started = generation / 'started.json'
        if started.exists():
            raise ContractError('native_blast_standard_database_original_worker_interrupted')
        _immutable(started, {'request_sha256': digest(request)})
        receipt, failure, errors = None, None, []
        try:
            result = run_local_job([sys.executable, '-B', '-m', 'gene_annotation_episode.native_blast_standard_database_result_worker',
                str(generation / 'request.json')], cwd=generation, policy=policy,
                stdout_path=generation / 'worker.stdout', stderr_path=generation / 'worker.stderr', env=_environment(generation))
            receipt = result.metadata
            if result.returncode != 0:
                # A signal alone does not establish an enforced resource limit.
                failure = _local_job_failure(None)
        except AcquisitionError as error:
            receipt = _local_job_exception_receipt(error)
            failure = _local_job_failure(error)
            errors = [_exception_diagnostic(error)]
        except (ValueError, OSError) as error:
            failure = _local_job_failure(error)
            errors = [_exception_diagnostic(error)]
        manifest_path = generation / 'output' / 'worker-manifest.json'
        manifest_ref, artifacts, unsealed = None, {}, {}
        if manifest_path.exists():
            manifest_ref = artifact_file(store, manifest_path, 'application/json')
            manifest_value = _json(store, manifest_ref)
            if manifest_value.get('version') != 'native_blast_standard_database_result_worker_manifest_v2':
                raise ContractError('native_blast_standard_database_worker_manifest_invalid')
            roles = _MANIFEST_ROLES[manifest_value['version']]
            for row in manifest_value['artifacts']:
                if row['role'] not in roles or (row['relative_path'], row['schema']) != roles[row['role']]:
                    raise ContractError('native_blast_standard_database_worker_artifact_manifest_conflict')
                artifacts[row['role']] = artifact_file(store, generation / 'output' / row['relative_path'])
            _manifest(store, manifest_ref, request, artifacts)
        elif failure is None:
            failure = _failure('worker', 'native_blast_standard_database_worker_failed', 'implementation_failure')
        diagnostics_ref = None
        if manifest_ref is None:
            # R atomically renames these filenames individually. Without the
            # final manifest they are retained diagnostics, never a row source.
            roles = _ROLES_V2
            for role, (name, _) in roles.items():
                path = generation / 'output' / name
                if path.is_file() and not path.is_symlink():
                    unsealed[role] = artifact_file(store, path)
        if failure is not None:
            diagnostics_ref = _json_artifact(store, {'schema': 'native_blast_standard_database_diagnostics_v1',
                'failures': [failure], 'metadata_issues': [], 'errors': errors})
        retained = {'manifest_artifact_ref': manifest_ref, 'artifact_refs': artifacts,
            'unsealed_artifact_refs': unsealed,
            'request_artifact_ref': artifact_file(store, generation / 'request.json', 'application/json'),
            'worker_receipt_artifact_ref': _json_artifact(store, receipt),
            'worker_log_artifact_refs': [artifact_file(store, generation / name) for name in ('worker.stdout', 'worker.stderr')
                if (generation / name).exists()], 'caller_failure': failure, 'caller_diagnostics_artifact_ref': diagnostics_ref}
        _immutable(cache, retained)
    manifest = None if retained['manifest_artifact_ref'] is None else _manifest(store,
        retained['manifest_artifact_ref'], request, retained['artifact_refs'])
    capture_ref = _json_artifact(store, capture)
    failures, status = _preparation_failures(manifest, retained['caller_failure'], capture)
    observation_path = directory.parent / 'observation.json'
    if not observation_path.is_file():
        raise ContractError('native_blast_standard_database_original_observation_required')
    grading = {'schema': 'native_blast_standard_database_retained_grading_v1', **retained,
        'authenticated_attempt_artifact_ref': _json_artifact(store, witness),
        'observation_artifact_ref': artifact_file(store, observation_path, 'application/json'),
        'intent_artifact_ref': artifact_file(store, directory / 'intent.json', 'application/json'),
        'capture_artifact_ref': capture_ref}
    prepared = {'version': PREPARATION_VERSION, 'calculation_id': request['calculation_id'],
        'bundle_artifact_ref': capture['bundle_artifact_ref'], 'capture_artifact_ref': capture_ref,
        'worker_manifest_artifact_ref': retained['manifest_artifact_ref'],
        'source_grading_artifact_ref': retain_tool_grading(store, provider='episode.execution_result',
            native_artifact_ref=capture['bundle_artifact_ref'], grading=grading),
        **{field: retained['artifact_refs'].get(role) for role, field in _ARTIFACT_FIELDS.items()},
        'status': status, 'failures': failures}
    if prepared['diagnostics_artifact_ref'] is None:
        prepared['diagnostics_artifact_ref'] = retained['caller_diagnostics_artifact_ref']
    _immutable(directory / 'preparation.json', prepared)
    _validate_preparation(store, context, prepared)
    return prepared


def _validate_preparation(store, context, preparation):
    expected = {'version', 'calculation_id', 'bundle_artifact_ref', 'capture_artifact_ref', 'worker_manifest_artifact_ref',
        'source_grading_artifact_ref', 'status', 'failures', *_ARTIFACT_FIELDS.values()}
    if type(preparation) is not dict or set(preparation) != expected or preparation['version'] != PREPARATION_VERSION:
        raise ContractError('native_blast_standard_database_preparation_invalid')
    _original_commission(store, context)
    envelope = _json(store, preparation['source_grading_artifact_ref'])
    if (envelope.get('schema') != 'tool_grading_artifact_v1' or envelope.get('provider') != 'episode.execution_result'
            or envelope.get('native_artifact_ref') != preparation['bundle_artifact_ref']):
        raise ContractError('native_blast_standard_database_grading_custody_conflict')
    grading = envelope['grading']
    intent = _json(store, grading['intent_artifact_ref'])
    if (intent['run_id'] != context.run_id or intent['episode_id'] != context.episode_id
            or intent['scope'] != plain(context.scope) or intent['assignment'] != plain(context.assignment)):
        raise ContractError('native_blast_standard_database_preparation_owner_conflict')
    capture = _json(store, preparation['capture_artifact_ref'])
    if capture != intent['capture'] or grading['capture_artifact_ref'] != preparation['capture_artifact_ref']:
        raise ContractError('native_blast_standard_database_preparation_capture_conflict')
    _validate_capture(store, capture, target=intent['target'])
    witness = _json(store, grading['authenticated_attempt_artifact_ref'])
    attempt = _attempt(intent['target'], witness)
    _original_handoff(store, context, intent['target'], attempt)
    bundle = validate_standard_blast_database_bundle(_json(store, preparation['bundle_artifact_ref']),
        original_job=intent['target']['assignment']['requested_job']['native_blast_standard_database'], attempt_identity=attempt)
    plan = _json(store, capture['plan_artifact_ref'])
    if bundle['plan'] != plan or digest(plan) != attempt['plan_sha256']:
        raise ContractError('native_blast_standard_database_frozen_plan_conflict')
    bykey = {r['artifact_key']: r for r in bundle['artifacts']}
    if capture['status'] == 'complete' and set(capture['artifact_refs']) != set(bykey):
        raise ContractError('native_blast_standard_database_frozen_capture_completeness_conflict')
    for key, ref in capture['artifact_refs'].items():
        _retained(store, ref, sha256=bykey[key]['sha256'], size_bytes=bykey[key]['size_bytes'])
    request = _json(store, grading['request_artifact_ref'])
    selector = validate_standard_blast_database_selector(intent['selector'], program=bundle['program'])
    validate_standard_blast_selected_inputs(store, context, selector)
    if (request['calculation_id'] != preparation['calculation_id'] or request['bundle'] != bundle
            or request['authenticated_attempt'] != attempt or request['bundle_artifact_ref'] != preparation['bundle_artifact_ref']
            or selector != plain(context.assignment)['selector']
            or request['metadata_descriptors'] != _metadata_descriptors(bundle, capture, selector)
            or request['sequence_model'] != bundle['requested_job']['native_blast_standard_database']['grading_parameters']['sequence_database_model']):
        raise ContractError('native_blast_standard_database_frozen_request_conflict')
    expected_artifacts = [dict(artifact_key=row['artifact_key'], artifact_ref=capture['artifact_refs'][row['artifact_key']],
        sha256=row['sha256'], size_bytes=row['size_bytes']) for row in bundle['artifacts'] if row['artifact_key'] in capture['artifact_refs']]
    if [{k: v for k, v in row.items() if k != 'path'} for row in request['artifacts']] != expected_artifacts:
        raise ContractError('native_blast_standard_database_frozen_artifact_association_conflict')
    expected_retained = _retained_catalog(store, selector, request['artifacts'], request['subject_snapshots'])
    if [{k: v for k, v in row.items() if k != 'path'} for row in request['retained_sources']] != [
            {k: v for k, v in row.items() if k != 'path'} for row in expected_retained]:
        raise ContractError('native_blast_standard_database_frozen_selected_source_conflict')
    known = _known(store, context)
    for row in [*request['artifacts'], *request['retained_sources']]:
        _retained(store, row['artifact_ref'], sha256=row['sha256'], size_bytes=row['size_bytes'])
    for row in request['subject_snapshots']:
        if row['subject_ref'] not in known or not store.reference_subset([row['subject_ref']], plain(context.scope)):
            raise ContractError('native_blast_standard_database_frozen_subject_authority_conflict')
        _retained(store, row['sequence_artifact_ref'], sha256=row['sequence_sha256'], size_bytes=row['length'])
    _json(store, grading['worker_receipt_artifact_ref'])
    for ref in grading['worker_log_artifact_refs']:
        _retained(store, ref)
    for ref in grading.get('unsealed_artifact_refs', {}).values():
        _retained(store, ref)
    if grading['caller_diagnostics_artifact_ref'] is not None:
        _json(store, grading['caller_diagnostics_artifact_ref'])
    manifest = None
    if preparation['worker_manifest_artifact_ref'] is not None:
        if preparation['worker_manifest_artifact_ref'] != grading['manifest_artifact_ref']:
            raise ContractError('native_blast_standard_database_frozen_manifest_conflict')
        manifest = _manifest(store, preparation['worker_manifest_artifact_ref'], request, grading['artifact_refs'])
    for role, field in _ARTIFACT_FIELDS.items():
        expected_ref = grading['artifact_refs'].get(role)
        if role == 'diagnostics' and expected_ref is None:
            expected_ref = grading['caller_diagnostics_artifact_ref']
        if preparation[field] != expected_ref:
            raise ContractError('native_blast_standard_database_frozen_artifact_association_conflict')
        if expected_ref is not None:
            _retained(store, expected_ref)
    validate_schema(preparation['failures'], standard_blast_database_fact_sources()['execution_blast_standard_database_failures']['report_schema'])
    failures, status = _preparation_failures(manifest, grading['caller_failure'], capture)
    if preparation['failures'] != failures or preparation['status'] != status:
        raise ContractError('native_blast_standard_database_frozen_preparation_outcome_conflict')
    return {'grading': grading, 'request': request, 'bundle': bundle, 'capture': capture,
        'manifest': manifest, 'observation': _json(store, grading['observation_artifact_ref'])}


def _full_rows(store, prepared, frozen):
    if prepared['full_rows_artifact_ref'] is None:
        return []
    raw = _retained(store, prepared['full_rows_artifact_ref']).read_bytes()
    rows, offsets, position = [], [], 0
    for line in raw.splitlines(keepends=True):
        row = _decode(line); rows.append(row)
        offsets.append(dict(family=row['family'], record_key=row['record_key'], ordinal=len(rows)-1,
            byte_start=position, byte_end=position + len(line))); position += len(line)
    index = _json(store, prepared['row_index_artifact_ref'])
    if index != dict(schema='native_blast_standard_database_row_index_v1', calculation_id=prepared['calculation_id'], rows=offsets):
        raise ContractError('native_blast_standard_database_frozen_row_index_conflict')
    if frozen['manifest']['counts']['numerical_rows'] != len(rows):
        raise ContractError('native_blast_standard_database_frozen_row_count_conflict')
    return rows


def _projection(store, context, preparation, selector):
    frozen = _validate_preparation(store, context, preparation)
    selector = validate_standard_blast_database_selector(selector, program=frozen['bundle']['program'])
    intent = _json(store, frozen['grading']['intent_artifact_ref'])
    if selector != intent['selector'] or selector != plain(context.assignment)['selector']:
        raise ContractError('native_blast_standard_database_original_selector_conflict')
    rows = _full_rows(store, preparation, frozen)
    projected = project_standard_blast_database_rows(rows, selector=selector, calculation_id=preparation['calculation_id'])
    return frozen, projected


class _QueryQualification(ValueError):
    """A usable numerical row lacks a proved biological query relation."""


def _one(values, reason):
    if len(values) != 1:
        raise _QueryQualification(reason)
    return values[0]


def _master_relation(store, inputs, calculations, query, axis):
    if axis != 'pssm_master':
        raise _QueryQualification('master_axis_unavailable')
    relation = _one([r for item in inputs['metadata'] if item['consumer'] == 'query_identity'
        and item['status'] == 'valid' and item['normalized'] is not None
        for r in item['normalized']['master_subjects'] if r['kind'] == 'pssm'
        and r['input_key'] == query['input_key'] and r['record_ordinal'] == query['record_ordinal']],
        'master_subject_relation_unresolved')
    if relation['subject_ref'] != query['subject_ref'] or relation['sequence_sha256'] != query['sequence_sha256']:
        raise _QueryQualification('master_subject_relation_conflict')
    source = store.get(relation['source']['source_ref'])
    if source['record_type'] != 'source':
        raise _QueryQualification('master_relation_source_record_unavailable')
    sheet = _one([s for s in inputs['pssm_sheets'] if s['artifact_key'] == query['artifact_key']],
        'master_positional_map_unavailable')
    original = _one([r for r in sheet['pssms'] if r['record_ordinal'] == query['record_ordinal']],
        'master_positional_map_unavailable')
    matrix = _one([r for item in calculations['pssm'] if item['artifact_key'] == query['artifact_key'] and item['components'] is not None
        for r in item['components']['matrices'] if r['pssm_key'] == original['pssm_key']
        and r['record_ordinal'] == query['record_ordinal']], 'master_positional_map_unavailable')
    master = matrix['master']
    if (master['status'] != 'complete' or master['sequence'] != query['sequence']
            or master['decoded_length'] != query['length'] or master['reported_length'] != query['length']
            or matrix['dimensions']['positions'] != query['length']
            or master['column_to_residue'] != [dict(column=i, master_position=i, symbol=s)
                for i, s in enumerate(query['sequence'])]):
        raise _QueryQualification('master_positional_map_conflict')
    return source['id']


def _at(value, pointer):
    """Resolve an exact frozen JSON pointer; no parser or calculator is called."""
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ContractError('native_blast_standard_database_frozen_component_pointer_invalid')
    try:
        for token in pointer.split('/')[1:]:
            token = token.replace('~1', '/').replace('~0', '~')
            if isinstance(value, list):
                if not token.isdecimal() or str(int(token)) != token:
                    raise ValueError
                value = value[int(token)]
            else:
                value = value[token]
    except (ValueError, KeyError, TypeError, IndexError) as error:
        raise ContractError('native_blast_standard_database_frozen_component_pointer_invalid') from error
    return value


def _qualified_hsp(calculations, sheets, key, full_row, query):
    qualified = _one([r for r in calculations['qualified_hsp_components'] if r['row_key'] == key],
        'qualified_hsp_unresolved')
    if qualified['status'] != 'available' or qualified['component_pointer'] is None:
        raise _QueryQualification('qualified_hsp_unavailable')
    matches = [(i, r) for i, r in enumerate(calculations['sequence']) if r['search_key'] == key['search_key']]
    index, sequence = _one(matches, 'qualified_search_unresolved')
    if sequence['components'] is None:
        raise _QueryQualification('qualified_search_unavailable')
    base = '/sequence/' + str(index) + '/components'
    components = sequence['components']['components']
    hit_key = dict(key, hsp_ordinal=None, description_ordinal=None)
    hit = _one([r for r in components['row_keys']['hits'] if r['row_key'] == hit_key], 'qualified_hit_unresolved')
    hsp = _one([r for r in hit['hsps'] if r['row_key'] == key], 'qualified_hsp_unresolved')
    pointer = base + '/components/database_sheet/hits/' + str(hit['component_index']) + '/hsp_components/' + str(hsp['component_index'])
    references = [(i, r) for i, r in enumerate(components['coordinate_context']['references']) if r['row_key'] == hit_key]
    reference_index, _ = _one(references, 'qualified_reference_unresolved')
    if (qualified['sequence_component_pointer'] != base or qualified['component_pointer'] != pointer
            or qualified['query_binding_pointer'] != '/sequence/' + str(index) + '/sheet/query_binding'
            or qualified['reference_context_pointer'] != base + '/components/coordinate_context/references/' + str(reference_index)
            or sheets['sequence'][index]['search_key'] != key['search_key']):
        raise ContractError('native_blast_standard_database_frozen_qualified_pointer_conflict')
    binding = _at(sheets, qualified['query_binding_pointer'])
    if (binding is None or binding['full_length'] != query['length']
            or binding['sequence_sha256'] != query['sequence_sha256']
            or binding['operand']['subject_ref'] != query['subject_ref']):
        raise _QueryQualification('qualified_full_query_binding_unavailable')
    measured = _at(calculations, pointer)
    cells = {r['name']: r for r in full_row['measurements']}
    for axis in ('query', 'reference'):
        for name, group, field in (('qualified_paired_' + axis + '_units', 'counts', 'paired_' + axis + '_positions'),
                ('full_' + axis + '_paired_coverage', 'fractions', axis + '_paired_coverage')):
            cell = cells[name]
            if cell['value'] != measured[group].get(field) or cell['component_pointer'] != pointer + '/' + group + '/' + field:
                raise ContractError('native_blast_standard_database_frozen_qualified_cell_conflict')
            if group == 'fractions' and (cell['numerator'] != measured['counts'].get('paired_' + axis + '_positions')
                    or cell['denominator'] != measured['denominators'].get(axis + '_length')
                    or cell['complete'] != measured['geometry_available']):
                raise ContractError('native_blast_standard_database_frozen_qualified_cell_conflict')
    flag = _one([r for r in full_row['booleans'] if r['name'] == 'qualified_geometry_available'], 'qualified_geometry_flag_unavailable')
    if flag['value'] != measured['geometry_available'] or flag['component_pointer'] != pointer + '/geometry_available':
        raise ContractError('native_blast_standard_database_frozen_qualified_cell_conflict')
    return measured


def _hsp_payload(store, context, preparation, frozen, full_row, documents):
    """Qualify saved components and exact biological operands, without regrading."""
    inputs, collection, calculations, sheets = documents
    key = full_row['identity']['row_key']
    search = _one([r for r in collection['searches'] if r['search_key'] == key['search_key']], 'query_search_unresolved')
    operand = search['operand_binding']
    if operand is None:
        raise _QueryQualification('query_operand_unresolved')
    query = _one([r for r in inputs['query_records'] if r['artifact_key'] == operand['artifact_key']
        and r['record_ordinal'] == operand['record_ordinal']], 'query_operand_unresolved')
    if (query['binding_status'] != 'available' or query['subject_ref'] is None
            or operand['subject_ref'] != query['subject_ref']):
        raise _QueryQualification('query_subject_identity_unresolved')
    snapshot = _one([r for r in frozen['request']['subject_snapshots'] if r['subject_ref'] == query['subject_ref']],
        'query_subject_snapshot_unavailable')
    subject = store.get(query['subject_ref'])
    from .alignment_site_native import immutable_record
    from .native_hmmer_result_publication import _subject_chunks
    immutable_record(subject)
    actual_digest, actual_length = hashlib.sha256(), 0
    for chunk in _subject_chunks(store, subject['id']):
        chunk = chunk.encode('ascii') if isinstance(chunk, str) else chunk
        actual_digest.update(chunk); actual_length += len(chunk)
    if (subject['record_type'] != snapshot['record_type']
            or actual_length != snapshot['length'] or actual_length != query['length']
            or store.subject_molecule(subject['id']) != query['molecule'] or snapshot['molecule'] != query['molecule']
            or actual_digest.hexdigest() != snapshot['sequence_sha256']
            or snapshot['sequence_sha256'] != query['sequence_sha256']
            or hashlib.sha256(query['sequence'].encode('ascii')).hexdigest() != query['sequence_sha256']
            or _retained(store, snapshot['sequence_artifact_ref']).read_bytes() != query['sequence'].encode('ascii')):
        raise _QueryQualification('complete_query_sequence_identity_conflict')
    axis, reference_axis = (full_row['context'][k] for k in ('query_axis_kind', 'reference_axis_kind'))
    if (axis not in {'sequence', 'pssm_master'}
            or reference_axis != 'sequence'):
        raise _QueryQualification('native_axis_identity_unresolved')
    relation_source = None if axis == 'sequence' else _master_relation(store, inputs, calculations, query, axis)
    component = _one([r for r in calculations['native_hsp_components'] if r['row_key'] == key], 'native_hsp_component_unresolved')
    measured = _qualified_hsp(calculations, sheets, key, full_row, query)
    if (component['status'] != 'available' or not measured['geometry_available']
            or not measured['traceback_available'] or not measured['pairs']
            or search['program_context']['geometry_program'] is None):
        raise _QueryQualification('complete_query_geometry_unavailable')
    spans = []
    for pair in measured['pairs']:
        start, end = pair['query_start'], pair['query_end']
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= query['length']:
            raise _QueryQualification('query_geometry_outside_complete_subject')
        if query['selected_interval'] is not None and not query['selected_interval'][0] <= start < end <= query['selected_interval'][1]:
            raise _QueryQualification('query_geometry_outside_selected_interval')
        spans.append((start, end))
    merged = []
    for start, end in sorted(set(spans)):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    if (not store.reference_subset([subject['id']], plain(context.scope))
            or not store.has_exact_mapping(subject['id'])):
        raise _QueryQualification('query_original_mapping_unavailable')
    segments = [dict(start=a, end=b) for a, b in merged]
    if not store.scope_covers(store.map_segments(subject['id'], segments), plain(context.scope)):
        raise _QueryQualification('query_geometry_outside_assigned_scope')
    names = dict(native_score_bits='native_score_bits', native_raw_score='native_raw_score', native_evalue='native_evalue',
        alignment_columns='alignment_columns', paired_columns='paired_positions', query_gap_columns='query_gap_columns',
        reference_gap_columns='reference_gap_columns', qualified_paired_query_units='query_aligned_positions',
        identical_pairs='identical_positions', paired_identity='paired_identity',
        alignment_identity='alignment_identity', qualified_paired_reference_units='reference_aligned_positions')
    values = [dict(name=names[cell['name']], value=dict(type='number', value=cell['value'], unit_ref=None))
        for cell in full_row['measurements'] if cell['name'] in names and cell['status'] == 'available'
        and type(cell['value']) in (int, float) and math.isfinite(cell['value'])]
    if not values:
        raise _QueryQualification('native_hsp_measurements_unavailable')
    payload = dict(subject_refs=[subject['id']], source_subject_refs=[], source_ref=identity('source',
        {'origin': 'tool', 'record': _source_payload(frozen['bundle'], frozen['capture'])}),
        kind='comparison', measurements=values,
        dependencies=[], anchor=None, operand_intervals=[dict(role='query', subject_ref=subject['id'],
            start=a, end=b, unit=store.subject_unit(subject['id']), model_unit=measured['coordinate_units']['alignment']) for a, b in merged],
        native_blast_standard_database=dict(version='native_blast_standard_database_observation_v1', program=full_row['program'],
            record_key=full_row['record_key'], search_key=key['search_key'], hit_ordinal=key['hit_ordinal'],
            hsp_ordinal=key['hsp_ordinal'], bundle_artifact_ref=preparation['bundle_artifact_ref'],
            query_axis_kind=axis, reference_axis_kind=reference_axis))
    payload['dependencies'] = list(dict.fromkeys([payload['source_ref'], subject['id'], *([relation_source] if relation_source else [])]))
    return payload


def _published_rows(store, context, preparation, frozen, projected, *, publish):
    """The same frozen projection proves writes and byte-exact read-only replay."""
    source = identity('source', {'origin': 'tool', 'record': _source_payload(frozen['bundle'], frozen['capture'])})
    all_rows = {(r['family'], r['record_key']): r for r in _full_rows(store, preparation, frozen)}
    documents = None
    if projected['families'] and any(f['family'] == 'hsp' and f['rows'] for f in projected['families']):
        refs = frozen['grading']['artifact_refs']
        documents = tuple(_json(store, refs[role]) for role in ('inputs', 'collection', 'calculations', 'sheets'))
    rows, references, failures, diagnostics = {}, [source], [], []
    for family in projected['families']:
        items = rows[family['family']] = []
        for selected in family['rows']:
            row = dict(**selected, source_ref=source, observation_ref=None, subject_ref=None,
                reference_refs=[], publication_status='source_only')
            if family['family'] == 'hsp':
                try:
                    payload = _hsp_payload(store, context, preparation, frozen,
                        all_rows[('hsp', selected['record_key'])], documents)
                except _QueryQualification as error:
                    diagnostics.append(dict(record_key=selected['record_key'], reason=str(error)))
                    failures.append(_failure('publication', 'native_blast_standard_database_query_unbound', 'query_identity_unresolved',
                        record_key=selected['record_key'], search_key=selected['identity']['row_key']['search_key'],
                        pointer='/grading/publication_diagnostics/' + str(len(diagnostics) - 1)))
                else:
                    reference = identity('observation', {'origin': 'tool', 'record': payload})
                    if publish:
                        actual = store.put('observation', payload, origin='tool', scope=plain(context.scope))
                    else:
                        actual = store.get(reference)
                    expected = dict(**payload, id=reference, origin='tool', record_type='observation')
                    if canonical(actual) != canonical(expected):
                        raise ContractError('native_blast_standard_database_frozen_observation_conflict')
                    store._validate_record('observation', payload, 'tool')
                    row.update(observation_ref=reference, subject_ref=payload['subject_refs'][0], publication_status='published')
                    if reference not in references:
                        references.append(reference)
            items.append(row)
    return rows, references, failures, diagnostics


def _required_failures(failures):
    # Missing biological query identity qualifies source-only publication. It
    # does not prevent faithful acquisition of requested numerical cells.
    return [row for row in failures if row['code'] != 'native_blast_standard_database_query_unbound']


def publish_selected_standard_blast_database_rows(store, *, context, preparation, selector, directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / 'publication.json'
    if receipt.exists():
        return validate_standard_blast_database_publication(store, context=context, publication=_read(receipt))
    frozen, projected = _projection(store, context, preparation, selector)
    source = store.put('source', _source_payload(frozen['bundle'], frozen['capture']), origin='tool')['id']
    rows, records, qualifications, diagnostics = _published_rows(store, context, preparation, frozen, projected, publish=True)
    projection_failures = deepcopy(preparation['failures']) + deepcopy(projected['failures'])
    failures = projection_failures + qualifications
    acquisition = frozen['capture']['status'] == 'complete'
    # Unavailable numerical cells are legitimate; malformed selected metadata,
    # failed interpretation or a missing explicit row are incomplete requests.
    projection = (preparation['full_rows_artifact_ref'] is not None and not _required_failures(projection_failures))
    observation, bundle = frozen['observation'], frozen['bundle']
    native_success = (observation['state'] == 'completed' and observation['returncode'] == 0
        and bundle['process']['started'] and bundle['process']['returncode'] == 0 and not bundle['failures'])
    selected_ref = retain_tool_grading(store, provider='episode.execution_result', native_artifact_ref=preparation['bundle_artifact_ref'],
        grading={'schema': 'native_blast_standard_database_selected_grading_v1', 'projection': projected,
            'rows_by_family': rows, 'publication_diagnostics': diagnostics})
    value = dict(version=PUBLICATION_VERSION, calculation_id=preparation['calculation_id'], source_ref=source,
        preparation_artifact_ref=_json_artifact(store, preparation), selector=selector, selected_rows_artifact_ref=selected_ref,
        rows_by_family=rows, record_refs=records, acquisition_complete=acquisition, projection_complete=projection,
        native_execution_successful=native_success, complete=acquisition and projection and native_success, failures=failures)
    _immutable(receipt, value)
    return validate_standard_blast_database_publication(store, context=context, publication=value)


def validate_standard_blast_database_publication(store, *, context, publication):
    expected = {'version', 'calculation_id', 'source_ref', 'preparation_artifact_ref', 'selector', 'selected_rows_artifact_ref',
        'rows_by_family', 'record_refs', 'acquisition_complete', 'projection_complete', 'native_execution_successful', 'complete', 'failures'}
    if type(publication) is not dict or set(publication) != expected or publication['version'] != PUBLICATION_VERSION:
        raise ContractError('native_blast_standard_database_publication_invalid')
    prepared = _json(store, publication['preparation_artifact_ref'])
    frozen, projected = _projection(store, context, prepared, publication['selector'])
    payload = _source_payload(frozen['bundle'], frozen['capture'])
    expected_source = identity('source', {'origin': 'tool', 'record': payload})
    source = store.get(publication['source_ref'])
    if (publication['source_ref'] != expected_source or {k: v for k, v in source.items()
            if k not in {'id', 'record_type', 'origin'}} != payload or source['origin'] != 'tool'):
        raise ContractError('native_blast_standard_database_original_source_conflict')
    rows, records, qualifications, diagnostics = _published_rows(store, context, prepared, frozen, projected, publish=False)
    selected = _json(store, publication['selected_rows_artifact_ref'])
    if selected != {'schema': 'tool_grading_artifact_v1', 'provider': 'episode.execution_result',
            'native_artifact_ref': prepared['bundle_artifact_ref'], 'grading': {'schema': 'native_blast_standard_database_selected_grading_v1',
                'projection': projected, 'rows_by_family': rows, 'publication_diagnostics': diagnostics}}:
        raise ContractError('native_blast_standard_database_frozen_projection_conflict')
    projection_failures = deepcopy(prepared['failures']) + deepcopy(projected['failures'])
    failures = projection_failures + qualifications
    acquisition = frozen['capture']['status'] == 'complete'
    projection = prepared['full_rows_artifact_ref'] is not None and not _required_failures(projection_failures)
    observation, bundle = frozen['observation'], frozen['bundle']
    success = (observation['state'] == 'completed' and observation['returncode'] == 0
        and bundle['process']['started'] and bundle['process']['returncode'] == 0 and not bundle['failures'])
    comparison = dict(publication, calculation_id=prepared['calculation_id'], rows_by_family=rows, record_refs=records,
        acquisition_complete=acquisition, projection_complete=projection, native_execution_successful=success,
        complete=acquisition and projection and success, failures=failures)
    if canonical(publication) != canonical(comparison):
        raise ContractError('native_blast_standard_database_frozen_publication_conflict')
    descriptors = standard_blast_database_fact_sources()
    for family, items in rows.items():
        validate_schema(items, descriptors['execution_blast_standard_database_' + family + '_rows']['report_schema'])
    return deepcopy(publication)


def validate_standard_blast_database_observation(store, observation):
    """Resolve only actual completed actions and their exact frozen publications."""
    if (type(observation) is not dict or observation.get('record_type') != 'observation'
            or observation.get('origin') != 'tool' or not observation.get('native_blast_standard_database')):
        raise ContractError('native_blast_standard_database_observation_required')
    payload = {k: v for k, v in observation.items() if k not in {'id', 'origin', 'record_type'}}
    if observation['id'] != identity('observation', {'origin': 'tool', 'record': payload}):
        raise ContractError('native_blast_standard_database_frozen_observation_conflict')
    if not store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_actions'").fetchone():
        raise ContractError('native_blast_standard_database_original_publication_required')
    actions = store.db.execute("SELECT run_id,episode_id,decision_index,action,result FROM runtime_actions "
        "WHERE result IS NOT NULL AND json_extract(result,'$.result.version')='native_blast_standard_database_result_receipt_v1' "
        "AND EXISTS(SELECT 1 FROM json_each(runtime_actions.result,'$.record_refs') WHERE value=?) "
        "ORDER BY run_id,episode_id,decision_index", (observation['id'],))
    for action in actions:
        result, selected = json.loads(action['result']), json.loads(action['action'])
        body = result['result']
        if (result.get('status') != 'completed' or body['publication'] is None
                or selected != dict(kind='tool', tool='execution.results.collect', arguments={})
                or body['tool_name'] != selected['tool'] or body['arguments'] != selected['arguments']
                or body['operation_key'] != f"{action['run_id']}:{action['episode_id']}:{action['decision_index']}"
                or body['run_id'] != action['run_id'] or body['episode_id'] != action['episode_id']
                or body['record_refs'] != result['record_refs']):
            raise ContractError('native_blast_standard_database_original_publication_conflict')
        authority = EpisodeReturnRecords(store, action['run_id'], failure_prefix='native_blast_standard_database_observation_')
        context = authority.context(action['episode_id'])
        if context.role != 'results' or plain(context.assignment) != body['assignment'] or plain(context.scope) != body['scope']:
            raise ContractError('native_blast_standard_database_original_publication_conflict')
        publication = validate_standard_blast_database_publication(store, context=context, publication=body['publication'])
        if (publication['record_refs'] != body['record_refs'] or publication['failures'] != body['failures']
                or _json(store, publication['preparation_artifact_ref']) != body['preparation']):
            raise ContractError('native_blast_standard_database_original_publication_conflict')
        for row in publication['rows_by_family'].get('hsp', []):
            if row['observation_ref'] == observation['id']:
                if canonical(store.get(observation['id'])) != canonical(observation):
                    raise ContractError('native_blast_standard_database_frozen_observation_conflict')
                prepared = body['preparation']
                frozen = _validate_preparation(store, context, prepared)
                if body['capture'] != frozen['capture'] or body['observation'] != frozen['observation']:
                    raise ContractError('native_blast_standard_database_original_publication_conflict')
                return deepcopy(_one([r for r in _full_rows(store, prepared, frozen) if r['family'] == 'hsp'
                    and r['record_key'] == row['record_key']], 'frozen_original_hsp_unavailable'))
    raise ContractError('native_blast_standard_database_original_publication_required')


__all__ = ['validate_standard_blast_job_inputs', 'validate_standard_blast_selected_inputs', 'prepare_standard_blast_database_grading', 'publish_selected_standard_blast_database_rows',
    'validate_standard_blast_database_publication', 'validate_standard_blast_database_observation']
