"""One authenticated ordinary Mutect2/FilterMutectCalls/SnpEff action.

Every scientific value is supplied by the existing VCF parser/calculator.
Explicit received Files and selected physical software remain the operands;
this owner never guesses sample identity, downloads software or grants auxiliaries.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path, PurePosixPath
import re

from .alignment_site_native import immutable_record
from .communication import plain
from .domain import ContractError, identity
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .flux_balance_tools import _action_lock
from .local_jobs import LocalJobPolicy
from .molecular_measurement_tools import MolecularOperationUnpublished, authenticate_molecular_invocation
from .molecular_sequence_input_contracts import input_record_digest, validate_molecular_sequence_received_file
from .native_atac_differential_driver import _directory, _immutable, _regular, decode_json
from .native_file_capture import NativeFileCaptureError, _identity, _metadata, capture_native_file
from .reference_edit_outcome_tools import _invocation, _context, _admit
from . import native_lifecycle
from . import somatic_variant_contracts as contracts

TOOL = contracts.TOOL
CONFIGURATION_VERSION = 'ordinary_somatic_variant_configuration_v1'
ENVIRONMENT_VERSION = 'somatic_variant_execution_selection_v1'
CAPTURE_VERSION = 'ordinary_somatic_variant_native_capture_v1'
CAPTURE_CONTROL_VERSION = 'ordinary_somatic_variant_native_capture_control_v1'
_WORKERS = {contracts.NATIVE_OPERATION: 'gene_annotation_episode.somatic_variant_driver',
    contracts.RESULT_OPERATION: 'gene_annotation_episode.somatic_variant_result_worker'}



def _require(condition, code):
    if not condition:
        raise ContractError('somatic_variant_' + code)


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()), 'fields_invalid')


def _same(first, second):
    return canonical(first) == canonical(second)


class _KnownFailure(ContractError):
    """An original selected result worker is confirmed terminal and failed."""


def _environment(value):
    _closed(value, 'version environment_realization software parameters')
    _require(value['version'] == ENVIRONMENT_VERSION
        and value['environment_realization'] == 'operation_scoped_tmp_and_cache_v1', 'environment_invalid')
    return dict(version=ENVIRONMENT_VERSION, environment_realization=value['environment_realization'],
        software=contracts.validate_somatic_software(value['software']),
        parameters=contracts.validate_somatic_parameters(value['parameters']))


def normalize_somatic_variant_configuration(resources, environments, *, policy):
    """Validate the caller's one explicit allocation and exact native profile."""
    _require(type(resources) is dict and isinstance(environments, (list, tuple)),
        'configuration_invalid')
    checked = LocalJobPolicy(**policy).to_dict()
    _require(_same(checked, contracts.POLICY), 'policy_invalid')
    _require(canonical(checked) == canonical(policy), 'policy_invalid')
    selected = []
    for entry in environments:
        _closed(entry, 'operation resource_id environment')
        _require(entry['operation'] == TOOL and not selected, 'ambiguous_resource_selection')
        name = entry['resource_id']
        _require(type(name) is str and bool(name), 'resource_selection_invalid')
        resource = resources.get(name)
        _require(type(resource) is dict and resource.get('kind') == 'local'
            and canonical(resource.get('policy')) == canonical(checked),
            'resource_allocation_conflict')
        selected.append(dict(resource_id=name, resource=deepcopy(resource),
            environment=_environment(entry['environment'])))
    return dict(version=CONFIGURATION_VERSION, policy=checked, resources=selected,
        saved_modes=False)


def validate_somatic_variant_configuration(value):
    """Check the same frozen selection on restoration without opening software."""
    _closed(value, 'version policy resources saved_modes')
    _require(value['version'] == CONFIGURATION_VERSION and type(value['saved_modes']) is bool
        and type(value['resources']) is list and len(value['resources']) <= 1,
        'configuration_invalid')
    resources, environments = {}, []
    for row in value['resources']:
        _closed(row, 'resource_id resource environment')
        _require(type(row['resource_id']) is str and bool(row['resource_id']),
            'resource_selection_invalid')
        resources[row['resource_id']] = row['resource']
        environments.append(dict(operation=TOOL, resource_id=row['resource_id'],
            environment=row['environment']))
    checked = normalize_somatic_variant_configuration(resources, environments,
        policy=value['policy'])
    checked['saved_modes'] = value['saved_modes']
    return checked


def somatic_variant_tool_arguments_schema(configuration):
    """Expose only configured modes using the one public argument contract."""
    configuration = validate_somatic_variant_configuration(configuration)
    allowed = set()
    if configuration['resources']:
        allowed.add('run_native')
    if configuration['saved_modes']:
        allowed.update(('calculate_saved', 'read_stored'))
    if not allowed:
        return None
    schema = contracts.somatic_result_schema('Arguments')
    arguments = schema['$defs']['SomaticArguments']
    arguments['oneOf'] = [branch for branch in arguments['oneOf']
        if branch['properties']['mode']['const'] in allowed]
    return schema


def somatic_variant_tool_contract(configuration):
    configuration = validate_somatic_variant_configuration(configuration)
    schema = somatic_variant_tool_arguments_schema(configuration)
    if schema is None:
        return None
    return dict(resources='local', invocation_route=dict(kind='direct'),
        description='Call and annotate somatic variants from explicitly supplied matched tumor/normal BAMs and reference inputs using selected Mutect2, FilterMutectCalls and SnpEff resources.',
        instructions='Supply each required received File, explicit BAM SM identities, reference association and annotation database. Native process status is separate from VCF validity or biological truth. Select a retained native stage and explicit record/sample/field window. Saved calculation reuses that stage Sheet; read_stored returns the original selected values. Preserve unknown/partial inputs, literal FILTER/INFO/ANN and population denominators. No clinical or function-confidence score is inferred.',
        input_schema=schema, configuration=dict(job_limits=configuration['policy'],
            saved_modes=configuration['saved_modes'], execution='isolated_store_free_worker', algorithm_substitution=False))


def _file(registry, value):
    value = _identity(value)
    metadata = _metadata(registry.store, value['artifact_ref'])
    _require(metadata['sha256'] == value['sha256'] and metadata['size'] == value['size_bytes'],
        'file_identity_conflict')
    return value


def _path(registry, value, *, store_root=None):
    root = registry.store.path if store_root is None else store_root
    return str(root / 'artifacts' / value['sha256'][:2] / value['sha256'])


def _source_admission(registry, context, reference, cutoff):
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix='somatic_variant_')
    records.authenticate(context)
    return records.source_admission_before(context, reference, cutoff)


def _input_decision_admission(registry, context, item, cutoff):
    record = registry.store.get(item['reference'])
    _require(record.get('record_type') == item['namespace'], 'input_namespace_conflict')
    if item['namespace'] == 'source':
        from .materials import source_window_selection
        immutable_record(record)
        artifact, representation, _ = source_window_selection(record, 'original')
        _require(representation == 'original', 'input_representation_conflict')
    else:
        artifact = item['reference']
    _metadata(registry.store, artifact)
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix='somatic_variant_')
    return records.file_admission_before(context, item['reference'], item['namespace'], artifact, cutoff)


def _file_admission(registry, context, received, item, cutoff, format):
    received = validate_molecular_sequence_received_file(received)
    _require(received['failure'] is None and received['selection'] == dict(
        reference=item['reference'], namespace=item['namespace']), 'input_not_received')
    value = received['input']
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix='somatic_variant_')
    records.authenticate(context)
    manifest = EpisodeReceipts.read_manifest(registry.store.db, context.run_id, context.episode_id)
    _require(value['receiver'] == dict(run_id=context.run_id, episode_id=context.episode_id,
        request_sha256=input_record_digest(plain(context.request)), assignment_sha256=input_record_digest(plain(context.assignment)))
        and _same(value['scope'], registry.store.validate_scope(plain(context.scope)))
        and _same(value['inheritance_manifest'], manifest)
        and _same(value['witness']['record'], registry.store.get(item['reference'])), 'input_admission_conflict')
    file = _file(registry, value['file'])
    _require(file['format'] == format and file['size_bytes'] <= item['max_bytes'], 'input_file_conflict')
    _require(file['artifact_ref'] == _input_decision_admission(registry, context, item, cutoff)['artifact_ref'], 'input_file_conflict')
    records.file_admission_before(context, item['reference'], item['namespace'], file['artifact_ref'], cutoff)
    return received


def _fresh_inputs(registry, context, reader, arguments, cutoff):
    inputs, admissions, decisions = [], [], []
    for item, (role, _, format) in zip(arguments['inputs'], contracts.INPUTS):
        decision = _input_decision_admission(registry, context, item, cutoff)
        artifact = decision['artifact_ref']
        _require(_metadata(registry.store, artifact)['size'] <= item['max_bytes'], 'input_byte_limit_exceeded')
        received, path = reader(context, item['reference'], item['namespace'], file_format=format)
        received = _file_admission(registry, context, received, item, cutoff, format)
        _require(_same(decision, _input_decision_admission(registry, context, item, cutoff)), 'input_decision_admission_conflict')
        file = received['input']['file']
        _require(received['input']['byte_verification'] == 'verified' and path is not None
            and str(path) == _path(registry, file), 'input_bytes_unavailable')
        inputs.append(dict(role=role, path=str(path), file=file,
            source_ref=item['reference'] if item['namespace'] == 'source' else None))
        admissions.append(received)
        decisions.append(decision)
    return inputs, admissions, decisions


def _check_inputs(registry, context, arguments, inputs, admissions, decisions, cutoff, *, store_root=None):
    _require(type(inputs) is type(admissions) is type(decisions) is list
        and len(inputs) == len(admissions) == len(decisions) == len(arguments['inputs']), 'input_count_conflict')
    for item, input, received, decision, (role, _, format) in zip(
            arguments['inputs'], inputs, admissions, decisions, contracts.INPUTS):
        received = _file_admission(registry, context, received, item, cutoff, format)
        file = received['input']['file']
        expected = dict(role=role, path=_path(registry, file, store_root=store_root), file=file,
            source_ref=item['reference'] if item['namespace'] == 'source' else None)
        _require(_same(input, expected) and _same(decision,
            _input_decision_admission(registry, context, item, cutoff)), 'input_decision_admission_conflict')


def _selected_resource(value, policy):
    _closed(value, 'resource_id resource environment')
    _require(type(value['resource_id']) is str and bool(value['resource_id'])
        and type(value['resource']) is dict and value['resource'].get('kind') == 'local'
        and _same(value['resource'].get('policy'), policy), 'resource_allocation_conflict')
    _environment(value['environment'])
    return value


def _run_selection(registry, owner, selected, policy):
    _selected_resource(selected, policy)
    _require(_same(owner.resources.get(selected['resource_id']), selected['resource'])
        and _same(registry.local_job_policy.to_dict(), policy), 'run_resource_selection_conflict')


def _native_request(inputs, arguments, selected_resource):
    environment = _environment(selected_resource['environment'])
    _require(arguments['annotation_database_id'] == environment['software']['database']['id'], 'selected_database_conflict')
    return contracts.validate_somatic_native_request(dict(version=contracts.NATIVE_REQUEST_VERSION,
        inputs=deepcopy(inputs), sample_ids=arguments['sample_ids'], reference_id=arguments['reference_id'],
        software=environment['software'], parameters=environment['parameters']))


def _worker_dispatch(registry, owner, request, directory, operation, policy, selected_resource):
    _require(_same(LocalJobPolicy(**policy).to_dict(), policy), 'policy_invalid')
    if selected_resource is not None:
        _selected_resource(selected_resource, policy)
    path = directory / 'execution-selection.json'
    if path.exists():
        selected = decode_json(path.read_bytes())
        _closed(selected, 'version command cwd environment policy request python implementation_files')
        _require(selected['version'] == 'ordinary_molecular_execution_v1'
            and _same(selected['request'], dict(operation=operation, arguments=dict(request=request)))
            and selected['cwd'] == str(directory) and _same(selected['policy'], policy)
            and selected['command'] == [selected['python']['path'], '-m', _WORKERS[operation],
                str(directory / 'worker-request.json'), str(directory / 'worker-result.json')],
            'original_worker_selection_conflict')
    else:
        _require(_same(registry.local_job_policy.to_dict(), policy), 'run_resource_selection_conflict')
        if selected_resource is not None:
            _run_selection(registry, owner, selected_resource, policy)


def _historical_store_root(worker, invocation, stage):
    supplied = worker['selection']['cwd']
    _require(type(supplied) is str, 'worker_selection_conflict')
    directory = PurePosixPath(supplied)
    _require(directory.is_absolute() and str(directory) == supplied and '..' not in directory.parts
        and directory.parts[-4:] == ('cache', 'molecular-measurements',
            digest(invocation['operation_key']), stage), 'worker_selection_conflict')
    return directory.parents[3]


def _worker_control(worker, request, operation, invocation, stage):
    """Validate retained worker metadata without reopening its old workspace."""
    _closed(worker, 'request selection handle observation native_request native_request_raw result_sha256')
    selected, original, observed = worker['selection'], worker['handle'], worker['observation']
    _closed(selected, 'version command cwd environment policy request python implementation_files')
    root = _historical_store_root(worker, invocation, stage)
    directory = root / 'cache' / 'molecular-measurements' / digest(invocation['operation_key']) / stage
    _require(selected['version'] == 'ordinary_molecular_execution_v1'
        and _same(worker['request'], request)
        and _same(selected['request'], dict(operation=operation, arguments=dict(request=request)))
        and selected['command'] == [selected['python']['path'], '-m', _WORKERS[operation],
            str(directory / 'worker-request.json'), str(directory / 'worker-result.json')]
        and original['command'] == selected['command']
        and original['cwd'] == selected['cwd'] == str(directory)
        and original['stdout'] == str(directory / 'stdout') and original['stderr'] == str(directory / 'stderr')
        and observed['terminal'] is True and observed['quiescent'] is True
        and _same(original['metadata']['policy'], selected['policy'])
        and _same(observed['metadata']['policy'], selected['policy'])
        and _same(LocalJobPolicy(**selected['policy']).to_dict(), selected['policy']), 'worker_control_conflict')
    paths = original['paths']
    _require(all(type(path) is str and PurePosixPath(path).parent == directory for path in paths.values()),
        'worker_handle_conflict')
    raw = worker['native_request_raw']
    _require(type(raw) is str and hashlib.sha256(raw.encode()).hexdigest() == original['request_sha256']
        and _same(decode_json(raw.encode()), worker['native_request'])
        and _same(worker['native_request'], dict(command=selected['command'], cwd=str(directory),
            file_bytes=selected['policy']['scratch_bytes'], ready_path=paths['ready'],
            release_path=paths['release'], result_path=paths['result'], stdin_path=None,
            env=selected['environment'])), 'worker_handle_conflict')
    return root


def _worker_record(registry, work, request, directory, operation, invocation, *, allow_failure=False):
    output = directory / 'worker-result.json'
    _require(Path(work.output_path) == output, 'worker_output_conflict')
    handle = native_lifecycle.NativeJobHandle(directory / 'native-handle.json')
    observed = native_lifecycle.status(handle)
    if not (observed['terminal'] and observed['quiescent']):
        raise MolecularOperationUnpublished('somatic_variant_worker_attempt_unconfirmed')
    _require(_same({key: value for key, value in work.metadata.items() if key != 'molecular_failure'},
        observed['metadata']), 'worker_metadata_conflict')
    selected = decode_json((directory / 'execution-selection.json').read_bytes())
    original = handle.read()
    with _regular(original['paths']['request']) as stream:
        raw = stream.read()
    with _regular(directory / 'worker-request.json') as stream:
        _require(_same(decode_json(stream.read()), selected['request']), 'worker_request_conflict')
    result = None
    if output.is_file():
        with _regular(output) as stream:
            try:
                result = decode_json(stream.read())
            except (ValueError, TypeError):
                if not allow_failure:
                    raise
    record = dict(request=request, selection=selected, handle=original, observation=observed,
        native_request=decode_json(raw), native_request_raw=raw.decode(),
        result_sha256=None if result is None else digest(result))
    stage = 'native' if operation == 'somatic_variant_native' else 'calculation'
    _require(str(_worker_control(record, request, operation, invocation, stage)) == str(registry.store.path),
        'worker_store_conflict')
    failed = bool(work.metadata.get('molecular_failure')) or observed['metadata'].get('native_returncode') != 0
    if not allow_failure and (failed or result is None):
        raise _KnownFailure('somatic_variant_result_calculation_failed')
    return result, record


def _capture_control(registry, capture, *, invocation, arguments, input_artifact_refs):
    from .molecular_measurement_tools import _publication_bytes
    immutable_record(capture)
    _require(capture.get('record_type') == 'source' and capture.get('origin') == 'tool'
        and capture.get('provider') == TOOL and capture.get('version') == CAPTURE_VERSION
        and capture.get('accession') == identity('operation', dict(key=invocation['operation_key'],
            name=TOOL, arguments=arguments)) and 'operand_refs' not in capture, 'capture_source_conflict')
    control = decode_json(_publication_bytes(registry.store, capture['request_ref']))
    _closed(control, 'version invocation arguments input_artifact_refs input_admissions input_decisions inputs selected_resource policy native_request native_worker manifest_ref')
    _require(control['version'] == CAPTURE_CONTROL_VERSION and _same(control['invocation'], invocation)
        and _same(control['arguments'], arguments) and arguments['mode'] == 'run_native'
        and control['input_artifact_refs'] == input_artifact_refs
        and input_artifact_refs == list(dict.fromkeys(row['file']['artifact_ref'] for row in control['inputs'])), 'capture_control_conflict')
    _selected_resource(control['selected_resource'], control['policy'])
    request = _native_request(control['inputs'], arguments, control['selected_resource'])
    _require(_same(request, control['native_request']), 'native_request_conflict')
    root = _worker_control(control['native_worker'], request, contracts.NATIVE_OPERATION, invocation, 'native')
    _require(_same(control['native_worker']['selection']['policy'], control['policy']), 'action_policy_conflict')
    _check_inputs(registry, _context(registry.store, invocation), arguments, control['inputs'],
        control['input_admissions'], control['input_decisions'], invocation['decision_index'], store_root=root)
    body = decode_json(_publication_bytes(registry.store, control['manifest_ref']))
    _closed(body, 'version invocation manifest outputs logs input_artifact_refs')
    manifest = contracts.validate_somatic_native_manifest(body['manifest'])
    _require(body['version'] == CAPTURE_VERSION and _same(body['invocation'], invocation)
        and body['input_artifact_refs'] == input_artifact_refs and _same(manifest['request'], request)
        and control['native_worker']['result_sha256'] == digest(manifest)
        and manifest['directory'] == str(PurePosixPath(control['native_worker']['selection']['cwd']) / contracts.NATIVE_DIRECTORY)
        and capture['artifact_ref'] == control['manifest_ref'], 'capture_body_conflict')
    _require(type(body['outputs']) is list and len(body['outputs']) == len(manifest['files']), 'capture_files_conflict')
    references, stage_inputs = [], []
    for row, declaration in zip(body['outputs'], manifest['files']):
        _closed(row, 'declaration file')
        file = _file(registry, row['file'])
        _require(_same(row['declaration'], declaration) and file['format'] == declaration['format']
            and all(file[key] == declaration[key] for key in ('sha256', 'size_bytes')), 'capture_declaration_conflict')
        references.append(file['artifact_ref'])
    _require(type(body['logs']) is list and [row.get('name') for row in body['logs']] == ['stdout', 'stderr'], 'capture_logs_conflict')
    for row in body['logs']:
        _closed(row, 'name file')
        if row['file'] is not None:
            file = _file(registry, row['file'])
            _require(file['format'] == 'somatic_variant_worker_log', 'capture_format_conflict')
            references.append(file['artifact_ref'])
    parents = list(dict.fromkeys(item['reference'] for item in arguments['inputs'] if item['namespace'] == 'source'))
    _require(capture.get('parent_source_refs') == parents and capture.get('auxiliary_artifact_refs') ==
        [ref for ref in dict.fromkeys(references) if ref not in input_artifact_refs and ref != capture['artifact_ref']], 'capture_source_conflict')
    for stage in contracts.STAGES:
        found = next((row for row in body['outputs'] if row['declaration']['role'] == stage), None)
        item = None if found is None else dict(path=_path(registry, found['file'], store_root=root),
            file=found['file'], source_ref=capture['id'], capture=dict(state='complete', byte_start_0based=0,
                byte_end_0based_exclusive=found['file']['size_bytes'], original_size_bytes=found['file']['size_bytes']))
        stage_inputs.append(dict(stage=stage, input=item))
    result_request = dict(version='somatic_variant_result_request_v1', mode='parse', stage_inputs=stage_inputs,
        saved=None, context=contracts.somatic_context_from_manifest(manifest), selection=arguments['selection'])
    return dict(control=control, body=body, store_root=root, request=result_request)


def _capture_native(registry, invocation, arguments, intent, manifest, worker, directory):
    manifest = contracts.validate_somatic_native_manifest(manifest)
    _require(_same(manifest['request'], intent['native_request']), 'native_request_conflict')
    rows, references = [], []
    for declaration in manifest['files']:
        file = capture_native_file(registry.store, directory=str(directory), relative_path=declaration['relative_path'],
            format=declaration['format'], media_type='application/octet-stream')
        _require(all(file[key] == declaration[key] for key in ('sha256', 'size_bytes')), 'native_output_identity_conflict')
        rows.append(dict(declaration=declaration, file=file))
        references.append(file['artifact_ref'])
    logs = []
    for name in ('stdout', 'stderr'):
        file = None
        try:
            file = capture_native_file(registry.store, directory=str(directory), relative_path=name,
                format='somatic_variant_worker_log', media_type='application/octet-stream')
        except NativeFileCaptureError as error:
            if error.code != 'capture_file_unavailable':
                raise
        logs.append(dict(name=name, file=file))
        if file is not None:
            references.append(file['artifact_ref'])
    excluded = list(dict.fromkeys(row['file']['artifact_ref'] for row in intent['inputs']))
    body = dict(version=CAPTURE_VERSION, invocation=invocation, manifest=manifest,
        outputs=rows, logs=logs, input_artifact_refs=excluded)
    manifest_ref = registry.store.artifact(canonical(body), 'application/json')
    control = dict(version=CAPTURE_CONTROL_VERSION, invocation=invocation, arguments=arguments,
        input_artifact_refs=excluded, inputs=intent['inputs'], input_admissions=intent['input_admissions'],
        input_decisions=intent['input_decisions'], selected_resource=intent['selected_resource'], policy=intent['policy'],
        native_request=intent['native_request'], native_worker=worker, manifest_ref=manifest_ref)
    control_ref = registry.store.artifact(canonical(control), 'application/json')
    stamp = directory.parent / 'publication-time.json'
    if not stamp.exists():
        _immutable(stamp, dict(retrieved_at=datetime.now(timezone.utc).isoformat()))
    source = registry._put('source', dict(provider=TOOL,
        accession=identity('operation', dict(key=invocation['operation_key'], name=TOOL, arguments=arguments)),
        uri=None, artifact_ref=manifest_ref, request_ref=control_ref, text_ref=None, version=CAPTURE_VERSION,
        retrieved_at=decode_json(stamp.read_bytes())['retrieved_at'],
        parent_source_refs=list(dict.fromkeys(item['reference'] for item in arguments['inputs'] if item['namespace'] == 'source')),
        auxiliary_artifact_refs=[ref for ref in dict.fromkeys(references) if ref not in excluded and ref != manifest_ref]), origin='tool')
    checked = _capture_control(registry, source, invocation=invocation, arguments=arguments, input_artifact_refs=excluded)
    return source, checked['request'], excluded


def _outcome(arguments, operation_key, public, *, redisplay=False):
    context = public['context']
    partial = bool(context['issues']) or any(row['state'] != 'exited' or row['returncode'] != 0 for row in context['stages'])
    partial = partial or not public['value']['population']['record_population_complete']
    return dict(status='partial' if partial else 'completed', operation_ref=identity('operation',
        dict(key=operation_key, name=TOOL, arguments=arguments)), record_refs=[public['source_ref']],
        changed_record_refs=[] if redisplay else [public['source_ref']], result=public,
        feedback=dict(category='representation', code='somatic_variant_selected_result_partial',
            source_ref=public['source_ref']) if partial else None)


def _failure(registry, arguments, operation_key, error):
    message = str(error)
    code = message if re.fullmatch(r'[a-z][a-z0-9_]*', message) else 'somatic_variant_execution_failed'
    diagnostic = registry.store.artifact(canonical(dict(version='somatic_variant_diagnostic_v1',
        exception_type=type(error).__module__ + '.' + type(error).__name__, exception_message=message)), 'application/json')
    return dict(status='failed' if isinstance(error, _KnownFailure) else
        'unavailable' if isinstance(error, OSError) or code.endswith('_unavailable') else
        'invalid' if isinstance(error, (ValueError, TypeError, KeyError)) else 'failed',
        operation_ref=identity('operation', dict(key=operation_key, name=TOOL, arguments=arguments)),
        record_refs=[], changed_record_refs=[], result=None,
        feedback=dict(category='execution', code=code, diagnostic_ref=diagnostic))


async def execute_somatic_variant_tool(registry, arguments, *, scope, operation_key, authority):
    """Run one selected action; recovery keeps both original owned handles."""
    from .molecular_measurement_tools import _recorded_molecular_action_details
    from .somatic_variant_publication import (
        _read_somatic_variant_publication, _publish, _saved_request,
        read_somatic_variant_action_result,
    )
    context, reader = authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
    _require(type(authority) is tuple and len(authority) == 2
        and authority[0] is context and authority[1] is reader, 'invocation_authority_conflict')
    owner = registry.execution_owner_for(context.run_id)
    _require(owner.store is registry.store and owner.tool_registry is registry
        and owner.run_id == context.run_id, 'execution_owner_conflict')
    invocation = _invocation(context, operation_key)
    directory = _directory(registry.store.path / 'cache' / 'molecular-measurements' / digest(operation_key))
    async with _action_lock(directory):
        authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
        if registry.store.db.execute('SELECT 1 FROM tool_operations WHERE operation_key=?', (operation_key,)).fetchone():
            details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
                recovery_context=context, recovery_operation_key=operation_key)
            outcome = details['outcome']
            if outcome.get('status') in ('completed', 'partial'):
                _require(_same(read_somatic_variant_action_result(registry, context, arguments,
                    operation_key, reader=reader), outcome['result']), 'cached_result_conflict')
            else:
                _require(outcome.get('status') in ('failed', 'invalid', 'unavailable')
                    and outcome.get('result') is None and outcome.get('record_refs') == [], 'cached_failure_conflict')
            return outcome
        intent_path = directory / 'somatic-variant-intent.json'
        result_intent_path = directory / 'calculation/somatic-variant-result-intent.json'
        attempt_possible = intent_path.exists() or result_intent_path.exists()
        try:
            arguments = contracts.validate_somatic_arguments(arguments)
            configured = registry._somatic_variant_configuration
            configuration = None if configured is None else validate_somatic_variant_configuration(configured)
            if arguments['mode'] == 'run_native':
                if intent_path.exists():
                    intent = decode_json(intent_path.read_bytes())
                    _closed(intent, 'version arguments invocation selected_resource policy inputs input_admissions input_decisions native_request')
                    _require(intent['version'] == 'ordinary_somatic_variant_intent_v1'
                        and _same(intent['arguments'], arguments) and _same(intent['invocation'], invocation), 'original_intent_conflict')
                    _check_inputs(registry, context, arguments, intent['inputs'], intent['input_admissions'],
                        intent['input_decisions'], invocation['decision_index'])
                else:
                    _require(configuration is not None and len(configuration['resources']) == 1, 'native_resource_required')
                    selected = configuration['resources'][0]
                    _run_selection(registry, owner, selected, configuration['policy'])
                    inputs, admissions, decisions = _fresh_inputs(registry, context, reader, arguments, invocation['decision_index'])
                    intent = dict(version='ordinary_somatic_variant_intent_v1', arguments=arguments,
                        invocation=invocation, selected_resource=selected, policy=configuration['policy'],
                        inputs=inputs, input_admissions=admissions, input_decisions=decisions,
                        native_request=_native_request(inputs, arguments, selected))
                    _immutable(intent_path, intent)
                _require(_same(intent['native_request'], _native_request(intent['inputs'], arguments,
                    intent['selected_resource'])), 'native_request_conflict')
                native_directory = _directory(directory / 'native')
                native_directory.mkdir(exist_ok=True)
                _worker_dispatch(registry, owner, intent['native_request'], native_directory,
                    contracts.NATIVE_OPERATION, intent['policy'], intent['selected_resource'])
                attempt_possible = True
                work = await registry._sequence_worker_async(contracts.NATIVE_OPERATION,
                    dict(request=intent['native_request']), directory=native_directory, owned_directory=native_directory)
                authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
                _check_inputs(registry, context, arguments, intent['inputs'], intent['input_admissions'],
                    intent['input_decisions'], invocation['decision_index'])
                manifest, native_worker = _worker_record(registry, work, intent['native_request'],
                    native_directory, contracts.NATIVE_OPERATION, invocation, allow_failure=True)
                _require(_same(native_worker['selection']['policy'], intent['policy']), 'action_policy_conflict')
                if manifest is None:
                    raise _KnownFailure('somatic_variant_native_manifest_unavailable')
                with registry.store.transaction():
                    capture, request, excluded = _capture_native(registry, invocation, arguments,
                        intent, manifest, native_worker, native_directory)
                prepared = dict(capture_source=capture, stage_sheets=None, context_file=None,
                    input_artifact_refs=excluded, source_admission=None, source_decision_admission=None,
                    original_source=None, policy=intent['policy'], selected_resource=intent['selected_resource'])
            else:
                _require(configuration is not None and configuration['saved_modes'], 'saved_modes_not_configured')
                with registry.store.read_snapshot():
                    publication = _read_somatic_variant_publication(registry, context, reader,
                        arguments['result_ref'], require_documents=arguments['mode'] == 'calculate_saved',
                        before_decision_index=invocation['decision_index'])
                if arguments['mode'] == 'read_stored':
                    with registry.store.transaction():
                        public = publication['public']
                        outcome = _outcome(arguments, operation_key, public, redisplay=True)
                        registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
                    return outcome
                previous = publication['control']
                prepared = dict(capture_source=registry.store.get(previous['capture_source']['source_ref']),
                    stage_sheets=previous['stage_sheets'], context_file=previous['context_file'],
                    input_artifact_refs=previous['input_artifact_refs'], source_admission=publication['received_input'],
                    source_decision_admission=publication['source_decision_admission'],
                    original_source=dict(source_ref=publication['source']['id'], record_sha256=digest(publication['source'])),
                    policy=configuration['policy'], selected_resource=None)
                request = _saved_request(registry, arguments, previous, store_root=registry.store.path)
            calculation = _directory(directory / 'calculation')
            calculation.mkdir(exist_ok=True)
            if result_intent_path.exists():
                saved_intent = decode_json(result_intent_path.read_bytes())
                _closed(saved_intent, 'invocation arguments request source_admission source_decision_admission policy selected_resource')
                _require(_same(saved_intent['invocation'], invocation) and _same(saved_intent['arguments'], arguments)
                    and _same(saved_intent['request'], request)
                    and _same(saved_intent['source_admission'], prepared['source_admission'])
                    and _same(saved_intent['source_decision_admission'], prepared['source_decision_admission'])
                    and _same(saved_intent['selected_resource'], prepared['selected_resource']), 'original_result_intent_conflict')
                _require(_same(LocalJobPolicy(**saved_intent['policy']).to_dict(), contracts.POLICY), 'action_policy_conflict')
                prepared['policy'] = saved_intent['policy']
            else:
                _immutable(result_intent_path, dict(invocation=invocation, arguments=arguments, request=request,
                    source_admission=prepared['source_admission'], source_decision_admission=prepared['source_decision_admission'],
                    policy=prepared['policy'], selected_resource=prepared['selected_resource']))
            _worker_dispatch(registry, owner, request, calculation, contracts.RESULT_OPERATION,
                prepared['policy'], prepared['selected_resource'])
            attempt_possible = True
            work = await registry._sequence_worker_async(contracts.RESULT_OPERATION, dict(request=request),
                directory=calculation, owned_directory=calculation)
            authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
            if arguments['mode'] == 'run_native':
                _check_inputs(registry, context, arguments, intent['inputs'], intent['input_admissions'],
                    intent['input_decisions'], invocation['decision_index'])
            else:
                _require(_same(_admit(registry.store, reader, context, arguments['result_ref'], 'source',
                    invocation['decision_index']), prepared['source_admission']) and _same(_source_admission(
                        registry, context, arguments['result_ref'], invocation['decision_index']),
                        prepared['source_decision_admission']), 'source_admission_conflict')
            result, worker = _worker_record(registry, work, request, calculation, contracts.RESULT_OPERATION, invocation)
            _require(_same(worker['selection']['policy'], prepared['policy']), 'action_policy_conflict')
            with registry.store.transaction():
                public = _publish(registry, arguments, invocation, prepared, result, worker, calculation)
                outcome = _outcome(arguments, operation_key, public)
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome
        except MolecularOperationUnpublished:
            raise
        except Exception as error:
            if attempt_possible and not isinstance(error, _KnownFailure):
                raise MolecularOperationUnpublished('somatic_variant_original_action_unpublished') from error
            with registry.store.transaction():
                outcome = _failure(registry, arguments, operation_key, error)
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome


def read_retained_somatic_variant_publication(registry, context, reader, source_ref, *, recovery_operation_key=None):
    from .somatic_variant_publication import read_retained_somatic_variant_publication as read
    return read(registry, context, reader, source_ref, recovery_operation_key=recovery_operation_key)


def read_somatic_variant_action_result(registry, context, arguments, operation_key, *, reader):
    from .somatic_variant_publication import read_somatic_variant_action_result as read
    return read(registry, context, arguments, operation_key, reader=reader)
