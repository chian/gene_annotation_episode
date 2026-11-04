"""Ordinary owned parsing and saved views of authenticated MACS2 captures.

Native execution and capture admission retain their existing owners. This host
publishes only a compact Source packet; the common component File and all
execution/admission controls remain private and confer no File receipt.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from .acquisition import AcquisitionError
from .communication import plain
from .domain import ContractError, identity, obj
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .flux_balance_tools import _action_lock
from .macs2_peak_result_contracts import (
    TOOL, VERSION, PACKET_VERSION, CONTROL_VERSION, STORED_VERSION,
    macs2_peak_return, validate_macs2_peak_return, macs2_peak_fact_sources,
)
from .macs2_peak_result_worker import REQUEST_VERSION, RESULT_VERSION, COMPONENT_FORMAT
from .molecular_measurement_tools import (
    MolecularOperationUnpublished, authenticate_molecular_invocation,
    _recorded_molecular_action_details, _recorded_molecular_producer_details, _publication_bytes,
)
from .molecular_reference_privacy import molecular_reference_restriction
from .native_atac_differential_driver import _directory, _immutable, _regular, decode_json
from .native_file_capture import _identity, _metadata, capture_native_file
from .native_macs2_peak_execution import validate_macs2_peak_run_plan, validate_macs2_peak_seal
from .reference_edit_outcome_tools import (
    _admit as _source_admit, _frozen_admission as _source_frozen_admission,
    _invocation as _source_invocation, _context as _source_context, _current_cutoff,
)
from .alignment_site_native import immutable_record
from . import native_lifecycle as native


_SOURCE = re.compile(r'source_[0-9a-f]{24,64}\Z', re.ASCII)
_OPERATION = 'macs2_peak_result'
_CONTROL_FIELDS = ('version stored_version arguments invocation admission_invocation capture_source_refs '
    'capture_admissions native_admission source_admission original_source components_file public_packet_ref '
    'worker native_call_state')
_WORKER_FIELDS = 'request selection handle request_raw observation metadata result_raw'


def _require(condition, code):
    if not condition:
        raise ContractError('macs2_peak_' + code)


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()), 'closed_fields_required')


def _same(left, right):
    return canonical(left) == canonical(right)


def _source_call(function, *args, **kwargs):
    """Reuse the existing Source/prefix authority, retaining this tool's errors."""
    try:
        return function(*args, **kwargs)
    except ValueError as error:
        text = str(error)
        if text.startswith('reference_edit_outcome_'):
            raise ContractError('macs2_peak_' + text.removeprefix('reference_edit_outcome_')) from error
        raise


def _invocation(context, operation_key):
    return _source_call(_source_invocation, context, operation_key)


def _context(store, invocation):
    return _source_call(_source_context, store, invocation)


def _admit(registry, context, reader, reference, cutoff):
    admitted = _source_call(_source_admit, registry.store, reader, context, reference, 'source', cutoff)
    verdict = molecular_reference_restriction(registry.store, context, reference, 'source')
    _require(verdict is not False, 'source_not_received')
    return admitted


def _frozen_admission(registry, context, admitted, reference, cutoff):
    return _source_call(_source_frozen_admission, registry.store, context, admitted, reference, 'source', cutoff)


def _arguments(value):
    try:
        value = json.loads(canonical(value))
    except (TypeError, ValueError) as error:
        raise ContractError('macs2_peak_arguments_invalid') from error
    _require(type(value) is dict, 'arguments_invalid')
    mode = value.get('mode')
    if mode == 'parse':
        _closed(value, 'mode capture_source_refs row_window')
        refs = value['capture_source_refs']
        _require(type(refs) is list and bool(refs) and all(type(ref) is str and _SOURCE.fullmatch(ref) for ref in refs)
            and len(set(refs)) == len(refs), 'capture_sources_invalid')
    else:
        _require(mode in ('read_stored', 'project_saved'), 'mode_invalid')
        _closed(value, 'mode result_ref' if mode == 'read_stored' else 'mode result_ref row_window')
        _require(type(value['result_ref']) is str and _SOURCE.fullmatch(value['result_ref']) is not None, 'source_required')
    if mode != 'read_stored':
        window = value['row_window']
        _closed(window, 'offset limit')
        _require(type(window['offset']) is int and window['offset'] >= 0
            and type(window['limit']) is int and window['limit'] >= 1, 'row_window_invalid')
    return value


def macs2_peak_tool_contract():
    source = dict(type='string', pattern=r'^source_[0-9a-f]{24,64}$')
    window = obj(dict(offset=dict(type='integer', minimum=0), limit=dict(type='integer', minimum=1)))
    return dict(resources='local', invocation_route=dict(kind='direct'),
        description='Read requested native MACS2 peak measurements from selected retained captures.',
        input_schema=dict(anyOf=[
            obj(dict(mode=dict(const='parse'), capture_source_refs=dict(type='array', minItems=1,
                uniqueItems=True, items=source), row_window=window)),
            obj(dict(mode=dict(const='read_stored'), result_ref=source)),
            obj(dict(mode=dict(const='project_saved'), result_ref=source, row_window=window))]),
        instructions=('Select the explicitly received captures of one original MACS2 callpeak attempt, including its seal. '
            'parse preserves native XLS, narrowPeak and summit values, coordinates, counts, missingness and qualifications. '
            'Each representation keeps its own row ordinals; the representations are not separate peak sets. '
            'Select the row window explicitly. read_stored returns the original recorded view literally. '
            'project_saved returns that same Source for an unchanged window; a changed window uses the same retained '
            'components and publishes a distinct Source. '
            'These modes run no MACS2 command and reread no original treatment/control data. Only the result Source is delivered; '
            'native provenance and private component identities grant no Files.'))


def _file(registry, value):
    value = _identity(value)
    _require(value['format'] == COMPONENT_FORMAT, 'components_format_conflict')
    metadata = _metadata(registry.store, value['artifact_ref'])
    _require(metadata['sha256'] == value['sha256'] and metadata['size'] == value['size_bytes'], 'components_identity_conflict')
    return value


def _file_path(registry, file):
    return str(registry.store.path / 'artifacts' / file['sha256'][:2] / file['sha256'])


def _packet(public):
    return dict(version=PACKET_VERSION, value={key: deepcopy(value) for key, value in public.items()
        if key not in ('version', 'source_ref')})


def _public_from_worker(value):
    # Supplying a Source happens only after the public packet has its immutable
    # identity. Validate the source-free value directly, without a fake ID.
    from .macs2_peak_result_contracts import _validate
    return _validate('Value', value)


def _metadata_publication(registry, source_ref, *, recovery_context=None, recovery_operation_key=None):
    source = registry.store.get(source_ref)
    immutable_record(source)
    _require(source.get('record_type') == 'source' and source.get('origin') == 'tool'
        and source.get('provider') == TOOL and source.get('version') == VERSION
        and 'operand_refs' not in source, 'producer_required')
    producer = _recorded_molecular_producer_details(registry, source_ref, TOOL,
        recovery_context=recovery_context, recovery_operation_key=recovery_operation_key)
    arguments = _arguments(producer['arguments'])
    public = validate_macs2_peak_return(producer['outcome']['result'])
    _require(public['source_ref'] == source_ref and producer['outcome'].get('record_refs') == [source_ref],
        'publication_conflict')
    parents = arguments['capture_source_refs'] if arguments['mode'] == 'parse' else [arguments['result_ref']]
    _require(source.get('parent_source_refs') == parents, 'parent_sources_conflict')
    auxiliary = source.get('auxiliary_artifact_refs')
    _require(type(auxiliary) is list and len(auxiliary) == 1, 'private_files_conflict')
    _require(_metadata(registry.store, auxiliary[0])['media_type'] == 'application/json'
        and _metadata(registry.store, source['request_ref'])['media_type'] == 'application/json', 'private_files_conflict')
    return dict(source=source, producer=producer, public=public, packet=None, received_input=None,
        control=None, components_file=None)


def _worker_record(value, *, request, result_value=None):
    """Validate retained worker custody without reopening its old deployment."""
    _closed(value, _WORKER_FIELDS)
    _require(_same(value['request'], request), 'worker_request_conflict')
    selected, handle, observation = value['selection'], value['handle'], value['observation']
    _closed(selected, 'version command cwd environment policy request python implementation_files')
    payload = dict(operation=_OPERATION, arguments=dict(request=request))
    _require(selected['version'] == 'ordinary_molecular_execution_v1' and _same(selected['request'], payload)
        and type(selected['python']) is dict and set(selected['python']) == {'path', 'sha256'}
        and type(selected['python']['path']) is str
        and type(selected['python']['sha256']) is str
        and re.fullmatch(r'[0-9a-f]{64}', selected['python']['sha256']) is not None,
        'worker_selection_conflict')
    root = PurePosixPath(selected['cwd'])
    _require(root.is_absolute() and str(root) == selected['cwd'] and '..' not in root.parts,
        'worker_selection_conflict')
    expected_command = [selected['python']['path'], '-m', 'gene_annotation_episode.sequence_worker',
        str(root / 'worker-request.json'), str(root / 'worker-result.json')]
    _require(selected['command'] == expected_command and type(selected['environment']) is dict
        and all(type(key) is str and type(item) is str for key, item in selected['environment'].items())
        and type(selected['implementation_files']) is list and bool(selected['implementation_files'])
        and all(type(pin) is dict and set(pin) == {'path', 'sha256'} and type(pin['path']) is str
            and type(pin['sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', pin['sha256'])
            for pin in selected['implementation_files']), 'worker_selection_conflict')
    _require(type(handle) is dict and handle.get('version') == native.VERSION
        and handle.get('stage') in ('prepared', 'submitting', 'released')
        and handle.get('command') == selected['command'] and handle.get('cwd') == str(root)
        and handle.get('stdout') == str(root / 'stdout') and handle.get('stderr') == str(root / 'stderr')
        and _same(handle.get('metadata', {}).get('policy'), selected['policy']), 'worker_handle_conflict')
    paths = handle.get('paths')
    required = {'request', 'ready', 'release', 'status', 'result', 'launcher'}
    _require(type(paths) is dict and required <= paths.keys() and not paths.keys() - required - {'statistics', 'native_events'}
        and all(type(path) is str and PurePosixPath(path).parent == root and str(PurePosixPath(path)) == path
            and '..' not in PurePosixPath(path).parts for path in paths.values())
        and len(set(paths.values())) == len(paths), 'worker_handle_conflict')
    _require(not {str(root / name) for name in ('native-handle.json', 'execution-selection.json',
        'worker-request.json', 'worker-result.json', 'stdout', 'stderr', 'binding.json')}.intersection(paths.values())
        and all((role in paths) == (role in handle) for role in ('statistics', 'native_events')), 'worker_handle_conflict')
    _require(type(value['request_raw']) is str, 'worker_request_conflict')
    raw = value['request_raw'].encode('utf-8')
    expected = dict(command=selected['command'], cwd=str(root), file_bytes=selected['policy']['scratch_bytes'],
        ready_path=paths['ready'], release_path=paths['release'], result_path=paths['result'], stdin_path=None,
        env=selected['environment'])
    _require(hashlib.sha256(raw).hexdigest() == handle.get('request_sha256')
        and _same(decode_json(raw), expected), 'worker_request_conflict')
    _require(type(observation) is dict and observation.get('terminal') is True
        and observation.get('quiescent') is True and observation.get('state') == 'returned'
        and _same(observation.get('metadata'), value['metadata'])
        and _same(value['metadata'].get('policy'), selected['policy'])
        and type(value['metadata'].get('native_returncode')) is int
        and value['metadata'].get('native_returncode') == 0, 'worker_not_closed')
    _require(type(value['result_raw']) is str, 'worker_result_conflict')
    result = decode_json(value['result_raw'].encode('utf-8'))
    _closed(result, 'version value components')
    _require(result['version'] == RESULT_VERSION, 'worker_result_conflict')
    result['value'] = _public_from_worker(result['value'])
    if result_value is not None:
        _require(_same(result['value'], result_value), 'worker_result_conflict')
    _require(_same(result['value']['peak_window']['row_window'], request['row_window']), 'worker_result_conflict')
    return result


def _read_regular_json(path):
    with _regular(path) as stream:
        return decode_json(stream.read())


def _completed_worker(registry, work, request, directory):
    output = directory / 'worker-result.json'
    _require(Path(work.output_path) == output, 'worker_output_path_conflict')
    selected = _read_regular_json(directory / 'execution-selection.json')
    handle = native.NativeJobHandle(directory / 'native-handle.json')
    original = handle.read()
    try:
        observation = native.status(handle)
    except AcquisitionError as error:
        raise MolecularOperationUnpublished('macs2_peak_result_worker_attempt_unconfirmed') from error
    if not (observation['terminal'] and observation['quiescent']):
        raise MolecularOperationUnpublished('macs2_peak_result_worker_attempt_unconfirmed')
    failure = work.metadata.get('molecular_failure')
    if failure is not None:
        raise AcquisitionError(failure['code'], phase=failure.get('phase'), operational=deepcopy(work.metadata))
    _require(_same(work.metadata, observation['metadata']), 'worker_metadata_conflict')
    paths = original.get('paths') or {}
    _require(type(paths.get('request')) is str and Path(paths['request']).parent == directory, 'worker_handle_conflict')
    with _regular(paths['request']) as stream:
        raw = stream.read().decode('utf-8')
    with _regular(output) as stream:
        result_raw = stream.read().decode('utf-8')
    record = dict(request=deepcopy(request), selection=selected, handle=original, request_raw=raw,
        observation=observation, metadata=deepcopy(work.metadata), result_raw=result_raw)
    result = _worker_record(record, request=request)
    _require(selected['cwd'] == str(directory), 'worker_selection_conflict')
    return result, record


def _native_identity(value):
    _closed(value, 'plan seal roles')
    plan = validate_macs2_peak_run_plan(value['plan'])
    seal = validate_macs2_peak_seal(value['seal'], plan=plan)
    _require(type(value['roles']) is list and len(value['roles']) == len(plan['outputs']), 'capture_roles_conflict')
    for role, specification in zip(value['roles'], plan['outputs']):
        _closed(role, 'specification source_ref file availability qualification')
        _require(_same(role['specification'], specification)
            and role['availability'] in ('retained', 'unavailable', 'not_selected'), 'capture_roles_conflict')
        _require((role['source_ref'] is None or type(role['source_ref']) is str
                and _SOURCE.fullmatch(role['source_ref']) is not None)
            and (role['qualification'] is None or type(role['qualification']) is dict
                and set(role['qualification']) == {'code'} and type(role['qualification']['code']) is str)
            and (role['file'] is None or role['source_ref'] is not None)
            and (role['availability'] != 'retained' or role['file'] is not None), 'capture_roles_conflict')
        if role['file'] is not None:
            file = _identity(role['file'])
            _require(file['format'] == specification['format'], 'capture_roles_conflict')
    return dict(plan=plan, seal=seal, roles=deepcopy(value['roles']))


def _native_sources(registry, admitted, references):
    for role in admitted['roles']:
        if role['source_ref'] is not None:
            _require(role['source_ref'] in references, 'capture_source_conflict')
            source = registry.store.get(role['source_ref'])
            immutable_record(source)
            _require(source.get('record_type') == 'source' and role['file'] is not None
                and source.get('artifact_ref') == role['file']['artifact_ref'], 'capture_source_conflict')


def _native_result(result, admitted):
    request = admitted['plan']['requested_job']['native_macs2_peak']['request']
    value = result['value']
    _require(value['run_key'] == request['run_key'] and value['reference_id'] == request['reference']['reference_id']
        and value['native_outcome'] == admitted['seal']['outcome']
        and all(any(_same(problem, retained) for retained in value['failures'])
            for problem in admitted['seal']['failures']), 'worker_result_conflict')


def _role_paths(registry, admitted):
    value = deepcopy(admitted)
    for role in value['roles']:
        file = role['file']
        if file is not None:
            file = _identity(file)
            metadata = _metadata(registry.store, file['artifact_ref'])
            _require(metadata['sha256'] == file['sha256'] and metadata['size'] == file['size_bytes'], 'capture_identity_conflict')
            role['file'] = file
        role['path'] = None if file is None else _file_path(registry, file)
    return value


def _public_packet(registry, publication):
    packet = json.loads(_publication_bytes(registry.store, publication['source']['artifact_ref']))
    _require(_same(packet, _packet(publication['public'])), 'public_packet_conflict')
    publication['packet'] = packet
    return packet


def _historical_store_root(worker, invocation):
    directory = PurePosixPath(worker['selection']['cwd'])
    _require(directory.parts[-3:] == ('cache', 'molecular-measurements', digest(invocation['operation_key'])),
        'worker_selection_conflict')
    return directory.parents[2]


def _historical_path(root, file):
    return str(root / 'artifacts' / file['sha256'][:2] / file['sha256'])


def _control(registry, publication, seen):
    source, producer = publication['source'], publication['producer']
    _require(source['id'] not in seen, 'source_lineage_cycle')
    seen = {*seen, source['id']}
    control = json.loads(_publication_bytes(registry.store, source['request_ref']))
    _closed(control, _CONTROL_FIELDS)
    _require(control['version'] == CONTROL_VERSION and control['stored_version'] == STORED_VERSION
        and control['native_call_state'] == 'not_requested'
        and _same(control['arguments'], producer['arguments']) and _same(control['invocation'], producer['invocation'])
        and control['public_packet_ref'] == source['artifact_ref'], 'control_conflict')
    file = _file(registry, control['components_file'])
    _require(source['auxiliary_artifact_refs'] == [file['artifact_ref']], 'components_identity_conflict')
    arguments = _arguments(control['arguments'])
    current = _context(registry.store, control['invocation'])
    native_admission = _native_identity(control['native_admission'])
    _native_sources(registry, native_admission, control['capture_source_refs'])
    request = control['worker']['request']
    _closed(request, 'version mode row_window native saved')
    _require(request['version'] == REQUEST_VERSION and request['mode'] == arguments['mode']
        and _same(request['row_window'], arguments['row_window']), 'worker_request_conflict')
    result = _worker_record(control['worker'], request=request, result_value=publication['packet']['value'])
    _native_result(result, native_admission)
    historical_root = _historical_store_root(control['worker'], control['invocation'])
    if arguments['mode'] == 'parse':
        _require(control['original_source'] is control['source_admission'] is None
            and _same(control['admission_invocation'], control['invocation'])
            and control['capture_source_refs'] == arguments['capture_source_refs'], 'control_conflict')
        _require(request['mode'] == 'parse' and request['saved'] is None, 'worker_request_conflict')
        expected_native = deepcopy(native_admission)
        for role in expected_native['roles']:
            role['path'] = None if role['file'] is None else _historical_path(historical_root, role['file'])
        _require(_same(request['native'], expected_native), 'worker_request_conflict')
    else:
        parent_record = control['original_source']
        _closed(parent_record, 'source_ref record_sha256')
        _require(parent_record['source_ref'] == arguments['result_ref'], 'original_source_conflict')
        parent = _metadata_publication(registry, arguments['result_ref'])
        _require(parent_record['record_sha256'] == digest(parent['source']), 'original_source_conflict')
        _frozen_admission(registry, current, control['source_admission'], parent_record['source_ref'],
            control['invocation']['decision_index'])
        _public_packet(registry, parent)
        previous = _control(registry, parent, seen)
        _require(_same(previous['components_file'], file) and _same(previous['native_admission'], native_admission)
            and all(_same(control[key], previous[key]) for key in (
                'admission_invocation', 'capture_source_refs', 'capture_admissions')), 'saved_components_conflict')
        _require(request['mode'] == 'project_saved' and request['native'] is None
            and _same(request['saved']['file'], file)
            and request['saved']['path'] == _historical_path(historical_root, file)
            and request['saved']['native_outcome'] == parent['public']['native_outcome']
            and _same(request['saved']['failures'], parent['public']['failures']), 'worker_request_conflict')
    admission_context = _context(registry.store, control['admission_invocation'])
    _require(type(control['capture_admissions']) is list
        and len(control['capture_admissions']) == len(control['capture_source_refs']), 'capture_admission_conflict')
    for reference, admitted in zip(control['capture_source_refs'], control['capture_admissions']):
        _frozen_admission(registry, admission_context, admitted, reference, control['admission_invocation']['decision_index'])
    if arguments['mode'] == 'parse':
        declaration = result['components']
        _closed(declaration, 'relative_path format sha256 size_bytes')
        _require(declaration['relative_path'] == 'components.json' and declaration['format'] == file['format']
            and declaration['sha256'] == file['sha256'] and type(declaration['size_bytes']) is int
            and declaration['size_bytes'] == file['size_bytes'], 'components_identity_conflict')
    else:
        _require(result['components'] is None, 'components_identity_conflict')
    publication['components_file'] = file
    return control


def _read_publication(registry, context, reader, source_ref, *, require_components=False,
        recovery_operation_key=None, before_decision_index=None):
    _require(type(require_components) is bool, 'read_mode_invalid')
    EpisodeReturnRecords(registry.store, context.run_id, failure_prefix='macs2_peak_').authenticate(context)
    publication = _metadata_publication(registry, source_ref,
        recovery_context=context if recovery_operation_key is not None else None,
        recovery_operation_key=recovery_operation_key)
    invocation = publication['producer']['invocation']
    own = recovery_operation_key is not None and recovery_operation_key == invocation['operation_key'] and (
        context.run_id, context.episode_id) == (invocation['run_id'], invocation['episode_id'])
    cutoff = _current_cutoff(registry, context) if before_decision_index is None else before_decision_index
    _require(type(cutoff) is int and cutoff >= 0, 'receipt_cutoff_invalid')
    if not own:
        publication['received_input'] = _admit(registry, context, reader, source_ref, cutoff)
        _require(molecular_reference_restriction(registry.store, context, source_ref, 'source', providers=(TOOL,)) is True,
            'source_not_received')
    _public_packet(registry, publication)
    if require_components:
        publication['control'] = _control(registry, publication, set())
    return publication


def read_macs2_peak_publication(registry, context, reader, source_ref, *, require_components=False,
        recovery_operation_key=None):
    with registry.store.read_snapshot():
        return _read_publication(registry, context, reader, source_ref, require_components=require_components,
            recovery_operation_key=recovery_operation_key)


def read_retained_macs2_peak_publication(registry, context, reader, source_ref, *, recovery_operation_key=None):
    """Return the original literal recorded DTO, with no private component read."""
    return read_macs2_peak_publication(registry, context, reader, source_ref,
        recovery_operation_key=recovery_operation_key)['public']


def _prepare(registry, context, reader, arguments, invocation):
    cutoff = invocation['decision_index']
    if arguments['mode'] == 'parse':
        capture_admissions = [_admit(registry, context, reader, reference, cutoff)
            for reference in arguments['capture_source_refs']]
        capture_reader = registry.macs2_peak_capture_reader_for(context.run_id)
        native_admission = capture_reader(context, arguments['capture_source_refs'], before_decision_index=cutoff)
        _require(type(native_admission) is dict and native_admission.get('seal') is not None, 'producer_seal_not_received')
        native_admission = _native_identity(native_admission)
        _native_sources(registry, native_admission, arguments['capture_source_refs'])
        request = dict(version=REQUEST_VERSION, mode='parse', row_window=deepcopy(arguments['row_window']),
            native=_role_paths(registry, native_admission), saved=None)
        return dict(request=request, native_admission=native_admission, capture_admissions=capture_admissions,
            admission_invocation=invocation, capture_source_refs=arguments['capture_source_refs'],
            source_admission=None, original_source=None, components_file=None)
    publication = read_macs2_peak_publication(registry, context, reader, arguments['result_ref'])
    if (arguments['mode'] == 'read_stored' or _same(arguments['row_window'],
            publication['public']['peak_window']['row_window'])):
        return dict(public=publication['public'])
    publication = read_macs2_peak_publication(registry, context, reader, arguments['result_ref'], require_components=True)
    previous = publication['control']
    request = dict(version=REQUEST_VERSION, mode='project_saved', row_window=deepcopy(arguments['row_window']), native=None,
        saved=dict(file=publication['components_file'], path=_file_path(registry, publication['components_file']),
            native_outcome=publication['public']['native_outcome'], failures=deepcopy(publication['public']['failures'])))
    return dict(request=request, components_file=publication['components_file'],
        native_admission=previous['native_admission'], admission_invocation=previous['admission_invocation'],
        capture_source_refs=previous['capture_source_refs'], capture_admissions=previous['capture_admissions'],
        source_admission=publication['received_input'],
        original_source=dict(source_ref=publication['source']['id'], record_sha256=digest(publication['source'])))


def _publish(registry, arguments, invocation, prepared, result, worker, directory):
    _require(registry.store.db.in_transaction, 'publication_transaction_required')
    if arguments['mode'] == 'parse':
        declared = result['components']
        _closed(declared, 'relative_path format sha256 size_bytes')
        _require(declared['relative_path'] == 'components.json' and declared['format'] == COMPONENT_FORMAT,
            'components_declaration_conflict')
        file = capture_native_file(registry.store, directory=str(directory), relative_path='components.json',
            format=COMPONENT_FORMAT, media_type='application/json')
        _require(type(declared['size_bytes']) is int and file['size_bytes'] == declared['size_bytes']
            and file['sha256'] == declared['sha256'], 'components_identity_conflict')
    else:
        _require(result['components'] is None, 'components_declaration_conflict')
        file = _file(registry, prepared['components_file'])
    packet = dict(version=PACKET_VERSION, value=deepcopy(result['value']))
    packet_ref = registry.store.artifact(canonical(packet), 'application/json')
    control = dict(version=CONTROL_VERSION, stored_version=STORED_VERSION, arguments=deepcopy(arguments),
        invocation=deepcopy(invocation), **{key: deepcopy(prepared[key]) for key in (
            'admission_invocation', 'capture_source_refs', 'capture_admissions', 'native_admission',
            'source_admission', 'original_source')}, components_file=file, public_packet_ref=packet_ref,
        worker=worker, native_call_state='not_requested')
    control_ref = registry.store.artifact(canonical(control), 'application/json')
    parents = arguments['capture_source_refs'] if arguments['mode'] == 'parse' else [arguments['result_ref']]
    source = registry._put('source', dict(provider=TOOL, accession=None, uri=None, artifact_ref=packet_ref,
        text_ref=None, request_ref=control_ref, version=VERSION, retrieved_at=datetime.now(timezone.utc).isoformat(),
        parent_source_refs=deepcopy(parents), auxiliary_artifact_refs=[file['artifact_ref']]), origin='tool')
    return macs2_peak_return(result['value'], source_ref=source['id'])


def read_macs2_peak_action_result(registry, context, arguments, operation_key, *, reader):
    arguments = _arguments(arguments)
    active = registry._current_invocation.get()
    recovery = context if active is not None and active[0] is context and active[4] == operation_key else None
    details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
        recovery_context=recovery, recovery_operation_key=operation_key if recovery is not None else None)
    outcome = details['outcome']
    _require(outcome.get('status') in ('completed', 'partial') and type(outcome.get('result')) is dict,
        'action_result_unavailable')
    public = validate_macs2_peak_return(outcome['result'])
    _require(outcome.get('record_refs') == [public['source_ref']], 'action_source_conflict')
    redisplay = (arguments['mode'] == 'read_stored' or arguments['mode'] == 'project_saved'
        and public['source_ref'] == arguments['result_ref'])
    with registry.store.read_snapshot():
        publication = _read_publication(registry, context, reader, public['source_ref'],
            recovery_operation_key=operation_key if not redisplay else None,
            before_decision_index=details['invocation']['decision_index'])
    _require(_same(publication['public'], public), 'action_source_conflict')
    if redisplay:
        _require(public['source_ref'] == arguments['result_ref'], 'action_source_conflict')
        if arguments['mode'] == 'project_saved':
            _require(_same(public['peak_window']['row_window'], arguments['row_window']), 'action_source_conflict')
    else:
        _require(publication['producer']['invocation']['operation_key'] == operation_key, 'action_source_conflict')
    return public


def _outcome(arguments, operation_key, public):
    redisplay = arguments['mode'] != 'parse' and public['source_ref'] == arguments['result_ref']
    return dict(status='completed' if public['status'] == 'complete' else 'partial',
        operation_ref=identity('operation', dict(key=operation_key, name=TOOL, arguments=arguments)),
        record_refs=[public['source_ref']], changed_record_refs=[] if redisplay else [public['source_ref']],
        result=public, feedback=None if public['status'] == 'complete' else dict(category='representation',
            code='macs2_peak_selected_result_partial', source_ref=public['source_ref']))


def _failure(registry, arguments, operation_key, error):
    text = str(error)
    code = text if re.fullmatch(r'[a-z][a-z0-9_]*', text) else 'macs2_peak_result_invalid'
    diagnostic = registry.store.artifact(canonical(dict(version='macs2_peak_result_diagnostic_v1',
        exception_type=type(error).__module__ + '.' + type(error).__name__, exception_message=text,
        operational=getattr(error, 'operational', None))), 'application/json')
    return dict(status='unavailable' if code == 'macs2_peak_producer_seal_not_received'
            or isinstance(error, OSError) or code.endswith('_unavailable') else
        'invalid' if isinstance(error, (ContractError, ValueError, KeyError, TypeError)) else 'failed',
        operation_ref=identity('operation', dict(key=operation_key, name=TOOL, arguments=arguments)),
        record_refs=[], changed_record_refs=[], result=None,
        feedback=dict(category='representation' if code == 'macs2_peak_producer_seal_not_received' else
            'arguments_or_reference' if isinstance(error, (ContractError, ValueError, KeyError, TypeError)) else 'execution',
            code=code, diagnostic_ref=diagnostic))


def _recheck_inputs(registry, context, reader, arguments, prepared, cutoff):
    if arguments['mode'] == 'parse':
        for reference, admitted in zip(prepared['capture_source_refs'], prepared['capture_admissions']):
            _require(_same(_admit(registry, context, reader, reference, cutoff), admitted), 'capture_admission_conflict')
    else:
        _require(_same(_admit(registry, context, reader, arguments['result_ref'], cutoff), prepared['source_admission']),
            'source_admission_conflict')


async def execute_macs2_peak_result(registry, arguments, *, scope, operation_key, authority):
    context, reader = authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
    _require(type(authority) is tuple and len(authority) == 2 and authority[0] is context and authority[1] is reader,
        'invocation_authority_conflict')
    invocation = _invocation(context, operation_key)
    directory = _directory(registry.store.path / 'cache' / 'molecular-measurements' / digest(operation_key))
    async with _action_lock(directory):
        authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
        saved = registry.store.db.execute('SELECT 1 FROM tool_operations WHERE operation_key=?', (operation_key,)).fetchone()
        if saved is not None:
            details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
                recovery_context=context, recovery_operation_key=operation_key)
            outcome = details['outcome']
            if outcome.get('status') in ('completed', 'partial'):
                _require(_same(read_macs2_peak_action_result(registry, context, arguments, operation_key, reader=reader),
                    outcome['result']), 'cached_result_conflict')
            else:
                _require(outcome.get('status') in ('invalid', 'unavailable', 'failed')
                    and outcome.get('result') is None and outcome.get('record_refs') == [], 'cached_failure_conflict')
            return outcome
        try:
            arguments = _arguments(arguments)
            prepared = _prepare(registry, context, reader, arguments, invocation)
            if 'public' in prepared:
                public = prepared['public']
                authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
            else:
                intent = dict(version='ordinary_macs2_peak_intent_v1', invocation=invocation,
                    arguments=arguments, prepared=prepared)
                _immutable(directory / 'binding.json', intent)
                work = await registry._sequence_worker_async(_OPERATION, dict(request=prepared['request']),
                    directory=directory, owned_directory=directory)
                authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
                _recheck_inputs(registry, context, reader, arguments, prepared, invocation['decision_index'])
                result, worker = _completed_worker(registry, work, prepared['request'], directory)
                _native_result(result, prepared['native_admission'])
                with registry.store.transaction():
                    public = _publish(registry, arguments, invocation, prepared, result, worker, directory)
                    outcome = _outcome(arguments, operation_key, public)
                    registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
                return outcome
            with registry.store.transaction():
                outcome = _outcome(arguments, operation_key, public)
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome
        except MolecularOperationUnpublished:
            raise
        except Exception as error:
            with registry.store.transaction():
                outcome = _failure(registry, arguments, operation_key, error)
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome


__all__ = ['TOOL', 'macs2_peak_tool_contract', 'execute_macs2_peak_result', 'read_macs2_peak_publication',
    'read_retained_macs2_peak_publication', 'read_macs2_peak_action_result', 'macs2_peak_fact_sources']
