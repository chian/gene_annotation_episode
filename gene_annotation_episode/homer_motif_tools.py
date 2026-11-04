"""Ordinary HOMER actions and immutable Source-only retained views.

Native execution, numerical calculation and publication have distinct owners.
Reading an admitted result authenticates its original action and literal packet;
it neither repeats the calculation nor opens the original deployment or inputs.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import asyncio
import hashlib
import json
import re
import threading

from .communication import plain
from .domain import ContractError, identity, obj
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .flux_balance_tools import _action_lock
from .homer_motif_contracts import OPERATION, ROLES, validate_homer_selector
from .homer_motif_result_contracts import (SOURCE_VERSION, CAPTURE_VERSION, PACKET_VERSION,
    validate_homer_motif_return, validate_homer_motif_value, homer_motif_return, homer_motif_fact_sources)
from .local_jobs import LocalJobPolicy
from .molecular_measurement_tools import (MolecularOperationUnpublished,
    authenticate_molecular_invocation, _recorded_molecular_action_details,
    _recorded_molecular_producer_details, _publication_bytes)
from .molecular_sequence_input_contracts import (validate_molecular_sequence_received_file,
    input_record_digest)
from .native_atac_differential_driver import _directory, _immutable, _regular, decode_json
from .native_file_capture import _identity, _metadata, capture_native_file
from .reference_edit_outcome_tools import (_invocation, _context, _admit,
    _frozen_admission, _current_cutoff)
from .alignment_site_native import immutable_record
from . import native_lifecycle

TOOL = OPERATION
CONFIGURATION_VERSION = 'ordinary_homer_configuration_v1'
CONTROL_VERSION = 'ordinary_homer_motif_publication_v1'
CAPTURE_CONTROL_VERSION = 'ordinary_homer_motif_native_capture_control_v1'
WORKER_OPERATION = 'homer_motif_result'
WORKER_REQUEST_VERSION = 'homer_motif_worker_request_v1'
WORKER_RESULT_VERSION = 'homer_motif_worker_result_v1'
_SOURCE = re.compile(r'^source_[0-9a-f]{24,64}$')
_ARTIFACT = re.compile(r'^artifact_[0-9a-f]{64}$')
_INPUTS = (('target_bed', 'bed'), ('reference_fasta', 'fasta'), ('background_bed', 'bed'))
DESCRIPTION = 'Find DNA motifs enriched in selected genomic regions relative to a selected background using the configured HOMER genome-region wrapper.'
INSTRUCTIONS = ('Select the resource, received target BED, reference FASTA or advertised installed genome, and supplied or native-generated background. '
    'Specify window size, motif lengths, motif count, threads, strand, statistical and normalization settings. '
    'Return controlled native motif records and qualified numeric values. Preserve ordered PWMs, population identities, counts, weights and rounded percentages. '
    'Keep detection thresholds separate from enrichment p/log-p/FDR. Unknown totals remain unknown. '
    'Motif labels and enrichment do not establish measured TF binding or regulation.')


def _require(condition, code):
    if not condition:
        raise ContractError('homer_motif_' + code)


class _KnownUnavailable(ContractError):
    """A closed attempt lacks authentic controls; it is not pending work."""


class _KnownFailure(ContractError):
    """A confirmed terminal calculation failed; its original work is retained."""


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()), 'fields_invalid')


def _same(a, b):
    return canonical(a) == canonical(b)


def _copy(value):
    return json.loads(canonical(value))


def _native():
    from . import native_homer_execution
    return native_homer_execution


def normalize_homer_configuration(resources, environments, *, policy):
    """Compile an explicitly selected resource; inspect no deployment bytes."""
    _require(type(resources) is dict and isinstance(environments, (list, tuple)), 'configuration_invalid')
    checked_policy = LocalJobPolicy(**policy).to_dict()
    _require(_same(policy, checked_policy), 'policy_invalid')
    rows = []
    for entry in environments:
        _closed(entry, 'operation resource_id binding_ordinal_0based environment')
        _require(entry['operation'] == TOOL and not rows, 'ambiguous_resource_selection')
        name, ordinal = entry['resource_id'], entry['binding_ordinal_0based']
        _require(type(name) is str and bool(name) and type(ordinal) is int and ordinal >= 0,
            'binding_selection_invalid')
        resource = resources.get(name)
        _require(type(resource) is dict and resource.get('kind') == 'local'
            and _same(resource.get('policy'), policy), 'resource_allocation_conflict')
        bindings = _native().validate_homer_bindings(resource.get('native_homer_motif'))
        _require(ordinal < len(bindings), 'binding_selection_invalid')
        _require(_same(policy, _native().POLICY), 'native_resource_policy_unsupported')
        workspace = resource.get('workspace')
        _require(type(workspace) is str and Path(workspace).is_absolute()
            and str(Path(workspace)) == workspace and '..' not in Path(workspace).parts,
            'workspace_invalid')
        environment = entry['environment']
        _require(_same(environment, dict(version='homer_execution_selection_v1',
            environment_realization='operation_scoped_tmp_and_cache_v1')), 'environment_invalid')
        row = dict(resource_id=name, binding_ordinal_0based=ordinal, workspace=workspace,
            binding=bindings[ordinal], environment=deepcopy(environment))
        _native()._selected(row)
        rows.append(row)
    return dict(version=CONFIGURATION_VERSION, policy=checked_policy, bindings=rows, saved_modes=False)


def _configuration(value):
    _closed(value, 'version policy bindings saved_modes')
    _require(value['version'] == CONFIGURATION_VERSION and type(value['saved_modes']) is bool
        and type(value['bindings']) is list and len(value['bindings']) <= 1, 'configuration_invalid')
    _require(_same(LocalJobPolicy(**value['policy']).to_dict(), value['policy']), 'policy_invalid')
    for row in value['bindings']:
        _native()._selected(row)
        _require(_same(value['policy'], _native().POLICY), 'native_resource_policy_unsupported')
    return _copy(value)


def _initial_selection(value):
    _closed(value, 'series offset limit')
    _require(type(value['series']) is list and type(value['offset']) is int and value['offset'] >= 0
        and type(value['limit']) is int and value['limit'] >= 0, 'selection_invalid')
    seen = set()
    for item in value['series']:
        _require(type(item) is dict, 'selection_invalid')
        if item.get('role') == 'denovo_pwm':
            _closed(item, 'role motif_length')
            _require(type(item['motif_length']) is int and item['motif_length'] >= 1, 'selection_invalid')
        else:
            _closed(item, 'role')
            _require(item['role'] in ('known_results', 'denovo_combined_pwm', 'denovo_nonredundant_pwm'),
                'selection_invalid')
        key = canonical(item)
        _require(key not in seen, 'selection_invalid')
        seen.add(key)
    return _copy(value)


def _arguments(value):
    value = _copy(value)
    _require(type(value) is dict, 'arguments_invalid')
    mode = value.get('mode')
    if mode == 'run_native':
        _closed(value, 'mode inputs parameters selection')
        _require(type(value['inputs']) is list and len(value['inputs']) == 3, 'inputs_invalid')
        for item, (role, _) in zip(value['inputs'], _INPUTS):
            _closed(item, 'role namespace reference')
            pattern = _ARTIFACT if item['namespace'] == 'artifact' else _SOURCE if item['namespace'] == 'source' else None
            _require(item['role'] == role and pattern is not None and type(item['reference']) is str
                and pattern.fullmatch(item['reference']) is not None, 'inputs_invalid')
        _native().validate_homer_arguments(value['parameters'])
        _initial_selection(value['selection'])
        _require(all(item.get('role') != 'denovo_pwm'
            or item['motif_length'] in value['parameters']['motif_lengths'] for item in value['selection']['series']),
            'unrequested_motif_length')
    else:
        _require(mode in ('read_stored', 'calculate_saved'), 'mode_invalid')
        _closed(value, 'mode result_ref' if mode == 'read_stored' else 'mode result_ref selector')
        _require(type(value['result_ref']) is str and _SOURCE.fullmatch(value['result_ref']), 'source_required')
        if mode == 'calculate_saved':
            validate_homer_selector(value['selector'])
    return value


def homer_tool_contract(configuration):
    configuration = _configuration(configuration)
    if not configuration['bindings'] and not configuration['saved_modes']:
        return None
    source = dict(type='string', pattern=_SOURCE.pattern)
    variants = []
    if configuration['bindings']:
        native = _native()
        parameters = native.homer_execution_schema('Arguments', binding=configuration['bindings'][0]['binding'])
        choices = [obj(dict(role=dict(const=role))) for role in
            ('known_results', 'denovo_combined_pwm', 'denovo_nonredundant_pwm')]
        choices.append(obj(dict(role=dict(const='denovo_pwm'), motif_length=dict(type='integer', minimum=1))))
        input_schemas = [obj(dict(role=dict(const=role), namespace=dict(enum=['artifact', 'source']),
            reference=dict(type='string', pattern=r'^(artifact_[0-9a-f]{64}|source_[0-9a-f]{24,64})$')))
            for role, _ in _INPUTS]
        variants.append(obj(dict(mode=dict(const='run_native'), inputs=dict(type='array',
            prefixItems=input_schemas, minItems=3, maxItems=3), parameters=parameters,
            selection=obj(dict(series=dict(type='array', items=dict(anyOf=choices), uniqueItems=True),
                offset=dict(type='integer', minimum=0), limit=dict(type='integer', minimum=0))))))
    if configuration['saved_modes']:
        from .homer_motif_contracts import homer_record_schema
        selector_schema = deepcopy(homer_record_schema('Selector')['$defs']['Selector'])
        variants.extend([obj(dict(mode=dict(const='read_stored'), result_ref=source)),
            obj(dict(mode=dict(const='calculate_saved'), result_ref=source, selector=selector_schema))])
    public_configuration = dict(job_limits=deepcopy(configuration['policy']), saved_modes=configuration['saved_modes'],
        bindings=[dict(resource_id=row['resource_id'], binding_ordinal_0based=row['binding_ordinal_0based'],
            variant=row['binding']['variant']) for row in configuration['bindings']])
    return dict(resources='local', invocation_route=dict(kind='direct'), description=DESCRIPTION,
        input_schema=dict(anyOf=variants,
            description='The configured native binding accepts supplied reference FASTA and explicit background BED only.'),
        instructions=INSTRUCTIONS,
        configuration=dict(**public_configuration,
            supported_native_inputs='supplied reference FASTA and explicit background BED only'))


def _file(registry, file):
    file = _identity(file)
    metadata = _metadata(registry.store, file['artifact_ref'])
    _require(file['artifact_ref'] == 'artifact_' + file['sha256']
        and metadata['sha256'] == file['sha256'] and metadata['size'] == file['size_bytes'], 'file_identity_conflict')
    return file


def _path(registry, file, *, store_root=None):
    root = registry.store.path if store_root is None else store_root
    return str(root / 'artifacts' / file['sha256'][:2] / file['sha256'])


def _historical_store_root(worker, invocation):
    """Validate saved paths against their original immutable worker custody."""
    supplied = worker['selection']['cwd']
    _require(type(supplied) is str, 'worker_selection_conflict')
    directory = PurePosixPath(supplied)
    _require(directory.is_absolute() and str(directory) == supplied and '..' not in directory.parts
        and directory.parts[-4:] == ('cache', 'molecular-measurements',
            digest(invocation['operation_key']), 'calculation'), 'worker_selection_conflict')
    return directory.parents[3]


def _packet(public):
    return dict(version=PACKET_VERSION, value={k: deepcopy(v) for k, v in public.items()
        if k not in ('version', 'source_ref')})


def _metadata_publication(registry, source_ref, *, recovery_context=None, recovery_operation_key=None):
    source = registry.store.get(source_ref)
    immutable_record(source)
    _require(source.get('record_type') == 'source' and source.get('origin') == 'tool'
        and source.get('provider') == TOOL and source.get('version') == SOURCE_VERSION
        and 'operand_refs' not in source, 'producer_required')
    producer = _recorded_molecular_producer_details(registry, source_ref, TOOL,
        recovery_context=recovery_context, recovery_operation_key=recovery_operation_key)
    public = validate_homer_motif_return(producer['outcome']['result'])
    _require(public['source_ref'] == source_ref and producer['outcome'].get('record_refs') == [source_ref],
        'publication_conflict')
    arguments = _arguments(producer['arguments'])
    if arguments['mode'] == 'run_native':
        parents = source.get('parent_source_refs')
        _require(type(parents) is list and len(parents) == 1, 'native_capture_conflict')
        capture = registry.store.get(parents[0])
        immutable_record(capture)
        _require(capture.get('provider') == TOOL and capture.get('version') == CAPTURE_VERSION
            and capture.get('origin') == 'tool' and capture.get('accession') == producer['operation_ref'],
            'native_capture_conflict')
    else:
        _require(source.get('parent_source_refs') == [arguments['result_ref']], 'original_source_conflict')
    return dict(source=source, producer=producer, public=public, control=None, received_input=None,
        source_decision_admission=None)


def _decision_admission(registry, context, reference, cutoff):
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix='homer_motif_')
    records.authenticate(context)
    return records.source_admission_before(context, reference, cutoff)


def _read_homer_publication(registry, context, reader, source_ref, *, recovery_operation_key=None,
        require_sheet=False, before_decision_index=None):
    EpisodeReturnRecords(registry.store, context.run_id, failure_prefix='homer_motif_').authenticate(context)
    publication = _metadata_publication(registry, source_ref,
        recovery_context=context if recovery_operation_key is not None else None,
        recovery_operation_key=recovery_operation_key)
    invocation = publication['producer']['invocation']
    own = recovery_operation_key is not None and invocation['operation_key'] == recovery_operation_key and (
        invocation['run_id'], invocation['episode_id']) == (context.run_id, context.episode_id)
    cutoff = _current_cutoff(registry, context) if before_decision_index is None else before_decision_index
    if not own:
        publication['received_input'] = _admit(registry.store, reader, context, source_ref, 'source', cutoff)
        active = registry._current_invocation.get()
        if before_decision_index is not None or (active is not None and active[0] is context):
            publication['source_decision_admission'] = _decision_admission(registry, context, source_ref, cutoff)
    packet = decode_json(_publication_bytes(registry.store, publication['source']['artifact_ref']))
    _require(_same(packet, _packet(publication['public'])), 'public_packet_conflict')
    if require_sheet:
        publication['control'] = _control(registry, publication, set())
    return publication


def read_retained_homer_publication(registry, context, reader, source_ref, *, recovery_operation_key=None):
    with registry.store.read_snapshot():
        return _read_homer_publication(registry, context, reader, source_ref,
            recovery_operation_key=recovery_operation_key)['public']


def _control(registry, publication, seen):
    source, producer = publication['source'], publication['producer']
    _require(source['id'] not in seen, 'source_lineage_cycle')
    seen = {*seen, source['id']}
    value = decode_json(_publication_bytes(registry.store, source['request_ref']))
    _closed(value, 'version arguments invocation capture_source sheet_file components_file source_admission source_decision_admission original_source worker public_packet_ref native_call_state input_artifact_refs')
    _require(value['version'] == CONTROL_VERSION and _same(value['arguments'], producer['arguments'])
        and _same(value['invocation'], producer['invocation'])
        and value['public_packet_ref'] == source['artifact_ref'], 'control_conflict')
    sheet, components = _file(registry, value['sheet_file']), _file(registry, value['components_file'])
    _require(sheet['format'] == 'homer_motif_sheet_v1' and components['format'] == 'homer_motif_components_v1',
        'component_format_conflict')
    capture = registry.store.get(value['capture_source']['source_ref'])
    immutable_record(capture)
    _require(digest(capture) == value['capture_source']['record_sha256']
        and capture.get('provider') == TOOL and capture.get('version') == CAPTURE_VERSION
        and capture.get('origin') == 'tool', 'native_capture_conflict')
    arguments = _arguments(value['arguments'])
    if arguments['mode'] == 'run_native':
        native_control = decode_json(_publication_bytes(registry.store, capture['request_ref']))
        _closed(native_control, 'version invocation arguments input_artifact_refs input_admissions input_decision_admissions native_execution manifest_ref')
        _require(native_control['version'] == CAPTURE_CONTROL_VERSION
            and _same(native_control['invocation'], value['invocation'])
            and _same(native_control['arguments'], arguments)
            and native_control['manifest_ref'] == capture['artifact_ref']
            and native_control['input_artifact_refs'] == value['input_artifact_refs'], 'native_capture_conflict')
        historical = _native().validate_homer_execution(native_control['native_execution'])
        _require(historical['plan']['identity']['operation_key'] == value['invocation']['operation_key']
            and _same(historical['plan']['request']['arguments'], arguments['parameters'])
            and list(dict.fromkeys(row['file']['artifact_ref'] for row in
                historical['plan']['request']['frozen_inputs']['inputs'])) == value['input_artifact_refs'],
            'native_capture_conflict')
        original_context = _context(registry.store, value['invocation'])
        _check_frozen_inputs(registry, original_context, arguments, dict(
            frozen_inputs=historical['plan']['request']['frozen_inputs'],
            input_admissions=native_control['input_admissions'],
            input_decision_admissions=native_control['input_decision_admissions']),
            value['invocation']['decision_index'],
            store_root=_historical_store_root(value['worker'], value['invocation']))
        outcome = historical['execution']['wrapper_outcome']
        call_state = 'returned' if outcome in ('succeeded', 'failed') else 'not_started' if outcome == 'not_run' else 'unconfirmed'
        _require(value['original_source'] is value['source_admission'] is value['source_decision_admission'] is None
            and source.get('parent_source_refs') == [capture['id']]
            and capture.get('accession') == producer['operation_ref']
            and value['native_call_state'] in ('returned', 'not_started', 'unconfirmed')
            and value['native_call_state'] == call_state, 'native_capture_conflict')
    else:
        _require(arguments['mode'] == 'calculate_saved' and value['native_call_state'] == 'not_requested', 'control_conflict')
        original = value['original_source']
        _closed(original, 'source_ref record_sha256')
        _require(original['source_ref'] == arguments['result_ref']
            and source.get('parent_source_refs') == [original['source_ref']], 'original_source_conflict')
        previous = _metadata_publication(registry, original['source_ref'])
        _require(digest(previous['source']) == original['record_sha256'], 'original_source_conflict')
        context = _context(registry.store, value['invocation'])
        _frozen_admission(registry.store, context, value['source_admission'], original['source_ref'],
            'source', value['invocation']['decision_index'])
        _require(_same(_decision_admission(registry, context, original['source_ref'],
            value['invocation']['decision_index']), value['source_decision_admission']), 'source_decision_admission_conflict')
        prior = _control(registry, previous, seen)
        _require(_same(sheet, prior['sheet_file']) and _same(value['capture_source'], prior['capture_source'])
            and value['input_artifact_refs'] == prior['input_artifact_refs'], 'saved_sheet_conflict')
    expected = list(dict.fromkeys([*capture.get('auxiliary_artifact_refs', []), sheet['artifact_ref'], components['artifact_ref']]))
    _require(source.get('auxiliary_artifact_refs') == [r for r in expected if r not in value['input_artifact_refs']],
        'private_files_conflict')
    _require(_same(value['worker']['request']['selection'], arguments['selection'] if arguments['mode'] == 'run_native'
        else arguments['selector']), 'worker_selection_conflict')
    return value


def homer_capture_reference_restriction(store, context, reference, namespace):
    """Classify only a real ordinary producer's private capture; grant nothing."""
    from .molecular_reference_privacy import molecular_capture_reference_restriction
    return molecular_capture_reference_restriction(
        store, context, reference, namespace, provider=TOOL)


def _file_admission(registry, context, value, item, cutoff):
    value = validate_molecular_sequence_received_file(value)
    _require(value['failure'] is None and value['selection'] == dict(reference=item['reference'], namespace=item['namespace']),
        'input_not_received')
    received = value['input']
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix='homer_motif_')
    records.authenticate(context)
    manifest = EpisodeReceipts.read_manifest(registry.store.db, context.run_id, context.episode_id)
    _require(received['receiver'] == dict(run_id=context.run_id, episode_id=context.episode_id,
        request_sha256=input_record_digest(plain(context.request)), assignment_sha256=input_record_digest(plain(context.assignment)))
        and _same(received['scope'], registry.store.validate_scope(plain(context.scope)))
        and _same(received['inheritance_manifest'], manifest)
        and _same(received['witness']['record'], registry.store.get(item['reference']))
        and records._received_before(context.episode_id, item['reference'], cutoff)
        and records._received_before(context.episode_id, received['file']['artifact_ref'], cutoff), 'input_admission_conflict')
    _file(registry, received['file'])
    return value


def _input_decision_admission(registry, context, item, cutoff):
    """Select metadata through the existing owner, before streaming any bytes."""
    record = registry.store.get(item['reference'])
    _require(record.get('record_type') == item['namespace'], 'input_namespace_conflict')
    if item['namespace'] == 'source':
        from .materials import source_window_selection
        immutable_record(record)
        artifact_ref, representation, _ = source_window_selection(record, 'original')
        _require(representation == 'original', 'input_representation_conflict')
    else:
        artifact_ref = item['reference']
    _metadata(registry.store, artifact_ref)
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix='homer_motif_')
    records.authenticate(context)
    try:
        return records.file_admission_before(context, item['reference'], item['namespace'], artifact_ref, cutoff)
    except ValueError as error:
        if str(error) == 'homer_motif_file_admission_projection_unavailable':
            raise _KnownUnavailable(str(error)) from error
        raise


def _fresh_inputs(registry, context, reader, arguments, cutoff):
    inputs, admissions, decision_admissions = [], [], []
    for item, (role, fmt) in zip(arguments['inputs'], _INPUTS):
        decision = _input_decision_admission(registry, context, item, cutoff)
        received, path = reader(context, item['reference'], item['namespace'], file_format=fmt)
        received = _file_admission(registry, context, received, item, cutoff)
        _require(_same(_input_decision_admission(registry, context, item, cutoff), decision),
            'input_decision_admission_conflict')
        _require(received['input']['byte_verification'] == 'verified' and path is not None, 'input_bytes_unavailable')
        file = received['input']['file']
        _require(str(path) == _path(registry, file) and file['format'] == fmt, 'input_path_conflict')
        inputs.append(dict(role=role, selection=dict(namespace=item['namespace'], reference=item['reference']),
            file=file, path=str(path)))
        admissions.append(received)
        decision_admissions.append(decision)
    return dict(version='ordinary_homer_frozen_inputs_v1', inputs=inputs), admissions, decision_admissions


def _check_frozen_inputs(registry, context, arguments, binding, cutoff, *, store_root=None):
    frozen = _native().validate_homer_frozen_inputs(binding['frozen_inputs'])
    _require(type(binding['input_admissions']) is list and len(binding['input_admissions']) == 3
        and type(binding['input_decision_admissions']) is list and len(binding['input_decision_admissions']) == 3,
        'input_admission_conflict')
    for item, admission, decision, selected, (role, fmt) in zip(arguments['inputs'], binding['input_admissions'],
            binding['input_decision_admissions'], frozen['inputs'], _INPUTS):
        admitted = _file_admission(registry, context, admission, item, cutoff)
        _require(selected['role'] == role and selected['file']['format'] == fmt
            and selected['selection'] == dict(namespace=item['namespace'], reference=item['reference'])
            and _same(selected['file'], admitted['input']['file'])
            and selected['path'] == _path(registry, selected['file'], store_root=store_root)
            and _same(_input_decision_admission(registry, context, item, cutoff), decision),
            'input_decision_admission_conflict')


def _run_selection(registry, owner, selected, policy):
    resource = owner.resources.get(selected['resource_id'])
    _require(type(resource) is dict and resource.get('kind') == 'local'
        and resource.get('workspace') == selected['workspace'] and _same(resource.get('policy'), policy)
        and _same(registry.local_job_policy.to_dict(), policy), 'run_resource_selection_conflict')
    bindings = resource.get('native_homer_motif')
    ordinal = selected['binding_ordinal_0based']
    _require(type(bindings) is list and ordinal < len(bindings) and _same(bindings[ordinal], selected['binding']),
        'run_resource_selection_conflict')


async def _observe_native(prepared):
    stop = threading.Event()
    task = asyncio.create_task(asyncio.to_thread(_native().run_ordinary_homer_attempt, prepared, cancel_event=stop))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        stop.set()
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if task.done() and not task.cancelled():
            task.exception()
        raise


def _native_capture(registry, invocation, arguments, binding, execution, directory):
    execution = _native().validate_homer_execution(execution)
    _require(execution['terminal'] is True and execution['quiescent'] is True, 'native_not_closed')
    actual = _native().read_homer_attempt_metadata(execution['plan'])
    for key in ('completion', 'completion_file', 'output_manifest', 'output_manifest_file', 'metadata_failures'):
        _require(_same(execution[key], actual[key]), 'native_metadata_conflict')
    manifest = execution['output_manifest']
    completion = execution['completion']
    if manifest is None and completion is None:
        raise _KnownUnavailable('homer_motif_native_metadata_unavailable')
    plan = execution['plan']
    selected = binding['selected']
    _require(plan['identity']['operation_key'] == invocation['operation_key']
        and plan['identity']['run_id'] == invocation['run_id']
        and plan['identity']['episode_id'] == invocation['episode_id']
        and _same(plan['request']['arguments'], arguments['parameters'])
        and plan['identity']['request_sha256'] == invocation['request_sha256']
        and plan['identity']['resource_id'] == selected['resource_id']
        and plan['identity']['binding_ordinal_0based'] == selected['binding_ordinal_0based']
        and _same(plan['software'], selected['binding']['software'])
        and _same(plan['policy'], binding['policy'])
        and _same(plan['request']['deployment'], selected['binding']['deployment'])
        and _same(plan['request']['frozen_inputs'], binding['frozen_inputs']), 'native_action_conflict')
    for key in ('plan_file', 'binding_file', 'request_file'):
        pin = execution[key]
        with _regular(pin['path']) as stream:
            raw = stream.read()
        _require(len(raw) == pin['size_bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256'],
            'native_control_identity_conflict')
        if key == 'plan_file':
            _require(_same(decode_json(raw), plan), 'native_plan_conflict')
    root = plan['attempt_directory']
    outputs, auxiliary = [], []
    if manifest is not None:
        rows = [(row, True) for row in manifest['files']] + [(row, False) for row in manifest['other_files']]
    else:
        # The completion independently seals these two logs. Without the
        # output manifest, no other native file has a provable original pin.
        rows = []
        for key in ('stdout', 'stderr'):
            pin = completion[key]
            if pin is not None:
                relative = str(Path(pin['path']).relative_to(root))
                rows.append((dict(role='native_log', native_relative_path=relative,
                    format='homer_native_log_v1', observed_state='present', sha256=pin['sha256'],
                    size_bytes=pin['size_bytes'], failure=None), True))
    for row, scientific in rows:
        file, qualification = None, None
        if row.get('observed_state', 'present') == 'present':
            try:
                file = capture_native_file(registry.store, directory=root, relative_path=row['native_relative_path'],
                    format=row.get('format', 'homer_native_file_v1'), media_type='application/octet-stream')
            except (ValueError, OSError):
                qualification = 'native_output_unavailable'
            else:
                auxiliary.append(file['artifact_ref'])
                if any(file[k] != row[k] for k in ('sha256', 'size_bytes')):
                    qualification = 'native_output_identity_conflict'
        elif row['observed_state'] == 'unavailable':
            qualification = 'native_output_unavailable'
        outputs.append(dict(scientific=scientific, declared=deepcopy(row), file=file, qualification=qualification))
    excluded = list(dict.fromkeys(i['file']['artifact_ref'] for i in binding['frozen_inputs']['inputs']))
    stamp = directory / 'publication-time.json'
    if not stamp.exists():
        _immutable(stamp, dict(retrieved_at=datetime.now(timezone.utc).isoformat()))
    retrieved = decode_json(stamp.read_bytes())['retrieved_at']
    capture_manifest = dict(version=CAPTURE_VERSION, invocation=invocation, outputs=outputs, input_artifact_refs=excluded)
    manifest_ref = registry.store.artifact(canonical(capture_manifest), 'application/json')
    control = dict(version=CAPTURE_CONTROL_VERSION, invocation=invocation, arguments=arguments,
        input_artifact_refs=excluded, input_admissions=binding['input_admissions'],
        input_decision_admissions=binding['input_decision_admissions'], native_execution=execution, manifest_ref=manifest_ref)
    control_ref = registry.store.artifact(canonical(control), 'application/json')
    operation_ref = identity('operation', dict(key=invocation['operation_key'], name=TOOL, arguments=arguments))
    parents = list(dict.fromkeys(i['reference'] for i in arguments['inputs'] if i['namespace'] == 'source'))
    source = registry._put('source', dict(provider=TOOL, accession=operation_ref, uri=None, artifact_ref=manifest_ref,
        request_ref=control_ref, text_ref=None, version=CAPTURE_VERSION, retrieved_at=retrieved,
        parent_source_refs=parents, auxiliary_artifact_refs=[r for r in dict.fromkeys(auxiliary) if r not in excluded]), origin='tool')
    files = []
    for row in outputs:
        if not row['scientific']:
            continue
        declaration, file, qualification = row['declared'], row['file'], row['qualification']
        available = file is not None and qualification is None
        path = declaration['native_relative_path']
        lengths = arguments['parameters']['motif_lengths']
        motif_length = next((length for length in lengths if path == 'native/homerMotifs.motifs' + str(length)), None)
        files.append(dict(role=declaration['role'], native_relative_path=path,
            file=file if available else None, path=_path(registry, file) if available else None,
            source_ref=source['id'], capture=dict(state='complete' if available else 'missing',
                byte_start_0based=0, byte_end_0based_exclusive=file['size_bytes'] if available else 0,
                original_size_bytes=file['size_bytes'] if available else None),
            motif_length=motif_length, qualification=qualification))
    return source, files, excluded, actual['execution']


def _measurement_invocation(execution):
    """Name actual selected custody; a binding digest is not a native version."""
    plan = execution['plan']
    parameters = plan['request']['arguments']
    return dict(invocation_id=identity('homer_native_invocation', plan['identity']), operation=TOOL,
        selected_window_bp=parameters['window_bp'], selected_motif_lengths=deepcopy(parameters['motif_lengths']),
        native_parameters=deepcopy(parameters), software=[dict(name='selected HOMER binding record',
            version=None, sha256=execution['binding_file']['sha256'])])


def _worker_completion(work, request, directory):
    output = directory / 'worker-result.json'
    _require(Path(work.output_path) == output, 'worker_output_conflict')
    handle = native_lifecycle.NativeJobHandle(directory / 'native-handle.json')
    observation = native_lifecycle.status(handle)
    if not (observation['terminal'] and observation['quiescent']):
        raise MolecularOperationUnpublished('homer_motif_worker_attempt_unconfirmed')
    if work.metadata.get('molecular_failure') or observation['metadata'].get('native_returncode') != 0:
        raise _KnownFailure('homer_motif_result_calculation_failed')
    _require(_same(work.metadata, observation['metadata']), 'worker_metadata_conflict')
    selection = decode_json((directory / 'execution-selection.json').read_bytes())
    _closed(selection, 'version command cwd environment policy request python implementation_files')
    original = handle.read()
    _require(selection['version'] == 'ordinary_molecular_execution_v1'
        and _same(selection['request'], dict(operation=WORKER_OPERATION, arguments=dict(request=request)))
        and selection['cwd'] == str(directory)
        and selection['command'] == [selection['python']['path'], '-m', 'gene_annotation_episode.native_homer_worker',
            str(directory / 'worker-request.json'), str(output)]
        and original['command'] == selection['command'] and original['cwd'] == str(directory)
        and original['stdout'] == str(directory / 'stdout') and original['stderr'] == str(directory / 'stderr')
        and _same(original['metadata']['policy'], selection['policy'])
        and _same(observation['metadata']['policy'], selection['policy']), 'worker_selection_conflict')
    paths = original['paths']
    _require(all(type(path) is str and Path(path).parent == directory for path in paths.values()),
        'worker_handle_conflict')
    with _regular(paths['request']) as stream:
        raw_request = stream.read()
    _require(hashlib.sha256(raw_request).hexdigest() == original['request_sha256']
        and _same(decode_json(raw_request), dict(command=selection['command'], cwd=str(directory),
            file_bytes=selection['policy']['scratch_bytes'], ready_path=paths['ready'],
            release_path=paths['release'], result_path=paths['result'], stdin_path=None,
            env=selection['environment'])), 'worker_handle_conflict')
    with _regular(output) as stream:
        raw = stream.read()
    result = decode_json(raw)
    _closed(result, 'version value selector sheet components')
    _require(result['version'] == WORKER_RESULT_VERSION, 'worker_result_invalid')
    result['value'] = validate_homer_motif_value(result['value'])
    result['selector'] = validate_homer_selector(result['selector'])
    _require(_same(result['value']['selector'], result['selector']), 'worker_result_conflict')
    if request['mode'] == 'calculate_saved':
        _require(result['sheet'] is None and _same(result['selector'], request['selection']), 'worker_result_conflict')
    record = dict(request=request, selection=selection, handle=original, observation=observation,
        native_request=decode_json(raw_request), result_sha256=digest(result))
    return result, record


def _capture_component(registry, directory, declaration, name, format):
    _closed(declaration, 'relative_path format sha256 size_bytes')
    _require(declaration['relative_path'] == name and declaration['format'] == format, 'component_declaration_conflict')
    file = capture_native_file(registry.store, directory=str(directory), relative_path=name,
        format=format, media_type='application/json')
    _require(type(declaration['size_bytes']) is int and all(file[k] == declaration[k] for k in ('sha256', 'size_bytes')),
        'component_identity_conflict')
    return file


def _publish(registry, arguments, invocation, prepared, result, worker, directory):
    _require(registry.store.db.in_transaction, 'publication_transaction_required')
    sheet = (_capture_component(registry, directory, result['sheet'], 'sheet.json', 'homer_motif_sheet_v1')
        if arguments['mode'] == 'run_native' else _file(registry, prepared['sheet_file']))
    components = _capture_component(registry, directory, result['components'], 'components.json', 'homer_motif_components_v1')
    capture = prepared['capture_source']
    packet_ref = registry.store.artifact(canonical(dict(version=PACKET_VERSION, value=result['value'])), 'application/json')
    control = dict(version=CONTROL_VERSION, arguments=arguments, invocation=invocation,
        capture_source=dict(source_ref=capture['id'], record_sha256=digest(capture)),
        sheet_file=sheet, components_file=components, source_admission=prepared['source_admission'],
        source_decision_admission=prepared['source_decision_admission'],
        original_source=prepared['original_source'], worker=worker, public_packet_ref=packet_ref,
        native_call_state=prepared['native_call_state'] if arguments['mode'] == 'run_native' else 'not_requested',
        input_artifact_refs=prepared['input_artifact_refs'])
    control_ref = registry.store.artifact(canonical(control), 'application/json')
    refs = list(dict.fromkeys([*capture['auxiliary_artifact_refs'], sheet['artifact_ref'], components['artifact_ref']]))
    parents = [capture['id']] if arguments['mode'] == 'run_native' else [arguments['result_ref']]
    source = registry._put('source', dict(provider=TOOL, accession=None, uri=None, artifact_ref=packet_ref,
        text_ref=None, request_ref=control_ref, version=SOURCE_VERSION, retrieved_at=datetime.now(timezone.utc).isoformat(),
        parent_source_refs=parents, auxiliary_artifact_refs=[r for r in refs if r not in prepared['input_artifact_refs']]), origin='tool')
    return homer_motif_return(result['value'], source_ref=source['id'])


def read_homer_action_result(registry, context, arguments, operation_key, *, reader):
    arguments = _arguments(arguments)
    active = registry._current_invocation.get()
    recovery = context if active is not None and active[0] is context and active[4] == operation_key else None
    details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
        recovery_context=recovery, recovery_operation_key=operation_key if recovery is not None else None)
    outcome = details['outcome']
    _require(outcome.get('status') in ('completed', 'partial') and type(outcome.get('result')) is dict,
        'action_result_unavailable')
    public = validate_homer_motif_return(outcome['result'])
    _require(outcome.get('record_refs') == [public['source_ref']], 'action_source_conflict')
    redisplay = arguments['mode'] != 'run_native' and arguments['result_ref'] == public['source_ref']
    with registry.store.read_snapshot():
        publication = _read_homer_publication(registry, context, reader, public['source_ref'],
            recovery_operation_key=None if redisplay else operation_key,
            before_decision_index=details['invocation']['decision_index'])
    _require(_same(publication['public'], public), 'action_source_conflict')
    if redisplay:
        _require(outcome.get('changed_record_refs') == [], 'action_source_conflict')
        if arguments['mode'] == 'calculate_saved':
            _require(_same(arguments['selector'], public['selector']), 'action_source_conflict')
    else:
        _require(publication['producer']['operation_ref'] == details['operation_ref'], 'action_source_conflict')
    return public


def _outcome(arguments, operation_key, public):
    partial = bool(public['issues']) or public['population_facts']['state'] != 'complete'
    partial |= any(public['execution'][key] not in ('succeeded', 'not_run')
        for key in ('wrapper_outcome', 'known_outcome', 'denovo_outcome'))
    partial |= any(s['capture_state'] != 'complete' or s['issues']
        or any(r['parse_state'] != 'complete' for r in s['observations']) for s in public['selected_series'])
    redisplay = arguments['mode'] != 'run_native' and public['source_ref'] == arguments['result_ref']
    return dict(status='partial' if partial else 'completed',
        operation_ref=identity('operation', dict(key=operation_key, name=TOOL, arguments=arguments)),
        record_refs=[public['source_ref']], changed_record_refs=[] if redisplay else [public['source_ref']], result=public,
        feedback=dict(category='representation', code='homer_motif_selected_result_partial',
            source_ref=public['source_ref']) if partial else None)


def _failure(registry, arguments, operation_key, error):
    message = str(error)
    code = message if re.fullmatch(r'[a-z][a-z0-9_]*', message) else 'homer_motif_execution_failed'
    diagnostic = registry.store.artifact(canonical(dict(version='homer_motif_diagnostic_v1',
        exception_type=type(error).__module__ + '.' + type(error).__name__, exception_message=message,
        cause=None if error.__cause__ is None else dict(exception_type=type(error.__cause__).__module__ + '.' + type(error.__cause__).__name__,
            exception_message=str(error.__cause__)))), 'application/json')
    return dict(status='unavailable' if isinstance(error, (_KnownUnavailable, _native().HomerPreflightRejected, OSError))
        or code.endswith('_unavailable') else 'failed' if isinstance(error, _KnownFailure) else
        'invalid' if isinstance(error, (ValueError, TypeError, KeyError)) else 'failed',
        operation_ref=identity('operation', dict(key=operation_key, name=TOOL, arguments=arguments)),
        record_refs=[], changed_record_refs=[], result=None,
        feedback=dict(category='execution', code=code, diagnostic_ref=diagnostic))


async def execute_homer_tool(registry, arguments, *, scope, operation_key, authority):
    context, reader = authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
    _require(type(authority) is tuple and len(authority) == 2 and authority[0] is context and authority[1] is reader,
        'invocation_authority_conflict')
    owner = registry.execution_owner_for(context.run_id)
    _require(owner.store is registry.store and owner.tool_registry is registry and owner.run_id == context.run_id,
        'execution_owner_conflict')
    invocation = _invocation(context, operation_key)
    directory = _directory(registry.store.path / 'cache' / 'molecular-measurements' / digest(operation_key))
    async with _action_lock(directory):
        authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
        if registry.store.db.execute('SELECT 1 FROM tool_operations WHERE operation_key=?', (operation_key,)).fetchone():
            details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
                recovery_context=context, recovery_operation_key=operation_key)
            outcome = details['outcome']
            if outcome.get('status') in ('completed', 'partial'):
                _require(_same(read_homer_action_result(registry, context, arguments, operation_key, reader=reader),
                    outcome['result']), 'cached_result_conflict')
            else:
                _require(outcome.get('status') in ('failed', 'invalid', 'unavailable')
                    and outcome.get('result') is None and outcome.get('record_refs') == [], 'cached_failure_conflict')
            return outcome
        original_attempt_possible = False
        try:
            arguments = _arguments(arguments)
            configuration = _configuration(registry._homer_configuration)
            if arguments['mode'] != 'run_native':
                _require(configuration['saved_modes'], 'saved_modes_not_configured')
                with registry.store.read_snapshot():
                    publication = _read_homer_publication(registry, context, reader, arguments['result_ref'],
                        before_decision_index=invocation['decision_index'])
                if arguments['mode'] == 'read_stored' or _same(arguments['selector'], publication['public']['selector']):
                    public = publication['public']
                    prepared = None
                else:
                    with registry.store.read_snapshot():
                        publication = _read_homer_publication(registry, context, reader, arguments['result_ref'],
                            require_sheet=True, before_decision_index=invocation['decision_index'])
                    previous = publication['control']
                    prepared = dict(capture_source=registry.store.get(previous['capture_source']['source_ref']),
                        sheet_file=previous['sheet_file'], input_artifact_refs=previous['input_artifact_refs'],
                        source_admission=publication['received_input'],
                        source_decision_admission=publication['source_decision_admission'],
                        original_source=dict(source_ref=publication['source']['id'], record_sha256=digest(publication['source'])))
                    request = dict(version=WORKER_REQUEST_VERSION, mode='calculate_saved', files=None, invocation=None,
                        execution=None, saved=dict(file=prepared['sheet_file'], path=_path(registry, prepared['sheet_file'])),
                        selection=arguments['selector'], projection_source_ref=arguments['result_ref'])
            else:
                binding_path = directory / 'native-binding.json'
                if binding_path.exists():
                    binding = decode_json(binding_path.read_bytes())
                    _closed(binding, 'version invocation arguments selected policy frozen_inputs input_admissions input_decision_admissions')
                    _require(binding['version'] == 'ordinary_homer_host_binding_v1'
                        and _same(binding['invocation'], invocation) and _same(binding['arguments'], arguments), 'original_binding_conflict')
                    _check_frozen_inputs(registry, context, arguments, binding, invocation['decision_index'])
                else:
                    _require(len(configuration['bindings']) == 1, 'configuration_required')
                    selected = configuration['bindings'][0]
                    _run_selection(registry, owner, selected, configuration['policy'])
                    frozen, admissions, decisions = _fresh_inputs(registry, context, reader, arguments, invocation['decision_index'])
                    binding = dict(version='ordinary_homer_host_binding_v1', invocation=invocation, arguments=arguments,
                        selected=selected, policy=configuration['policy'], frozen_inputs=frozen, input_admissions=admissions,
                        input_decision_admissions=decisions)
                    _immutable(binding_path, binding)
                original_attempt_possible = True
                native = _native().prepare_ordinary_homer_attempt(context=context, operation_key=operation_key,
                    arguments=arguments['parameters'], frozen_inputs=binding['frozen_inputs'], selected=binding['selected'],
                    policy=LocalJobPolicy(**binding['policy']))
                execution = await _observe_native(native)
                authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
                _check_frozen_inputs(registry, context, arguments, binding, invocation['decision_index'])
                with registry.store.transaction():
                    capture, files, excluded, native_execution = _native_capture(registry, invocation, arguments, binding, execution, directory)
                prepared = dict(capture_source=capture, sheet_file=None, input_artifact_refs=excluded,
                    source_admission=None, source_decision_admission=None, original_source=None,
                    native_call_state='returned' if native_execution['wrapper_outcome'] in ('succeeded', 'failed') else
                        'not_started' if native_execution['wrapper_outcome'] == 'not_run' else 'unconfirmed')
                request = dict(version=WORKER_REQUEST_VERSION, mode='parse', files=files,
                    invocation=_measurement_invocation(execution), execution=native_execution, saved=None,
                    selection=arguments['selection'], projection_source_ref=capture['id'])
            if prepared is not None:
                worker_directory = _directory(directory / 'calculation')
                _immutable(worker_directory / 'homer-intent.json', dict(invocation=invocation, arguments=arguments, request=request,
                    source_admission=prepared['source_admission'], source_decision_admission=prepared['source_decision_admission']))
                work = await registry._sequence_worker_async(WORKER_OPERATION, dict(request=request),
                    directory=worker_directory, owned_directory=worker_directory)
                authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
                if arguments['mode'] == 'calculate_saved':
                    _require(_same(_admit(registry.store, reader, context, arguments['result_ref'], 'source',
                        invocation['decision_index']), prepared['source_admission']), 'source_admission_conflict')
                    _require(_same(_decision_admission(registry, context, arguments['result_ref'], invocation['decision_index']),
                        prepared['source_decision_admission']), 'source_decision_admission_conflict')
                else:
                    _check_frozen_inputs(registry, context, arguments, binding, invocation['decision_index'])
                result, worker = _worker_completion(work, request, worker_directory)
                with registry.store.transaction():
                    public = _publish(registry, arguments, invocation, prepared, result, worker, worker_directory)
                    outcome = _outcome(arguments, operation_key, public)
                    registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
                return outcome
            authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
            with registry.store.transaction():
                outcome = _outcome(arguments, operation_key, public)
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome
        except (asyncio.CancelledError, MolecularOperationUnpublished):
            raise
        except Exception as error:
            if original_attempt_possible and not isinstance(error, (_KnownUnavailable, _KnownFailure, _native().HomerPreflightRejected)):
                raise MolecularOperationUnpublished('homer_motif_original_action_unpublished') from error
            with registry.store.transaction():
                outcome = _failure(registry, arguments, operation_key, error)
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome


__all__ = ['TOOL', 'normalize_homer_configuration', 'homer_tool_contract', 'execute_homer_tool',
    'read_homer_action_result', 'read_retained_homer_publication', 'homer_motif_fact_sources',
    'homer_capture_reference_restriction']
