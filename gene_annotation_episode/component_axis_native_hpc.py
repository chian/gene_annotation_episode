"""Frozen component requests and scientific admission via the shared HPC owner.

No scheduler, launcher, native calculation or scientific scalar reducer lives
here. Only authenticated received HPC result documents can publish components.
"""
from copy import deepcopy
import base64
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import zlib

from .communication import plain
from .domain import ContractError, canonical
from .component_axis_native_contracts import VERSION, OPERATIONS, PROFILES
from .component_axis_native_worker import PROGRAM
from .tool_grading_artifacts import retain_tool_grading, source_tool_grading_entries
from .hpc_result_receipts import planned_input_files


REQUEST_PROVIDER = 'host.component_axis.native_request'
RESULT_PROVIDER = 'host.component_axis.native_components'
STATUS_PROVIDER = 'host.component_axis.native_execution'
FACT_SOURCE = 'component_axis_native_component_records'
EXECUTION_SOURCE = 'component_axis_native_execution_records'
MAX_INPUT_BYTES = 8*1024**2
MAX_RESULT_BYTES = 32*1024**2
SOURCE_FILES = {
    'A107': ('component_axis_native_contracts.py', 'a107_expression_contracts.py', 'a107_expression_components.py'),
    'A110': ('component_axis_native_contracts.py', 'a110_chemical_contracts.py',
        'a110_chemical_accounting.py', 'literature_reaction_calculations.py', 'literature_experimental_contracts.py'),
}


def scientific_profile(body):
    return body['scientific_profile'] if 'scientific_profile' in body else PROFILES[body['axis']]


def provenance(store, references):
    """Snapshot actual input-witness metadata without reading private source bytes."""
    fields = ('record_type', 'provider', 'accession', 'revision', 'version', 'artifact_ref',
        'text_ref', 'request_ref', 'parent_source_refs', 'operand_refs')
    return [{'reference': ref, 'identity': {key: deepcopy(record[key]) for key in fields if key in record}}
        for ref in sorted(set(references)) for record in [store.get(ref)]]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, code):
    if not condition:
        raise ContractError('component_native_'+code)


def install(store):
    for table in ('component_native_requests', 'component_native_outputs'):
        store.db.execute('CREATE TABLE IF NOT EXISTS '+table+' (source_ref TEXT PRIMARY KEY,body TEXT NOT NULL)')


def publish(store, provider, body):
    install(store)
    artifact = store.artifact(canonical(body), 'application/json')
    grading = retain_tool_grading(store, provider=provider, native_artifact_ref=artifact,
        grading={'grader': scientific_profile(body), 'failure': None,
            'sheet': body['native_components']}) if provider == RESULT_PROVIDER else None
    reference = store.put('source', {'provider': provider, 'accession': sha(canonical(body).encode()),
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': VERSION, 'retrieved_at': None, 'operand_refs': body['scope']['subject_refs'],
        **({'auxiliary_artifact_refs': [grading]} if grading is not None else {})}, origin='tool')['id']
    table = 'component_native_requests' if provider == REQUEST_PROVIDER else 'component_native_outputs'
    store.db.execute('INSERT OR IGNORE INTO '+table+' VALUES(?,?)', (reference, canonical(body)))
    return reference


def read(store, reference, provider):
    source = store.get(reference)
    if source.get('provider') != provider:
        return None
    table = 'component_native_requests' if provider == REQUEST_PROVIDER else 'component_native_outputs'
    exists = store.db.execute('SELECT 1 FROM sqlite_master WHERE name=?', (table,)).fetchone()
    saved = store.db.execute('SELECT body FROM '+table+' WHERE source_ref=?', (reference,)).fetchone() if exists else None
    require(saved is not None and source['origin'] == 'tool' and source['version'] == VERSION,
        'original_native_grant_required')
    body = json.loads(saved[0])
    require(json.loads(store.get_artifact(source['artifact_ref'])) == body, 'original_native_grant_conflict')
    if provider == RESULT_PROVIDER:
        entries = source_tool_grading_entries(store, reference)
        require(len(entries) == 1 and entries[0]['grading'] == {'grader': scientific_profile(body),
            'failure': None, 'sheet': body['native_components']}, 'original_native_grader_conflict')
    return body


def freeze(registry, axis, args, *, context, known, invocation):
    if invocation[2] == 'chemistry.request_flux_balance_hpc':
        from .a110_fba_hpc import freeze as freeze_fba
        return freeze_fba(registry, args, context=context, known=known, invocation=invocation)
    if invocation[2] == 'partner.request_detection_hpc':
        from .a107_genomic_detection_hpc import freeze as freeze_detection
        return freeze_detection(registry, args, context=context, known=known, invocation=invocation)
    store = registry.store
    require({args['target_ref'], args['source_ref']} <= known, 'original_operands_not_received')
    footprint = store.coverage(args['target_ref'])
    require(footprint and store.scope_covers(footprint, plain(context.scope)), 'target_outside_original_scope')
    roots = {row['target_ref'] for row in footprint}
    require(len(roots) == 1, 'single_original_target_required')
    require(args['source_ref'] in store.reference_subset([args['source_ref']], plain(context.scope)),
        'original_input_source_outside_scope')
    admission, path = invocation[1](context, args['source_ref'], 'source', file_format='json')
    if admission.get('failure') is not None or path is None:
        from .materials import source_window_selection
        artifact, _, _ = source_window_selection(store.get(args['source_ref']), 'original')
        raise ContractError('component_native_original_source_file_not_admitted', detail={
            'input_admission': True, 'failure': admission.get('failure'),
            'witness_ref': args['source_ref'], 'required_artifact_ref': artifact})
    file = admission['input']['file']
    require(file['size_bytes'] <= MAX_INPUT_BYTES, 'input_exceeds_coordinator_transfer_capacity; requires_explicit_large_file_staging')
    raw = path.read_bytes()
    require(len(raw) == file['size_bytes'] and sha(raw) == file['sha256'], 'original_source_bytes_conflict')
    # Admit the existing input contract before creating an executable grant.
    # This is bounded parsing/validation, not the scientific calculation.
    from jsonschema import ValidationError
    from .component_axis_native_contracts import load_json, source_schema, validate_source
    document = None
    try:
        document = load_json(raw)
        validate_source(axis, document)
    except (ValueError, ValidationError, UnicodeDecodeError) as error:
        raise ContractError('component_native_input_contract_mismatch', detail={
            'axis': axis, 'source_ref': args['source_ref'],
            'observed_version': document.get('version') if isinstance(document, dict) else None,
            'input_path': list(error.absolute_path) if isinstance(error, ValidationError) else [],
            'expected_source_schema': source_schema(axis),
            'recovery': 'Select an actually received source matching this operation input contract. '
                + ('A reaction-measurement dataset is not a chemical-equation panel. '
                    if axis == 'A110' else 'An expression request requires a supported declared expression table. ')
                + 'This input-format rejection establishes no biological opposition and creates no job.',
        }) from error
    directory = Path(__file__).parent
    sources = {'axis_native/'+name: (directory/name).read_text() for name in SOURCE_FILES[axis]}
    sources['axis_native/__init__.py'] = ''
    worker = (directory/'component_axis_native_worker.py').read_text()
    manifest = {name: sha(text.encode()) for name, text in sources.items()}
    manifest['component-worker.py'] = sha(worker.encode())
    snapshot = canonical(sources)+'\n'
    request = {'version': VERSION, 'axis': axis, 'operation': OPERATIONS[axis],
        'scientific_profile': PROFILES[axis], 'selection': deepcopy(args['selection']),
        'run_id': context.run_id, 'scope': plain(context.scope), 'target_ref': next(iter(roots)),
        'target_regions': footprint, 'resource_id': args['resource_id'],
        'jsonschema_version': version('jsonschema'),
        'input': {'file': file, 'bytes_base64': base64.b64encode(raw).decode()},
        'code_manifest': manifest, 'code_manifest_sha256': sha(canonical(manifest).encode()),
        'source_snapshot_sha256': sha(snapshot.encode())}
    request_raw = (canonical(request)+'\n').encode()
    body = {'version': VERSION, 'axis': axis, 'operation': OPERATIONS[axis],
        'scientific_profile': PROFILES[axis], 'run_id': context.run_id,
        'scope': plain(context.scope), 'target_ref': next(iter(roots)),
        'target_regions': footprint, 'source_ref': args['source_ref'], 'input_file': file,
        'request': request, 'request_sha256': sha(request_raw),
        'logical_work_sha256': sha(canonical({'axis': axis, 'input_sha256': file['sha256'],
            'selection': args['selection'], 'profile': PROFILES[axis], 'code': manifest}).encode()),
        'worker_sha256': manifest['component-worker.py'],
        'code_manifest_sha256': request['code_manifest_sha256'], 'resource_id': args['resource_id'],
        'evidence_refs': sorted({args['target_ref'], args['source_ref']}),
        'files': {'component-worker.py': worker, 'component-sources.json': snapshot,
            'component-request.json': request_raw.decode()},
        'input_admission': admission, 'input_provenance': provenance(store, [args['source_ref']]),
        'arguments_sha256': sha(canonical(args).encode()),
        'scientific_credit': None}
    reference = publish(store, REQUEST_PROVIDER, body)
    return reference, body


def commission(body, resources):
    from .hpc_scientific_commission import commission as describe
    return describe(resource_id=body['resource_id'], resource=resources[body['resource_id']],
        tool=body['operation'], request_sha256=body['request_sha256'],
        worker_sha256=body['worker_sha256'], implementation_sha256=body['code_manifest_sha256'],
        parameters={'axis': body['axis'], 'selection': body['request']['selection']}, files=body['files'],
        worker_name='component-worker.py', request_name='component-request.json',
        program=PROGRAM, version=VERSION,
        features={'input_bytes': body['input_file']['size_bytes'], **body.get('features', {})},
        preparation=body.get('preparation', 'Prepare and execute this declared source-component analysis. '
            'Choose the scripts, environment and commands needed for its jsonschema '
            +body['request']['jsonschema_version']+' dependency, keeping preparation files within the '
            'assigned workspace. Preserve the original scientific inputs, software identity and '
            'output contract. Scientific computation runs on allocated compute nodes and retains '
            'its original result in HPC_UNIT_DIRECTORY.'),
        objective='Calculate exactly the selected '+body['axis']+' source components. Preserve partial '
            'results, actual native quantities, missing inputs, source identity and dependence. No '
            'particular scientific answer is expected. Return the original authenticated result '
            'sources through hpc_result_refs for success, partial results and failure alike; '
            'operational rejection does not make the original failure receipt unreturnable. '
            'The scientific parent owns revisions to the input or scientific selection. This '
            'commission preserves its frozen inputs; reading a failed result again cannot '
            'repair them. Operational acceptance is not scientific credit.')


def admit(registry, expected, hpc_ref, *, context, known, reader):
    store = registry.store
    require(expected['run_id'] == context.run_id and set(expected['evidence_refs']) <= known,
        'original_run_and_received_operands_required')
    authority = reader(context, hpc_ref)
    receipt, plan, unit = authority['receipt'], authority['plan'], authority['unit']
    result, workspace = receipt['document'], plan['manifest']['workspace']
    require(receipt['scope'] == expected['scope'], 'original_hpc_scope_conflict')
    staged = {row['path']: row for row in planned_input_files(plan)}
    require(all(workspace+'/'+name in staged and staged[workspace+'/'+name]['sha256'] == sha(text.encode())
        for name, text in expected['files'].items()), 'original_staged_files_conflict')
    require(authority['resource_id'] == expected['resource_id'] and unit['argv'] == [
        authority['resource']['python_executable'], '-B', workspace+'/component-worker.py',
        workspace+'/component-request.json'], 'original_native_command_conflict')
    require(result.get('program') == PROGRAM and result.get('version') == VERSION
        and result.get('request_sha256') == expected['request_sha256']
        and result.get('worker_sha256') == expected['worker_sha256']
        and result.get('code_manifest_sha256') == expected['code_manifest_sha256']
        and result.get('pbs_job_id') == receipt['job_id'] and result.get('compute_hostname')
        and not result['compute_hostname'].startswith(('aurora-uan', 'login')), 'original_native_identity_conflict')
    require(result['returncode'] == receipt['unit']['returncode'], 'execution_outcome_conflict')
    common = {'version': VERSION, 'axis': expected['axis'], 'scope': expected['scope'], 'run_id': context.run_id,
        'operation': expected['operation'], 'scientific_profile': scientific_profile(expected),
        'request_ref': expected['request_ref'], 'logical_work_sha256': expected['logical_work_sha256'],
        'hpc_result_ref': hpc_ref, 'hpc_source_artifact_ref': authority['source_artifact_ref'],
        'pbs_job_id': receipt['job_id'], 'input_source_ref': expected['source_ref'],
        'input_file': expected['input_file'], 'target_ref': expected['target_ref'],
        'input_provenance': deepcopy(expected['input_provenance']),
        'target_regions': expected['target_regions'], 'python_version': result.get('python_version'),
        'scientific_credit': None}
    if not result['completed']:
        require(result['returncode'] != 0 and result.get('failure'), 'original_failure_reason_required')
        return publish(store, STATUS_PROVIDER, {**common, 'status': 'native_execution_failed',
            'failure': result['failure']})
    require(result['returncode'] == 0 and result['axis'] == expected['axis']
        and result['scientific_profile'] == scientific_profile(expected)
        and result['jsonschema_version'] == expected['request']['jsonschema_version']
        and result['input_sha256'] == expected['input_file']['sha256']
        and result['payload_encoding'] == 'zlib_base64', 'qualified_native_components_required')
    decoder = zlib.decompressobj()
    raw = decoder.decompress(base64.b64decode(result['payload'], validate=True), MAX_RESULT_BYTES)
    require(decoder.eof and not decoder.unconsumed_tail and not decoder.unused_data
        and sha(raw) == result['payload_sha256'], 'original_native_payload_conflict')
    native = json.loads(raw)
    require(native['version'] == scientific_profile(expected)
        and native['selection'] == expected['request']['selection'], 'original_scientific_selection_conflict')
    if scientific_profile(expected) == 'a110_flux_balance_hpc_v2':
        require(native['software']['selected_manifest_sha256'] == sha(canonical(
            expected['request']['binding']['software']).encode()), 'original_fba_software_manifest_conflict')
        require('native_outcome' not in native, 'unselected_full_fba_result_not_admitted')
    if scientific_profile(expected) == 'a107_genomic_detection_v1':
        from .a107_genomic_detection_native import validate_reference_translations
        require(native['query_sequence_sha256'] == expected['request']['query_sequence_sha256']
            and native['database_sha256'] == expected['input_file']['sha256']
            and native['software']['sha256'] == expected['request']['binding']['sha256']
            and native['software']['biopython_version'] == expected['request']['biopython_version']
            and native['detection']['component_ref'] == expected['request']['component_ref']
            and native['detection']['native_database_sha256'] == native['database_sha256']
            and native['detection']['native_search_complete'] is True,
            'a107_original_search_and_detector_identity_conflict')
        validate_reference_translations(native, expected['request'])
    return publish(store, RESULT_PROVIDER, {**common, 'status': 'scientifically_admitted',
        'scientific_admission': 'original_input_and_fixed_algorithm_custody; source_assertions_not_independently_verified',
        'native_components': native, 'native_payload_sha256': sha(raw),
        'dependencies': {'input_sha256': expected['input_file']['sha256'],
            'dataset_id': native['dataset_id'], 'origin': native['origin'],
            'origin_source_refs': sorted({row['reference'] for row in expected['input_provenance']
                if row['identity'].get('record_type') == 'source'} | {ref for row in expected['input_provenance']
                    for ref in row['identity'].get('parent_source_refs', [])}),
            'independence': 'not_inferred_from_distinct_sources_or_missing_dataset_identity'},
        'target_transfer': 'no_automatic_mapping_from_table_features_or_reaction_to_submitted_target'})


def receive(registry, context, known, *, reader):
    requests = {}
    for ref in known:
        body = read(registry.store, ref, REQUEST_PROVIDER)
        if body is not None and body['run_id'] == context.run_id:
            # Keep only addresses while inspecting the receipt inventory; frozen
            # source/code/input byte copies need not accumulate in memory.
            requests[body['request_sha256']] = ref
    completed = {(body['request_ref'], body['hpc_result_ref']) for ref in known
        if (body := read(registry.store, ref, RESULT_PROVIDER)) is not None}
    completed.update((body['request_ref'], body['hpc_result_ref']) for ref in known
        if (body := read(registry.store, ref, STATUS_PROVIDER)) is not None
        and body['status'] == 'native_execution_failed')
    generated, needs = [], []
    requests_by_arguments = {body.get('arguments_sha256') for ref in known
        if (body := read(registry.store, ref, REQUEST_PROVIDER)) is not None and body['run_id'] == context.run_id}
    for reference in sorted(known):
        body = read(registry.store, reference, STATUS_PROVIDER)
        if body is None or body.get('run_id') != context.run_id or body['status'] != 'input_admission_unavailable' or body.get(
                'arguments_sha256') in requests_by_arguments:
            continue
        if context.role == 'scientific_process' and context.assignment.get('selection', {}).get(
                'evidence_axis', {}).get('option_id') != body['axis']:
            continue
        if not registry.store.scope_contains(plain(context.scope), body['scope']):
            continue
        needs.append((reference, {'target_ref': body['target_ref'], 'policy': body['operation'],
            'missing': ['actual_input_file_admission:'+str(body['failure'])],
            'required_operands': {'source_refs': [body['witness_ref']],
                'artifact_refs': [] if body['required_artifact_ref'] is None else [body['required_artifact_ref']]}}))
    for ref in sorted(known):
        record = registry.store.get(ref)
        if record.get('provider') != 'episode.hpc_result':
            continue
        document = json.loads(registry.store.get_artifact(record['artifact_ref'])).get('document', {})
        request_ref = requests.get(document.get('request_sha256'))
        if document.get('program') != PROGRAM or request_ref is None or (request_ref, ref) in completed:
            continue
        expected = {**read(registry.store, request_ref, REQUEST_PROVIDER), 'request_ref': request_ref}
        if context.role == 'scientific_process' and context.assignment.get('selection', {}).get(
                'evidence_axis', {}).get('option_id') != expected['axis']:
            continue
        missing = set(expected['evidence_refs'])-known
        if missing:
            body = {'version': VERSION, 'axis': expected['axis'], 'scope': expected['scope'], 'run_id': context.run_id,
                'request_ref': expected['request_ref'], 'hpc_result_ref': ref,
                'status': 'pending_original_operands', 'missing_record_refs': sorted(missing), 'scientific_credit': None}
            generated.append(publish(registry.store, STATUS_PROVIDER, body))
            needs.append((expected['request_ref'], {'target_ref': expected['target_ref'],
                'policy': 'component_axis_received_native_inputs', 'missing': ['original_received_source_operands'],
                'required_operands': {'source_refs': sorted(missing)}}))
            continue
        try:
            with registry.store.transaction():
                generated.append(admit(registry, expected, ref, context=context, known=known, reader=reader))
        except (ValueError, KeyError, OSError, TypeError) as error:
            generated.append(publish(registry.store, STATUS_PROVIDER, {'version': VERSION,
                'axis': expected['axis'], 'scope': expected['scope'], 'run_id': context.run_id, 'request_ref': expected['request_ref'],
                'hpc_result_ref': ref, 'status': 'scientific_admission_unavailable',
                'reason': str(error), 'scientific_credit': None}))
    return list(dict.fromkeys(generated)), needs


def received_components(store, references, scope, *, axis=None, compact=True, known=None):
    known = set(references if known is None else known)
    rows = []
    for reference in sorted(set(references)):
        body = read(store, reference, RESULT_PROVIDER)
        if body is None or axis is not None and body['axis'] != axis:
            continue
        if not store.scope_contains(plain(scope), body['scope']):
            continue
        row = {'source_ref': reference, 'artifact_ref': store.get(reference)['artifact_ref'], **deepcopy(body)}
        changed = []
        for witness in row['input_provenance']:
            if witness['reference'] in known:
                current = store.get(witness['reference'])
                if any(current.get(key) != value for key, value in witness['identity'].items()):
                    changed.append(witness['reference'])
        row['changed_received_input_metadata_refs'] = changed
        row['input_snapshot_status'] = 'received_input_metadata_changed; historical_bytes_retained' if changed else (
            'no_change_in_actually_received_input_metadata; unknown_unreceived_revisions')
        if compact and row['axis'] == 'A107' and 'pairs' in row['native_components']:
            pairs = row['native_components'].pop('pairs')
            row['native_components']['pairs_retained'] = {'count': len(pairs), 'source_ref': reference,
                'artifact_ref': row['artifact_ref'], 'pointer': '/native_components/pairs',
                'preview': pairs[:8], 'complete_native_pairs_preserved': True}
            for side, criteria in row['native_components'].get('detection_criteria', {}).items():
                row['native_components']['detection_criteria'][side] = {'count': len(criteria),
                    'source_ref': reference, 'artifact_ref': row['artifact_ref'],
                    'pointer': '/native_components/detection_criteria/'+side, 'preview': criteria[:4],
                    'complete_native_criteria_preserved': True}
        if compact and row.get('scientific_profile') == 'a107_genomic_detection_v1':
            for name, artifact in row['native_components']['native_artifacts'].items():
                artifact.pop('bytes_base64')
                artifact.update(source_ref=reference, artifact_ref=row['artifact_ref'],
                    pointer='/native_components/native_artifacts/'+name,
                    availability='complete_original_native_bytes_retained_in_this_received_publication')
        rows.append(row)
    return rows


def execution_findings(store, references, scope, *, axis=None):
    rows = []
    for reference in sorted(set(references)):
        body = read(store, reference, STATUS_PROVIDER)
        if body is None and (request := read(store, reference, REQUEST_PROVIDER)) is not None:
            body = {'version': VERSION, 'axis': request['axis'], 'scope': request['scope'], 'run_id': request['run_id'],
                'request_ref': reference, 'hpc_result_ref': None, 'status': 'native_work_requested',
                'logical_work_sha256': request['logical_work_sha256'], 'resource_id': request['resource_id'],
                'arguments_sha256': request.get('arguments_sha256'),
                'selection': deepcopy(request['request']['selection']),
                'scientific_credit': None, 'meaning': 'no_native_result_admitted_by_this_request_record'}
        if body is None or axis is not None and body['axis'] != axis:
            continue
        if not store.scope_contains(plain(scope), body['scope']):
            continue
        rows.append({'source_ref': reference, **deepcopy(body)})
    prepared = {(row['run_id'], row['arguments_sha256']): row['source_ref'] for row in rows
        if row['status'] == 'native_work_requested' and row.get('arguments_sha256') is not None}
    for row in rows:
        if row['status'] == 'input_admission_unavailable':
            row['resolved_by_received_request_ref'] = prepared.get((row.get('run_id'), row.get('arguments_sha256')))
    return rows


def fact_sources():
    ref = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    schema = {'type': 'array', 'items': ref, 'uniqueItems': True}
    return {FACT_SOURCE: {'type': 'array', 'meaning':
        'Actually received, automatically graded A107/A110 native component publications.',
        'report_schema': {**deepcopy(schema), 'x-source': FACT_SOURCE}},
        EXECUTION_SOURCE: {'type': 'array', 'meaning':
            'Actually received native execution/admission failures and missing original operand findings.',
            'report_schema': {**deepcopy(schema), 'x-source': EXECUTION_SOURCE}}}
