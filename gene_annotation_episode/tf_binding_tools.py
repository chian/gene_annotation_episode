"""Ordinary supplied-input TF actions and immutable retained publications.

The existing molecular worker owns execution. This adapter owns the selected
action's admissions, private native capture and Source-only publication. Native
scoring and retained numerical calculation remain in their existing workers.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import stat

from .communication import plain
from .domain import ContractError, identity, obj
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .flux_balance_tools import _action_lock
from .local_jobs import LocalJobPolicy
from .molecular_measurement_tools import (
    MolecularOperationUnpublished, authenticate_molecular_invocation,
    _publication_bytes, _recorded_molecular_action_details,
    _recorded_molecular_producer_details,
)
from .molecular_sequence_input_contracts import (
    input_record_digest, validate_molecular_sequence_received_file,
)
from .native_atac_differential_driver import _directory, _immutable, _regular, decode_json
from .native_file_capture import NativeFileCaptureError, _identity, _metadata, capture_native_file
from .reference_edit_outcome_tools import (
    _admit, _context, _current_cutoff, _frozen_admission, _invocation,
)
from .alignment_site_native import immutable_record
from .tf_binding_result_contracts import (
    TOOL, SOURCE_VERSION, CAPTURE_VERSION, PACKET_VERSION,
    tf_binding_return, validate_tf_binding_return, validate_tf_binding_value,
)
from . import native_lifecycle
from . import tf_binding_measurements as core


CONFIGURATION_VERSION = 'ordinary_tf_binding_configuration_v1'
CONTROL_VERSION = 'ordinary_tf_binding_publication_v1'
CAPTURE_CONTROL_VERSION = 'ordinary_tf_binding_native_capture_control_v1'
_SOURCE = re.compile(r'^source_[0-9a-f]{24,64}$')
_ARTIFACT = re.compile(r'^artifact_[0-9a-f]{64}$')
_SCORE_NAME = re.compile(r'^scores-[0-9]{6,}\.f32$')
_FORMATS = {'dna': ('fasta', 'raw_dna'),
    'matrix': ('jaspar_json', 'jaspar_pfm', 'acgt_count_json')}
_WORKERS = {'tf_binding_native': 'gene_annotation_episode.tf_binding_driver',
    'tf_binding_result': 'gene_annotation_episode.tf_binding_result_worker'}


def _require(condition, code):
    if not condition:
        raise ContractError('tf_binding_' + code)


class _KnownUnavailable(ContractError):
    """A confirmed attempt has no authentic selected result to deliver."""


class _KnownFailure(ContractError):
    """An original worker is confirmed terminal and failed."""


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()), 'fields_invalid')


def _same(first, second):
    return canonical(first) == canonical(second)


def _copy(value):
    return json.loads(canonical(value))


def normalize_tf_binding_configuration(resources, environments, *, policy):
    """Select an explicitly named existing local allocation, without I/O."""
    _require(type(resources) is dict and isinstance(environments, (list, tuple)),
        'configuration_invalid')
    checked = LocalJobPolicy(**policy).to_dict()
    _require(_same(checked, policy), 'policy_invalid')
    selected = []
    for entry in environments:
        _closed(entry, 'operation resource_id environment')
        _require(entry['operation'] == TOOL and not selected, 'ambiguous_resource_selection')
        name = entry['resource_id']
        _require(type(name) is str and bool(name), 'resource_selection_invalid')
        resource = resources.get(name)
        _require(type(resource) is dict and resource.get('kind') == 'local'
            and _same(resource.get('policy'), policy), 'resource_allocation_conflict')
        environment = dict(version='tf_binding_execution_selection_v1',
            environment_realization='operation_scoped_tmp_and_cache_v1')
        _require(_same(entry['environment'], environment), 'environment_invalid')
        selected.append(dict(resource_id=name, resource=_copy(resource), environment=environment))
    return dict(version=CONFIGURATION_VERSION, policy=checked, resources=selected, saved_modes=False)


def _configuration(value):
    _closed(value, 'version policy resources saved_modes')
    _require(value['version'] == CONFIGURATION_VERSION and type(value['saved_modes']) is bool
        and type(value['resources']) is list and len(value['resources']) <= 1,
        'configuration_invalid')
    _require(_same(LocalJobPolicy(**value['policy']).to_dict(), value['policy']), 'policy_invalid')
    for row in value['resources']:
        _closed(row, 'resource_id resource environment')
        _require(type(row['resource_id']) is str and bool(row['resource_id'])
            and type(row['resource']) is dict and row['resource'].get('kind') == 'local'
            and _same(row['resource'].get('policy'), value['policy'])
            and _same(row['environment'], dict(version='tf_binding_execution_selection_v1',
                environment_realization='operation_scoped_tmp_and_cache_v1')),
            'configuration_invalid')
    return _copy(value)


def _result_selection(value):
    _closed(value, 'scope scan_ids raw_threshold offset limit')
    _require(value['scope'] in ('all_retained_scans', 'selected_scan_ids'), 'selection_scope_invalid')
    _require(value['scan_ids'] is None if value['scope'] == 'all_retained_scans'
        else type(value['scan_ids']) is list, 'selection_scope_invalid')
    core.validate_tf_binding_selection(dict(version='tf_binding_selection_v1',
        scan_ids=[] if value['scan_ids'] is None else value['scan_ids'],
        **{key: deepcopy(value[key]) for key in ('raw_threshold', 'offset', 'limit')}))
    return _copy(value)


def _arguments(value):
    value = _copy(value)
    _require(type(value) is dict, 'arguments_invalid')
    if value.get('mode') == 'run_native':
        _closed(value, 'mode inputs scan_selection parameters selection')
        _require(type(value['inputs']) is list and bool(value['inputs']), 'inputs_invalid')
        seen, roles = set(), set()
        for item in value['inputs']:
            _closed(item, 'input_id role format namespace reference')
            _require(type(item['input_id']) is str and bool(item['input_id'])
                and item['input_id'] not in seen and item['role'] in _FORMATS
                and item['format'] in _FORMATS[item['role']], 'inputs_invalid')
            pattern = _ARTIFACT if item['namespace'] == 'artifact' else _SOURCE if item['namespace'] == 'source' else None
            _require(pattern is not None and type(item['reference']) is str
                and pattern.fullmatch(item['reference']) is not None, 'inputs_invalid')
            seen.add(item['input_id']); roles.add(item['role'])
        _require(roles == set(_FORMATS), 'dna_and_matrix_inputs_required')
        core._selection(deepcopy(value['scan_selection']))
        core._parameters(deepcopy(value['parameters']))
        _result_selection(value['selection'])
    else:
        _require(value.get('mode') in ('read_stored', 'calculate_saved'), 'mode_invalid')
        _closed(value, 'mode result_ref' if value['mode'] == 'read_stored'
            else 'mode result_ref selection')
        _require(type(value['result_ref']) is str and _SOURCE.fullmatch(value['result_ref']),
            'source_required')
        if value['mode'] == 'calculate_saved':
            _result_selection(value['selection'])
    return value


def tf_binding_tool_arguments_schema(configuration):
    """Return argument structure only; no model-facing scientific wording."""
    configuration = _configuration(configuration)
    text = dict(type='string', minLength=1)
    integer = dict(type='integer', minimum=0)
    source = dict(type='string', pattern=_SOURCE.pattern)
    inputs = [obj(dict(input_id=text, role=dict(const=role), format=dict(enum=list(formats)),
        namespace=dict(enum=['artifact', 'source']), reference=dict(type='string',
            pattern=r'^(artifact_[0-9a-f]{64}|source_[0-9a-f]{24,64})$')))
        for role, formats in _FORMATS.items()]
    selection = obj(dict(scope=dict(enum=['all_retained_scans', 'selected_scan_ids']),
        scan_ids=dict(anyOf=[dict(type='null'), dict(type='array', items=text, uniqueItems=True)]),
        raw_threshold=dict(type='number'), offset=integer, limit=integer))
    request = obj(dict(sequence_input_id=text, sequence_record_ordinal_0based=integer,
        matrix_input_id=text, matrix_record_ordinal_0based=integer,
        strands=dict(type='array', items=dict(enum=['+', '-']), minItems=1, uniqueItems=True)))
    scan = dict(anyOf=[obj(dict(mode=dict(const='all_supplied_occurrences_both_strands'))),
        obj(dict(mode=dict(const='explicit'), requests=dict(type='array', items=request)))])
    quantities = obj({base: dict(type='number', minimum=0) for base in 'ACGT'})
    variants = []
    if configuration['resources']:
        variants.append(obj(dict(mode=dict(const='run_native'), inputs=dict(type='array',
            items=dict(anyOf=inputs), minItems=2), scan_selection=scan,
            parameters=obj(dict(background=quantities, pseudocounts=quantities)), selection=selection)))
    if configuration['saved_modes']:
        variants += [obj(dict(mode=dict(const='read_stored'), result_ref=source)),
            obj(dict(mode=dict(const='calculate_saved'), result_ref=source, selection=selection))]
    return dict(anyOf=variants) if variants else None


def _file(registry, value):
    value = _identity(value)
    metadata = _metadata(registry.store, value['artifact_ref'])
    _require(metadata['sha256'] == value['sha256'] and metadata['size'] == value['size_bytes'],
        'file_identity_conflict')
    return value


def _path(registry, file, *, store_root=None):
    root = registry.store.path if store_root is None else store_root
    return str(root / 'artifacts' / file['sha256'][:2] / file['sha256'])


def _source_admission(registry, context, source_ref, cutoff):
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix='tf_binding_')
    records.authenticate(context)
    return records.source_admission_before(context, source_ref, cutoff)


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
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix='tf_binding_')
    return records.file_admission_before(context, item['reference'], item['namespace'], artifact, cutoff)


def _file_admission(registry, context, received, item, cutoff):
    received = validate_molecular_sequence_received_file(received)
    _require(received['failure'] is None and received['selection'] == dict(
        reference=item['reference'], namespace=item['namespace']), 'input_not_received')
    value = received['input']
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix='tf_binding_')
    records.authenticate(context)
    manifest = EpisodeReceipts.read_manifest(registry.store.db, context.run_id, context.episode_id)
    _require(value['receiver'] == dict(run_id=context.run_id, episode_id=context.episode_id,
        request_sha256=input_record_digest(plain(context.request)),
        assignment_sha256=input_record_digest(plain(context.assignment)))
        and _same(value['scope'], registry.store.validate_scope(plain(context.scope)))
        and _same(value['inheritance_manifest'], manifest)
        and _same(value['witness']['record'], registry.store.get(item['reference']))
        and records._received_before(context.episode_id, item['reference'], cutoff)
        and records._received_before(context.episode_id, value['file']['artifact_ref'], cutoff),
        'input_admission_conflict')
    _file(registry, value['file'])
    _require(value['file']['format'] == item['format'], 'input_format_conflict')
    return received


def _fresh_inputs(registry, context, reader, arguments, cutoff):
    inputs, admissions, decisions = [], [], []
    for item in arguments['inputs']:
        decision = _input_decision_admission(registry, context, item, cutoff)
        received, path = reader(context, item['reference'], item['namespace'], file_format=item['format'])
        received = _file_admission(registry, context, received, item, cutoff)
        _require(_same(decision, _input_decision_admission(registry, context, item, cutoff)),
            'input_decision_admission_conflict')
        file = received['input']['file']
        _require(received['input']['byte_verification'] == 'verified' and path is not None
            and str(path) == _path(registry, file), 'input_bytes_unavailable')
        inputs.append(dict(input_id=item['input_id'], role=item['role'], format=item['format'],
            path=str(path), artifact=dict(artifact_ref=file['artifact_ref'], sha256=file['sha256'],
                size_bytes=file['size_bytes'], source_ref=item['reference'] if item['namespace'] == 'source' else None),
            capture=dict(state='complete', byte_start_0based=0,
                byte_end_0based_exclusive=file['size_bytes'], original_size_bytes=file['size_bytes'])))
        admissions.append(received); decisions.append(decision)
    return inputs, admissions, decisions


def _check_inputs(registry, context, arguments, inputs, admissions, decisions, cutoff, *, store_root=None):
    _require(type(inputs) is list and type(admissions) is list and type(decisions) is list
        and len(inputs) == len(admissions) == len(decisions) == len(arguments['inputs']),
        'input_admission_conflict')
    for item, frozen, admission, decision in zip(arguments['inputs'], inputs, admissions, decisions):
        received = _file_admission(registry, context, admission, item, cutoff)
        file = received['input']['file']
        expected = dict(input_id=item['input_id'], role=item['role'], format=item['format'],
            path=_path(registry, file, store_root=store_root), artifact=dict(
                artifact_ref=file['artifact_ref'], sha256=file['sha256'], size_bytes=file['size_bytes'],
                source_ref=item['reference'] if item['namespace'] == 'source' else None),
            capture=dict(state='complete', byte_start_0based=0,
                byte_end_0based_exclusive=file['size_bytes'], original_size_bytes=file['size_bytes']))
        _require(_same(frozen, expected) and _same(decision,
            _input_decision_admission(registry, context, item, cutoff)), 'input_decision_admission_conflict')


def _run_selection(registry, owner, selected, policy):
    _require(_same(owner.resources.get(selected['resource_id']), selected['resource'])
        and selected['resource'].get('kind') == 'local'
        and _same(selected['resource'].get('policy'), policy)
        and _same(registry.local_job_policy.to_dict(), policy), 'run_resource_selection_conflict')


def _native_request(invocation, arguments, inputs):
    """Build the one selected native payload for fresh, restored and closed work."""
    return dict(version='tf_binding_native_request_v1', inputs=deepcopy(inputs), invocation=dict(
        version='tf_binding_invocation_v1', invocation_id=identity('tf_binding_native_invocation', invocation),
        operation=TOOL, scan_selection=deepcopy(arguments['scan_selection']),
        parameters=deepcopy(arguments['parameters']), software=[]))


def _worker_dispatch(registry, owner, request, directory, operation, policy, selected_resource):
    """Join allocation before first selection, or keep the original selection."""
    _require(_same(LocalJobPolicy(**policy).to_dict(), policy), 'policy_invalid')
    if selected_resource is not None:
        _closed(selected_resource, 'resource_id resource environment')
        _require(type(selected_resource['resource_id']) is str and bool(selected_resource['resource_id'])
            and type(selected_resource['resource']) is dict
            and selected_resource['resource'].get('kind') == 'local'
            and _same(selected_resource['resource'].get('policy'), policy)
            and _same(selected_resource['environment'], dict(version='tf_binding_execution_selection_v1',
                environment_realization='operation_scoped_tmp_and_cache_v1')), 'resource_allocation_conflict')
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


def _worker_record(registry, work, payload, directory, operation, *, allow_failure=False):
    """Authenticate the existing worker's original selection and closed handle."""
    output = directory / 'worker-result.json'
    _require(Path(work.output_path) == output and operation in _WORKERS, 'worker_output_conflict')
    handle = native_lifecycle.NativeJobHandle(directory / 'native-handle.json')
    observed = native_lifecycle.status(handle)
    if not (observed['terminal'] and observed['quiescent']):
        raise MolecularOperationUnpublished('tf_binding_worker_attempt_unconfirmed')
    _require(_same({k: v for k, v in work.metadata.items() if k != 'molecular_failure'},
        observed['metadata']), 'worker_metadata_conflict')
    selected = decode_json((directory / 'execution-selection.json').read_bytes())
    _closed(selected, 'version command cwd environment policy request python implementation_files')
    original = handle.read()
    _require(selected['version'] == 'ordinary_molecular_execution_v1'
        and _same(selected['request'], dict(operation=operation, arguments=dict(request=payload)))
        and selected['cwd'] == str(directory)
        and selected['command'] == [selected['python']['path'], '-m', _WORKERS[operation],
            str(directory / 'worker-request.json'), str(output)]
        and original['command'] == selected['command'] and original['cwd'] == str(directory)
        and original['stdout'] == str(directory / 'stdout') and original['stderr'] == str(directory / 'stderr')
        and _same(original['metadata']['policy'], selected['policy'])
        and _same(observed['metadata']['policy'], selected['policy']), 'worker_selection_conflict')
    paths = original['paths']
    _require(all(type(p) is str and Path(p).parent == directory for p in paths.values()),
        'worker_handle_conflict')
    with _regular(paths['request']) as stream:
        raw_request = stream.read()
    native_request = decode_json(raw_request)
    _require(hashlib.sha256(raw_request).hexdigest() == original['request_sha256']
        and _same(native_request, dict(command=selected['command'], cwd=str(directory),
            file_bytes=selected['policy']['scratch_bytes'], ready_path=paths['ready'],
            release_path=paths['release'], result_path=paths['result'], stdin_path=None,
            env=selected['environment'])), 'worker_handle_conflict')
    with _regular(directory / 'worker-request.json') as stream:
        _require(_same(decode_json(stream.read()), selected['request']), 'worker_request_conflict')
    failure = bool(work.metadata.get('molecular_failure')) or observed['metadata'].get('native_returncode') != 0
    result = None
    if output.is_file():
        with _regular(output) as stream:
            raw = stream.read()
        try:
            result = decode_json(raw)
        except (ValueError, TypeError):
            if not allow_failure:
                raise
    if not allow_failure and (failure or result is None):
        raise _KnownFailure('tf_binding_result_calculation_failed')
    record = dict(request=payload, selection=selected, handle=original, observation=observed,
        native_request=native_request, native_request_raw=raw_request.decode('utf-8'),
        result_sha256=None if result is None else digest(result))
    return result, record


def _worker_control(worker, request, operation, invocation, stage):
    """Check retained original worker metadata without reopening its workspace."""
    _closed(worker, 'request selection handle observation native_request native_request_raw result_sha256')
    selected, original, observed = worker['selection'], worker['handle'], worker['observation']
    _closed(selected, 'version command cwd environment policy request python implementation_files')
    root = _historical_store_root(worker, invocation, stage)
    directory = root / 'cache' / 'molecular-measurements' / digest(invocation['operation_key']) / stage
    expected = dict(operation=operation, arguments=dict(request=request))
    _require(_same(worker['request'], request) and _same(selected['request'], expected)
        and selected['version'] == 'ordinary_molecular_execution_v1'
        and selected['command'] == [selected['python']['path'], '-m', _WORKERS[operation],
            str(directory / 'worker-request.json'), str(directory / 'worker-result.json')]
        and original['command'] == selected['command'] and original['cwd'] == selected['cwd'] == str(directory)
        and original['stdout'] == str(directory / 'stdout') and original['stderr'] == str(directory / 'stderr')
        and observed['terminal'] is True and observed['quiescent'] is True
        and _same(original['metadata']['policy'], selected['policy'])
        and _same(observed['metadata']['policy'], selected['policy'])
        and _same(LocalJobPolicy(**selected['policy']).to_dict(), selected['policy']),
        'worker_control_conflict')
    paths = original['paths']
    _require(all(type(p) is str and PurePosixPath(p).parent == directory for p in paths.values()),
        'worker_handle_conflict')
    raw = worker['native_request_raw']
    _require(type(raw) is str and hashlib.sha256(raw.encode('utf-8')).hexdigest() == original['request_sha256']
        and _same(decode_json(raw.encode('utf-8')), worker['native_request'])
        and _same(worker['native_request'], dict(command=selected['command'], cwd=str(directory),
            file_bytes=selected['policy']['scratch_bytes'], ready_path=paths['ready'], release_path=paths['release'],
            result_path=paths['result'], stdin_path=None, env=selected['environment'])),
        'worker_handle_conflict')
    return root


def _native_manifest(value):
    _closed(value, 'version value files calls failures')
    _require(value['version'] == 'tf_binding_native_manifest_v1'
        and type(value['files']) is list and type(value['calls']) is list
        and type(value['failures']) is list, 'native_manifest_invalid')
    native = core.validate_tf_binding_native_value(value['value'])
    seen, paths = set(), set()
    for row in value['files']:
        _closed(row, 'file_id role relative_path format sha256 size_bytes')
        _require(row['file_id'] not in seen and row['relative_path'] not in paths
            and row['role'] in ('native_result', 'scores'),
            'native_manifest_file_invalid')
        expected = 'native-result.json' if row['role'] == 'native_result' else None
        _require(row['relative_path'] == expected if expected is not None
            else type(row['relative_path']) is str and _SCORE_NAME.fullmatch(row['relative_path']),
            'native_manifest_path_invalid')
        _identity(dict(artifact_ref='artifact_' + row['sha256'], sha256=row['sha256'],
            size_bytes=row['size_bytes'], format=row['format']))
        if row['role'] == 'native_result':
            _require(row['file_id'] == 'native-result' and row['format'] == 'tf_binding_native_result_json',
                'native_manifest_file_invalid')
        else:
            matches = [(i, scan) for i, scan in enumerate(native['scans'])
                if scan['score_file_id'] == row['file_id']]
            _require(len(matches) == 1, 'native_manifest_scan_conflict')
            index, scan = matches[0]
            _require(row['relative_path'] == 'scores-%06d.f32' % index
                and row['format'] == 'tf_binding_scores_float32'
                and all(row[key] == scan[key] for key in ('sha256', 'size_bytes')),
                'native_manifest_scan_conflict')
        seen.add(row['file_id']); paths.add(row['relative_path'])
    _require([row.get('scan_id') for row in value['calls']] == [row['scan_id'] for row in native['scans']],
        'native_calls_conflict')
    for row in value['calls']:
        _closed(row, 'scan_id state failure_code')
        _require(row['state'] in ('not_called', 'returned', 'raised')
            and (row['failure_code'] is None or type(row['failure_code']) is str), 'native_calls_conflict')
    return value


def _capture_native(registry, invocation, arguments, intent, manifest, worker, directory):
    """Retain actual closed outputs before any result parsing or calculation."""
    root = directory / 'tf-binding-native'
    rows, captured = [], []
    valid = None
    try:
        valid = _native_manifest(manifest) if manifest is not None else None
    except (ValueError, TypeError, KeyError):
        pass
    if valid is not None:
        native = valid['value']
        expected_inputs = [{'input_id': v['input_id'], **{k: v['artifact'][k]
            for k in ('artifact_ref', 'sha256', 'size_bytes')}} for v in intent['inputs']]
        if not (native['invocation_id'] == intent['native_request']['invocation']['invocation_id']
                and _same(native['parameters'], arguments['parameters'])
                and _same(native['scan_selection'], arguments['scan_selection'])
                and _same(native['input_identities'], expected_inputs)):
            valid = None
    declarations = {} if valid is None else {row['relative_path']: row for row in valid['files']}
    try:
        regular_directory = stat.S_ISDIR(root.lstat().st_mode)
    except OSError:
        regular_directory = False
    if regular_directory:
        names = [p.name for p in root.iterdir() if p.name == 'native-result.json' or _SCORE_NAME.fullmatch(p.name)]
    else:
        names = []
    for name in sorted(set(names) | set(declarations)):
        declaration = declarations.get(name)
        file, qualification = None, 'native_output_unbound' if declaration is None else None
        try:
            file = capture_native_file(registry.store, directory=str(root), relative_path=name,
                format='tf_binding_native_result_json' if name == 'native-result.json'
                    else 'tf_binding_scores_float32', media_type='application/octet-stream')
        except NativeFileCaptureError as error:
            if error.code != 'capture_file_unavailable':
                raise
            qualification = 'native_output_unavailable'
        else:
            captured.append(file['artifact_ref'])
            if declaration is not None and any(file[k] != declaration[k] for k in ('sha256', 'size_bytes')):
                qualification = 'native_output_identity_conflict'
        rows.append(dict(relative_path=name, declared=deepcopy(declaration), file=file,
            qualification=qualification))
    logs = []
    for name in ('stdout', 'stderr'):
        file = None
        try:
            file = capture_native_file(registry.store, directory=str(directory), relative_path=name,
                format='tf_binding_native_log', media_type='application/octet-stream')
        except NativeFileCaptureError as error:
            if error.code != 'capture_file_unavailable':
                raise
        if file is not None:
            captured.append(file['artifact_ref'])
        logs.append(dict(name=name, file=file))
    excluded = list(dict.fromkeys(row['artifact']['artifact_ref'] for row in intent['inputs']))
    stamp = directory.parent / 'publication-time.json'
    if not stamp.exists():
        _immutable(stamp, dict(retrieved_at=datetime.now(timezone.utc).isoformat()))
    body = dict(version=CAPTURE_VERSION, invocation=invocation,
        original_manifest=deepcopy(manifest), outputs=rows, logs=logs, input_artifact_refs=excluded)
    manifest_ref = registry.store.artifact(canonical(body), 'application/json')
    control = dict(version=CAPTURE_CONTROL_VERSION, invocation=invocation, arguments=arguments,
        input_artifact_refs=excluded, input_admissions=intent['input_admissions'],
        input_decision_admissions=intent['input_decision_admissions'], inputs=intent['inputs'],
        selected_resource=intent['selected_resource'], policy=intent['policy'],
        native_worker=worker, manifest_ref=manifest_ref)
    control_ref = registry.store.artifact(canonical(control), 'application/json')
    parents = list(dict.fromkeys(i['reference'] for i in arguments['inputs'] if i['namespace'] == 'source'))
    source = registry._put('source', dict(provider=TOOL,
        accession=identity('operation', dict(key=invocation['operation_key'], name=TOOL, arguments=arguments)),
        uri=None, artifact_ref=manifest_ref, request_ref=control_ref, text_ref=None,
        version=CAPTURE_VERSION, retrieved_at=decode_json(stamp.read_bytes())['retrieved_at'],
        parent_source_refs=parents, auxiliary_artifact_refs=[ref for ref in dict.fromkeys(captured)
            if ref not in excluded]), origin='tool')
    if valid is None:
        return source, [], excluded, None
    native = valid['value']
    files = []
    for row in rows:
        declaration = row['declared']
        if declaration is None:
            continue
        file = row['file'] if row['qualification'] is None else None
        files.append(dict(file_id=declaration['file_id'], role=declaration['role'],
            path=None if file is None else _path(registry, file), artifact=None if file is None else
                dict(raw_artifact_ref=file['artifact_ref'], source_ref=source['id'], sha256=file['sha256'],
                    size_bytes=file['size_bytes']), capture=dict(state='missing' if file is None else 'complete',
                    byte_start_0based=0, byte_end_0based_exclusive=0 if file is None else file['size_bytes'],
                    original_size_bytes=declaration['size_bytes'])))
    metadata = [row for row in files if row['role'] == 'native_result' and row['path'] is not None]
    for log in logs:
        file = log['file']
        files.append(dict(file_id='native-' + log['name'], role='native_log',
            path=None if file is None else _path(registry, file), artifact=None if file is None else
                dict(raw_artifact_ref=file['artifact_ref'], source_ref=source['id'], sha256=file['sha256'],
                    size_bytes=file['size_bytes']), capture=dict(state='missing' if file is None else 'complete',
                    byte_start_0based=0, byte_end_0based_exclusive=0 if file is None else file['size_bytes'],
                    original_size_bytes=None if file is None else file['size_bytes'])))
    if len(metadata) != 1:
        return source, files, excluded, None
    return source, files, excluded, dict(metadata_file_id=metadata[0]['file_id'], value=native)


def _capture_component(registry, directory, declaration, name, format):
    _closed(declaration, 'relative_path format sha256 size_bytes')
    _require(declaration['relative_path'] == name and declaration['format'] == format,
        'component_declaration_conflict')
    file = capture_native_file(registry.store, directory=str(directory), relative_path=name,
        format=format, media_type='application/json')
    _require(type(declaration['size_bytes']) is int
        and all(file[k] == declaration[k] for k in ('sha256', 'size_bytes')), 'component_identity_conflict')
    return file


def _packet(value):
    return dict(version=PACKET_VERSION, value={k: deepcopy(v) for k, v in value.items()
        if k not in ('version', 'source_ref')})


def _metadata_publication(registry, source_ref, *, recovery_context=None, recovery_operation_key=None):
    source = registry.store.get(source_ref); immutable_record(source)
    _require(source.get('record_type') == 'source' and source.get('origin') == 'tool'
        and source.get('provider') == TOOL and source.get('version') == SOURCE_VERSION
        and 'operand_refs' not in source, 'producer_required')
    producer = _recorded_molecular_producer_details(registry, source_ref, TOOL,
        recovery_context=recovery_context, recovery_operation_key=recovery_operation_key)
    public = validate_tf_binding_return(producer['outcome']['result'])
    _require(public['source_ref'] == source_ref and producer['outcome']['record_refs'] == [source_ref],
        'publication_conflict')
    arguments = _arguments(producer['arguments'])
    if arguments['mode'] == 'run_native':
        parents = source.get('parent_source_refs')
        _require(type(parents) is list and len(parents) == 1, 'capture_source_conflict')
        capture = registry.store.get(parents[0]); immutable_record(capture)
        _require(capture.get('origin') == 'tool' and capture.get('provider') == TOOL
            and capture.get('version') == CAPTURE_VERSION
            and capture.get('accession') == producer['operation_ref'], 'capture_source_conflict')
    else:
        _require(source.get('parent_source_refs') == [arguments['result_ref']], 'original_source_conflict')
    return dict(source=source, producer=producer, public=public, control=None,
        received_input=None, source_decision_admission=None)


def _historical_store_root(worker, invocation, stage):
    supplied = worker['selection']['cwd']
    _require(type(supplied) is str, 'worker_selection_conflict')
    directory = PurePosixPath(supplied)
    _require(directory.is_absolute() and str(directory) == supplied
        and '..' not in directory.parts and directory.parts[-4:] == ('cache', 'molecular-measurements',
            digest(invocation['operation_key']), stage), 'worker_selection_conflict')
    return directory.parents[3]


def _capture_descriptors(registry, capture, body, *, store_root):
    """Reproduce original parser operands from authenticated capture metadata."""
    rows = []
    for item in body['outputs']:
        declaration = item['declared']
        if declaration is None:
            continue
        file = _file(registry, item['file']) if item['file'] is not None else None
        if item['qualification'] is not None:
            file = None
        rows.append(dict(file_id=declaration['file_id'], role=declaration['role'],
            path=None if file is None else _path(registry, file, store_root=store_root),
            artifact=None if file is None else dict(raw_artifact_ref=file['artifact_ref'],
                source_ref=capture['id'], sha256=file['sha256'], size_bytes=file['size_bytes']),
            capture=dict(state='missing' if file is None else 'complete', byte_start_0based=0,
                byte_end_0based_exclusive=0 if file is None else file['size_bytes'],
                original_size_bytes=declaration['size_bytes'])))
    for item in body['logs']:
        file = _file(registry, item['file']) if item['file'] is not None else None
        rows.append(dict(file_id='native-' + item['name'], role='native_log',
            path=None if file is None else _path(registry, file, store_root=store_root),
            artifact=None if file is None else dict(raw_artifact_ref=file['artifact_ref'],
                source_ref=capture['id'], sha256=file['sha256'], size_bytes=file['size_bytes']),
            capture=dict(state='missing' if file is None else 'complete', byte_start_0based=0,
                byte_end_0based_exclusive=0 if file is None else file['size_bytes'],
                original_size_bytes=None if file is None else file['size_bytes'])))
    return rows


def _capture_body(registry, capture, body, manifest, invocation, arguments, input_refs):
    _closed(body, 'version invocation original_manifest outputs logs input_artifact_refs')
    _require(body['version'] == CAPTURE_VERSION and _same(body['invocation'], invocation)
        and body['input_artifact_refs'] == input_refs and type(body['outputs']) is list
        and type(body['logs']) is list, 'native_capture_conflict')
    declared = {row['relative_path']: row for row in manifest['files']}
    names, files = set(), []
    for row in body['outputs']:
        _closed(row, 'relative_path declared file qualification')
        name = row['relative_path']
        _require(type(name) is str and name not in names
            and (name == 'native-result.json' or _SCORE_NAME.fullmatch(name))
            and _same(row['declared'], declared.get(name))
            and row['qualification'] in (None, 'native_output_unbound',
                'native_output_unavailable', 'native_output_identity_conflict'), 'native_capture_conflict')
        names.add(name)
        if row['file'] is not None:
            file = _file(registry, row['file']); files.append(file['artifact_ref'])
            _require(file['format'] == ('tf_binding_native_result_json'
                if name == 'native-result.json' else 'tf_binding_scores_float32'), 'native_capture_conflict')
        if row['qualification'] is None:
            _require(row['file'] is not None and row['declared'] is not None
                and all(row['file'][key] == row['declared'][key] for key in ('sha256', 'size_bytes')),
                'native_capture_conflict')
    _require(set(declared) <= names and [row.get('name') for row in body['logs']] == ['stdout', 'stderr'],
        'native_capture_conflict')
    for row in body['logs']:
        _closed(row, 'name file')
        if row['file'] is not None:
            file = _file(registry, row['file']); files.append(file['artifact_ref'])
            _require(file['format'] == 'tf_binding_native_log', 'native_capture_conflict')
    parents = list(dict.fromkeys(row['reference'] for row in arguments['inputs'] if row['namespace'] == 'source'))
    _require(capture.get('parent_source_refs') == parents
        and capture.get('auxiliary_artifact_refs') == [ref for ref in dict.fromkeys(files)
            if ref not in input_refs], 'native_capture_conflict')
    return body


def _control(registry, publication, seen):
    source, producer = publication['source'], publication['producer']
    _require(source['id'] not in seen, 'source_lineage_cycle'); seen = {*seen, source['id']}
    value = decode_json(_publication_bytes(registry.store, source['request_ref']))
    _closed(value, 'version arguments invocation capture_source sheet_file components_file source_admission source_decision_admission original_source policy selected_resource worker public_packet_ref input_artifact_refs')
    _require(value['version'] == CONTROL_VERSION and _same(value['arguments'], producer['arguments'])
        and _same(value['invocation'], producer['invocation'])
        and value['public_packet_ref'] == source['artifact_ref'], 'control_conflict')
    sheet, components = _file(registry, value['sheet_file']), _file(registry, value['components_file'])
    _require(sheet['format'] == core.SHEET_VERSION and components['format'] == core.COMPONENTS_VERSION,
        'component_format_conflict')
    capture = registry.store.get(value['capture_source']['source_ref']); immutable_record(capture)
    _require(digest(capture) == value['capture_source']['record_sha256']
        and capture.get('provider') == TOOL and capture.get('origin') == 'tool'
        and capture.get('version') == CAPTURE_VERSION, 'capture_source_conflict')
    arguments = _arguments(value['arguments'])
    if arguments['mode'] == 'run_native':
        native_control = decode_json(_publication_bytes(registry.store, capture['request_ref']))
        _closed(native_control, 'version invocation arguments input_artifact_refs input_admissions input_decision_admissions inputs selected_resource policy native_worker manifest_ref')
        _require(native_control['version'] == CAPTURE_CONTROL_VERSION
            and _same(native_control['invocation'], value['invocation'])
            and _same(native_control['arguments'], arguments)
            and native_control['manifest_ref'] == capture['artifact_ref']
            and native_control['input_artifact_refs'] == value['input_artifact_refs'], 'capture_source_conflict')
        context = _context(registry.store, value['invocation'])
        native_request = _native_request(value['invocation'], arguments, native_control['inputs'])
        native_root = _worker_control(native_control['native_worker'], native_request,
            'tf_binding_native', value['invocation'], 'native')
        selected = native_control['selected_resource']
        _closed(selected, 'resource_id resource environment')
        _require(type(selected['resource_id']) is str and bool(selected['resource_id'])
            and type(selected['resource']) is dict and selected['resource'].get('kind') == 'local'
            and _same(selected['resource'].get('policy'), native_control['policy'])
            and _same(native_control['native_worker']['selection']['policy'], native_control['policy'])
            and _same(selected['environment'], dict(version='tf_binding_execution_selection_v1',
                environment_realization='operation_scoped_tmp_and_cache_v1')), 'resource_allocation_conflict')
        _require(_same(value['policy'], native_control['policy'])
            and _same(value['selected_resource'], selected), 'action_policy_conflict')
        _check_inputs(registry, context, arguments, native_control['inputs'],
            native_control['input_admissions'], native_control['input_decision_admissions'],
            value['invocation']['decision_index'], store_root=native_root)
        captured = decode_json(_publication_bytes(registry.store, capture['artifact_ref']))
        manifest = _native_manifest(captured['original_manifest'])
        _capture_body(registry, capture, captured, manifest, value['invocation'], arguments,
            value['input_artifact_refs'])
        _require(digest(manifest) == native_control['native_worker']['result_sha256'], 'native_manifest_conflict')
        _require(manifest['value']['invocation_id'] == native_request['invocation']['invocation_id']
            and _same(manifest['value']['parameters'], arguments['parameters'])
            and _same(manifest['value']['scan_selection'], arguments['scan_selection'])
            and _same(manifest['value']['input_identities'], [{'input_id': row['input_id'],
                **{key: row['artifact'][key] for key in ('artifact_ref', 'sha256', 'size_bytes')}}
                for row in native_control['inputs']]), 'native_invocation_conflict')
        root = _historical_store_root(value['worker'], value['invocation'], 'calculation')
        _require(root == native_root, 'worker_selection_conflict')
        files = _capture_descriptors(registry, capture, captured, store_root=root)
        metadata = [row for row in files if row['role'] == 'native_result' and row['path'] is not None]
        _require(len(metadata) == 1, 'native_metadata_unavailable')
        expected_request = dict(version='tf_binding_result_request_v1', mode='parse',
            inputs=native_control['inputs'], invocation=native_request['invocation'],
            execution=dict(metadata_file_id=metadata[0]['file_id'], value=manifest['value']), files=files,
            saved=None, selection=arguments['selection'], projection_source_ref=capture['id'])
        _require(source.get('parent_source_refs') == [capture['id']]
            and capture.get('accession') == producer['operation_ref']
            and value['source_admission'] is value['source_decision_admission'] is value['original_source'] is None,
            'capture_source_conflict')
    else:
        original = value['original_source']; _closed(original, 'source_ref record_sha256')
        _require(arguments['mode'] == 'calculate_saved' and original['source_ref'] == arguments['result_ref']
            and source.get('parent_source_refs') == [original['source_ref']]
            and value['selected_resource'] is None, 'original_source_conflict')
        previous = _metadata_publication(registry, original['source_ref'])
        _require(digest(previous['source']) == original['record_sha256'], 'original_source_conflict')
        context = _context(registry.store, value['invocation'])
        _frozen_admission(registry.store, context, value['source_admission'], original['source_ref'],
            'source', value['invocation']['decision_index'])
        _require(_same(_source_admission(registry, context, original['source_ref'],
            value['invocation']['decision_index']), value['source_decision_admission']),
            'source_decision_admission_conflict')
        prior = _control(registry, previous, seen)
        _require(_same(sheet, prior['sheet_file']) and _same(value['capture_source'], prior['capture_source'])
            and value['input_artifact_refs'] == prior['input_artifact_refs'], 'saved_sheet_conflict')
        root = _historical_store_root(value['worker'], value['invocation'], 'calculation')
        expected_request = dict(version='tf_binding_result_request_v1', mode='calculate_saved',
            inputs=None, invocation=None, execution=None, files=None,
            saved=dict(file=sheet, path=_path(registry, sheet, store_root=root)),
            selection=arguments['selection'], projection_source_ref=arguments['result_ref'])
    expected = list(dict.fromkeys([*capture.get('auxiliary_artifact_refs', []),
        sheet['artifact_ref'], components['artifact_ref']]))
    _require(source.get('auxiliary_artifact_refs') == [ref for ref in expected
        if ref not in value['input_artifact_refs']], 'private_files_conflict')
    _worker_control(value['worker'], expected_request, 'tf_binding_result', value['invocation'], 'calculation')
    _require(_same(LocalJobPolicy(**value['policy']).to_dict(), value['policy'])
        and _same(value['worker']['selection']['policy'], value['policy']), 'action_policy_conflict')
    if value['selected_resource'] is not None:
        selected = value['selected_resource']
        _closed(selected, 'resource_id resource environment')
        _require(type(selected['resource_id']) is str and bool(selected['resource_id'])
            and type(selected['resource']) is dict and selected['resource'].get('kind') == 'local'
            and _same(selected['resource'].get('policy'), value['policy'])
            and _same(selected['environment'], dict(version='tf_binding_execution_selection_v1',
                environment_realization='operation_scoped_tmp_and_cache_v1')), 'resource_allocation_conflict')
    public = publication['public']
    expected_result = dict(version='tf_binding_result_output_v1', requested_selection=arguments['selection'],
        selection=public['selection'], value=dict(public, source_ref=expected_request['projection_source_ref']),
        sheet=None if arguments['mode'] == 'calculate_saved' else dict(relative_path='sheet.json',
            format=core.SHEET_VERSION, sha256=sheet['sha256'], size_bytes=sheet['size_bytes']),
        components=dict(relative_path='components.json', format=core.COMPONENTS_VERSION,
            sha256=components['sha256'], size_bytes=components['size_bytes']))
    _require(value['worker']['result_sha256'] == digest(expected_result), 'worker_result_conflict')
    return value


def _read_tf_binding_publication(registry, context, reader, source_ref, *, recovery_operation_key=None,
        require_sheet=False, before_decision_index=None):
    EpisodeReturnRecords(registry.store, context.run_id, failure_prefix='tf_binding_').authenticate(context)
    publication = _metadata_publication(registry, source_ref,
        recovery_context=context if recovery_operation_key is not None else None,
        recovery_operation_key=recovery_operation_key)
    producer = publication['producer']['invocation']
    own = recovery_operation_key is not None and producer['operation_key'] == recovery_operation_key
    own &= (producer['run_id'], producer['episode_id']) == (context.run_id, context.episode_id)
    cutoff = _current_cutoff(registry, context) if before_decision_index is None else before_decision_index
    if not own:
        publication['received_input'] = _admit(registry.store, reader, context, source_ref, 'source', cutoff)
        active = registry._current_invocation.get()
        if before_decision_index is not None or active is not None and active[0] is context:
            publication['source_decision_admission'] = _source_admission(registry, context, source_ref, cutoff)
    packet = decode_json(_publication_bytes(registry.store, publication['source']['artifact_ref']))
    _require(_same(packet, _packet(publication['public'])), 'public_packet_conflict')
    if require_sheet:
        publication['control'] = _control(registry, publication, set())
    return publication


def read_retained_tf_binding_publication(registry, context, reader, source_ref, *, recovery_operation_key=None):
    with registry.store.read_snapshot():
        return _read_tf_binding_publication(registry, context, reader, source_ref,
            recovery_operation_key=recovery_operation_key)['public']


def _resolved_selection(public, selected):
    selected = _result_selection(selected)
    return core.validate_tf_binding_selection(dict(version='tf_binding_selection_v1',
        scan_ids=[row['scan_id'] for row in public['available_scans']]
            if selected['scope'] == 'all_retained_scans' else selected['scan_ids'],
        **{key: selected[key] for key in ('raw_threshold', 'offset', 'limit')}))


def _publish(registry, arguments, invocation, prepared, result, worker, directory):
    _require(registry.store.db.in_transaction, 'publication_transaction_required')
    _closed(result, 'version requested_selection selection value sheet components')
    _require(result['version'] == 'tf_binding_result_output_v1'
        and _same(result['requested_selection'], arguments['selection']), 'worker_result_conflict')
    public_value = validate_tf_binding_value({k: v for k, v in result['value'].items()
        if k not in ('version', 'source_ref')})
    _require(result['value']['version'] == core.RETURN_VERSION
        and result['value']['source_ref'] == prepared['projection_source_ref']
        and _same(public_value['selection'], result['selection'])
        and _same(_resolved_selection(public_value, arguments['selection']), result['selection']),
        'worker_result_conflict')
    if arguments['mode'] == 'calculate_saved':
        _require(result['sheet'] is None, 'worker_result_conflict')
        sheet = _file(registry, prepared['sheet_file'])
    else:
        sheet = _capture_component(registry, directory, result['sheet'], 'sheet.json', core.SHEET_VERSION)
    components = _capture_component(registry, directory, result['components'], 'components.json', core.COMPONENTS_VERSION)
    capture = prepared['capture_source']
    packet_ref = registry.store.artifact(canonical(dict(version=PACKET_VERSION, value=public_value)), 'application/json')
    control = dict(version=CONTROL_VERSION, arguments=arguments, invocation=invocation,
        capture_source=dict(source_ref=capture['id'], record_sha256=digest(capture)), sheet_file=sheet,
        components_file=components, source_admission=prepared['source_admission'],
        source_decision_admission=prepared['source_decision_admission'], original_source=prepared['original_source'],
        policy=prepared['policy'], selected_resource=prepared['selected_resource'],
        worker=worker, public_packet_ref=packet_ref, input_artifact_refs=prepared['input_artifact_refs'])
    control_ref = registry.store.artifact(canonical(control), 'application/json')
    auxiliary = list(dict.fromkeys([*capture.get('auxiliary_artifact_refs', []), sheet['artifact_ref'], components['artifact_ref']]))
    source = registry._put('source', dict(provider=TOOL, accession=None, uri=None, artifact_ref=packet_ref,
        text_ref=None, request_ref=control_ref, version=SOURCE_VERSION,
        retrieved_at=datetime.now(timezone.utc).isoformat(), parent_source_refs=[capture['id']]
            if arguments['mode'] == 'run_native' else [arguments['result_ref']],
        auxiliary_artifact_refs=[ref for ref in auxiliary if ref not in prepared['input_artifact_refs']]), origin='tool')
    return tf_binding_return(public_value, source_ref=source['id'])


def read_tf_binding_action_result(registry, context, arguments, operation_key, *, reader):
    arguments = _arguments(arguments)
    active = registry._current_invocation.get()
    recovery = context if active is not None and active[0] is context and active[4] == operation_key else None
    details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
        recovery_context=recovery, recovery_operation_key=operation_key if recovery is not None else None)
    outcome = details['outcome']
    _require(outcome.get('status') in ('completed', 'partial') and type(outcome.get('result')) is dict,
        'action_result_unavailable')
    public = validate_tf_binding_return(outcome['result'])
    _require(outcome.get('record_refs') == [public['source_ref']], 'action_source_conflict')
    redisplay = arguments['mode'] != 'run_native' and public['source_ref'] == arguments['result_ref']
    with registry.store.read_snapshot():
        publication = _read_tf_binding_publication(registry, context, reader, public['source_ref'],
            recovery_operation_key=None if redisplay else operation_key,
            before_decision_index=details['invocation']['decision_index'])
    _require(_same(publication['public'], public), 'action_source_conflict')
    if redisplay:
        _require(outcome.get('changed_record_refs') == [], 'action_source_conflict')
        if arguments['mode'] == 'calculate_saved':
            _require(_same(_resolved_selection(public, arguments['selection']), public['selection']),
                'action_source_conflict')
    else:
        _require(publication['producer']['operation_ref'] == details['operation_ref'], 'action_source_conflict')
    return public


def _outcome(arguments, operation_key, public, *, redisplay=None, native_transport_failed=False):
    partial = public['status'] != 'complete' or bool(public['issues']) or native_transport_failed
    result = dict(status='partial' if partial else 'completed', operation_ref=identity('operation',
        dict(key=operation_key, name=TOOL, arguments=arguments)), record_refs=[public['source_ref']],
        changed_record_refs=[] if redisplay is not None else [public['source_ref']], result=public,
        feedback=dict(category='representation', code='tf_binding_selected_result_partial',
            source_ref=public['source_ref']) if partial else None)
    if redisplay is not None:
        result['status'], result['feedback'] = redisplay['status'], deepcopy(redisplay.get('feedback'))
    elif native_transport_failed:
        result['feedback'] = dict(category='execution', code='tf_binding_native_transport_partial',
            source_ref=public['source_ref'])
    return result


def _failure(registry, arguments, operation_key, error):
    message = str(error)
    code = message if re.fullmatch(r'[a-z][a-z0-9_]*', message) else 'tf_binding_execution_failed'
    diagnostic = registry.store.artifact(canonical(dict(version='tf_binding_diagnostic_v1',
        exception_type=type(error).__module__ + '.' + type(error).__name__, exception_message=message)), 'application/json')
    return dict(status='unavailable' if isinstance(error, (_KnownUnavailable, OSError))
        or code.endswith('_unavailable') else 'failed' if isinstance(error, _KnownFailure)
        else 'invalid' if isinstance(error, (ValueError, TypeError, KeyError)) else 'failed',
        operation_ref=identity('operation', dict(key=operation_key, name=TOOL, arguments=arguments)),
        record_refs=[], changed_record_refs=[], result=None,
        feedback=dict(category='execution', code=code, diagnostic_ref=diagnostic))


async def execute_tf_binding_tool(registry, arguments, *, scope, operation_key, authority):
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
                _require(_same(read_tf_binding_action_result(registry, context, arguments, operation_key,
                    reader=reader), outcome['result']), 'cached_result_conflict')
            else:
                _require(outcome.get('status') in ('failed', 'invalid', 'unavailable')
                    and outcome.get('result') is None and outcome.get('record_refs') == [], 'cached_failure_conflict')
            return outcome
        attempt_possible = False
        try:
            arguments = _arguments(arguments)
            configuration = _configuration(registry._tf_binding_configuration)
            redisplay = None
            if arguments['mode'] != 'run_native':
                _require(configuration['saved_modes'], 'saved_modes_not_configured')
                with registry.store.read_snapshot():
                    publication = _read_tf_binding_publication(registry, context, reader,
                        arguments['result_ref'], before_decision_index=invocation['decision_index'])
                if arguments['mode'] == 'read_stored' or _same(
                        _resolved_selection(publication['public'], arguments['selection']),
                        publication['public']['selection']):
                    public, prepared = publication['public'], None
                    redisplay = publication['producer']['outcome']
                else:
                    with registry.store.read_snapshot():
                        publication = _read_tf_binding_publication(registry, context, reader,
                            arguments['result_ref'], require_sheet=True,
                            before_decision_index=invocation['decision_index'])
                    previous = publication['control']
                    prepared = dict(capture_source=registry.store.get(previous['capture_source']['source_ref']),
                        sheet_file=previous['sheet_file'], input_artifact_refs=previous['input_artifact_refs'],
                        source_admission=publication['received_input'],
                        source_decision_admission=publication['source_decision_admission'],
                        original_source=dict(source_ref=publication['source']['id'], record_sha256=digest(publication['source'])),
                        projection_source_ref=arguments['result_ref'], native_transport_failed=False,
                        policy=configuration['policy'], selected_resource=None)
                    request = dict(version='tf_binding_result_request_v1', mode='calculate_saved',
                        inputs=None, invocation=None, execution=None, files=None,
                        saved=dict(file=prepared['sheet_file'], path=_path(registry, prepared['sheet_file'])),
                        selection=arguments['selection'], projection_source_ref=arguments['result_ref'])
            else:
                intent_path = directory / 'tf-binding-intent.json'
                if intent_path.exists():
                    # Existing preparation is not proof that dispatch never
                    # happened. A conflicting control cannot close old work.
                    attempt_possible = True
                    intent = decode_json(intent_path.read_bytes())
                    _closed(intent, 'version arguments invocation selected_resource policy inputs input_admissions input_decision_admissions native_request')
                    _require(intent['version'] == 'ordinary_tf_binding_intent_v1'
                        and _same(intent['arguments'], arguments) and _same(intent['invocation'], invocation),
                        'original_intent_conflict')
                    _check_inputs(registry, context, arguments, intent['inputs'], intent['input_admissions'],
                        intent['input_decision_admissions'], invocation['decision_index'])
                else:
                    _require(len(configuration['resources']) == 1, 'native_resource_required')
                    selected = configuration['resources'][0]
                    _run_selection(registry, owner, selected, configuration['policy'])
                    inputs, admissions, decisions = _fresh_inputs(registry, context, reader,
                        arguments, invocation['decision_index'])
                    native_request = _native_request(invocation, arguments, inputs)
                    intent = dict(version='ordinary_tf_binding_intent_v1', arguments=arguments,
                        invocation=invocation, selected_resource=selected, policy=configuration['policy'],
                        inputs=inputs, input_admissions=admissions, input_decision_admissions=decisions,
                        native_request=native_request)
                    _immutable(intent_path, intent)
                native_directory = _directory(directory / 'native')
                native_directory.mkdir(exist_ok=True)
                _require(_same(intent['native_request'], _native_request(invocation, arguments, intent['inputs'])),
                    'native_request_conflict')
                _worker_dispatch(registry, owner, intent['native_request'], native_directory,
                    'tf_binding_native', intent['policy'], intent['selected_resource'])
                attempt_possible = True
                work = await registry._sequence_worker_async('tf_binding_native',
                    dict(request=intent['native_request']), directory=native_directory, owned_directory=native_directory)
                authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
                _check_inputs(registry, context, arguments, intent['inputs'], intent['input_admissions'],
                    intent['input_decision_admissions'], invocation['decision_index'])
                manifest, native_worker = _worker_record(registry, work, intent['native_request'],
                    native_directory, 'tf_binding_native', allow_failure=True)
                _require(_same(native_worker['selection']['policy'], intent['policy']),
                    'action_policy_conflict')
                with registry.store.transaction():
                    capture, files, excluded, execution = _capture_native(registry, invocation,
                        arguments, intent, manifest, native_worker, native_directory)
                if execution is None:
                    raise _KnownUnavailable('tf_binding_native_metadata_unavailable')
                prepared = dict(capture_source=capture, sheet_file=None, input_artifact_refs=excluded,
                    source_admission=None, source_decision_admission=None, original_source=None,
                    projection_source_ref=capture['id'], native_transport_failed=
                        native_worker['observation']['metadata'].get('native_returncode') != 0,
                    policy=intent['policy'], selected_resource=intent['selected_resource'])
                request = dict(version='tf_binding_result_request_v1', mode='parse', inputs=intent['inputs'],
                    invocation=intent['native_request']['invocation'], execution=execution, files=files,
                    saved=None, selection=arguments['selection'], projection_source_ref=capture['id'])
            if prepared is not None:
                calculation = _directory(directory / 'calculation')
                result_intent_path = calculation / 'tf-binding-result-intent.json'
                if result_intent_path.exists():
                    attempt_possible = True
                    result_intent = decode_json(result_intent_path.read_bytes())
                    _closed(result_intent, 'invocation arguments request source_admission source_decision_admission policy selected_resource')
                    _require(_same(result_intent['invocation'], invocation)
                        and _same(result_intent['arguments'], arguments)
                        and _same(result_intent['request'], request)
                        and _same(result_intent['source_admission'], prepared['source_admission'])
                        and _same(result_intent['source_decision_admission'], prepared['source_decision_admission']),
                        'original_result_intent_conflict')
                    if arguments['mode'] == 'run_native':
                        _require(_same(result_intent['policy'], intent['policy'])
                            and _same(result_intent['selected_resource'], intent['selected_resource']),
                            'action_policy_conflict')
                    else:
                        _require(result_intent['selected_resource'] is None, 'action_policy_conflict')
                    prepared['policy'] = result_intent['policy']
                    prepared['selected_resource'] = result_intent['selected_resource']
                else:
                    result_intent = dict(invocation=invocation, arguments=arguments, request=request,
                        source_admission=prepared['source_admission'],
                        source_decision_admission=prepared['source_decision_admission'],
                        policy=prepared['policy'], selected_resource=prepared['selected_resource'])
                    _immutable(result_intent_path, result_intent)
                _worker_dispatch(registry, owner, request, calculation, 'tf_binding_result',
                    prepared['policy'], prepared['selected_resource'])
                attempt_possible = True
                work = await registry._sequence_worker_async('tf_binding_result', dict(request=request),
                    directory=calculation, owned_directory=calculation)
                authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
                if arguments['mode'] == 'calculate_saved':
                    _require(_same(_admit(registry.store, reader, context, arguments['result_ref'], 'source',
                        invocation['decision_index']), prepared['source_admission'])
                        and _same(_source_admission(registry, context, arguments['result_ref'],
                            invocation['decision_index']), prepared['source_decision_admission']),
                        'source_admission_conflict')
                else:
                    _check_inputs(registry, context, arguments, intent['inputs'], intent['input_admissions'],
                        intent['input_decision_admissions'], invocation['decision_index'])
                result, worker = _worker_record(registry, work, request, calculation, 'tf_binding_result')
                _require(_same(worker['selection']['policy'], prepared['policy']), 'action_policy_conflict')
                with registry.store.transaction():
                    public = _publish(registry, arguments, invocation, prepared, result, worker, calculation)
                    outcome = _outcome(arguments, operation_key, public,
                        native_transport_failed=prepared['native_transport_failed'])
                    registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
                return outcome
            with registry.store.transaction():
                outcome = _outcome(arguments, operation_key, public, redisplay=redisplay)
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome
        except MolecularOperationUnpublished:
            raise
        except Exception as error:
            if attempt_possible and not isinstance(error, (_KnownFailure, _KnownUnavailable)):
                raise MolecularOperationUnpublished('tf_binding_original_action_unpublished') from error
            with registry.store.transaction():
                outcome = _failure(registry, arguments, operation_key, error)
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome


__all__ = ['TOOL', 'normalize_tf_binding_configuration', 'tf_binding_tool_arguments_schema',
    'execute_tf_binding_tool', 'read_tf_binding_action_result', 'read_retained_tf_binding_publication']
