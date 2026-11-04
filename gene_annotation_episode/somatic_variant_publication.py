"""Authenticated retained somatic-stage publications; no parsing or calculation.

The selected current action, actual native capture and owned result worker are
joined to private retained Sheets and one controlled public packet. Only the
outer Source is a semantic grant. Saved reads never reopen original operands.
"""
from datetime import datetime, timezone
import re

from .alignment_site_native import immutable_record
from .domain import ContractError
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .local_jobs import LocalJobPolicy
from .molecular_measurement_tools import (
    _publication_bytes, _recorded_molecular_action_details, _recorded_molecular_producer_details,
    authenticate_molecular_invocation,
)
from .native_file_capture import capture_native_file
from .native_flux_balance_storage import decode_json
from .reference_edit_outcome_tools import _admit, _context, _current_cutoff, _frozen_admission, _invocation
from . import somatic_variant_contracts as contracts
from . import somatic_variant_result_worker as result_worker
from . import vcf_result_measurements as vcf

TOOL = contracts.TOOL
SOURCE_VERSION = contracts.SOURCE_VERSION
CONTROL_VERSION = 'ordinary_somatic_variant_publication_v1'
CAPTURE_VERSION = 'ordinary_somatic_variant_native_capture_v1'
_CONTROL_FIELDS = ('version arguments invocation capture_source stage_sheets context_file components_file value_file '
    'input_artifact_refs source_admission source_decision_admission original_source policy selected_resource worker')
_PREPARED_FIELDS = ('capture_source stage_sheets context_file input_artifact_refs source_admission '
    'source_decision_admission original_source policy selected_resource')
_FILE_FIELDS = {'context_file': contracts.CONTEXT_VERSION,
    'components_file': vcf.COMPONENTS_VERSION, 'value_file': contracts.PACKET_VERSION}



def _ports():
    # The execution owner imports publication ports only when executing them.
    from . import somatic_variant_tools
    return somatic_variant_tools


def _require(condition, code):
    if not condition:
        raise ContractError("somatic_variant_" + code)


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()), "fields_invalid")


def _same(first, second):
    return canonical(first) == canonical(second)


def _input_refs(value):
    _require(type(value) is list and all(type(item) is str and
        re.fullmatch(r"artifact_[0-9a-f]{64}", item) is not None for item in value)
        and len(value) == len(set(value)), "input_files_conflict")
    return value


def _checked_file(registry, value, format, *, nullable=False):
    if value is None:
        _require(nullable, "document_missing")
        return None
    file = _ports()._file(registry, value)
    _require(file["format"] == format, "document_format_conflict")
    return file


def _document(registry, file):
    return None if file is None else decode_json(_publication_bytes(registry.store, file["artifact_ref"]))


def _capture(registry, descriptor):
    _closed(descriptor, "source_ref record_sha256")
    capture = registry.store.get(descriptor["source_ref"])
    immutable_record(capture)
    _require(capture.get("record_type") == "source" and capture.get("origin") == "tool"
        and capture.get("provider") == TOOL and capture.get("version") == CAPTURE_VERSION
        and digest(capture) == descriptor["record_sha256"] and "operand_refs" not in capture,
        "capture_source_conflict")
    return capture


def _file_values(registry, control):
    files = {key: _checked_file(registry, control[key], format) for key, format in _FILE_FIELDS.items()}
    sheets = control['stage_sheets']
    _require(type(sheets) is list and len(sheets) == 3, 'stage_sheets_conflict')
    files['stage_sheets'] = []
    for row, stage in zip(sheets, contracts.STAGES):
        _closed(row, 'stage file')
        _require(row['stage'] == stage, 'stage_sheets_conflict')
        files['stage_sheets'].append(dict(stage=stage, file=_checked_file(registry, row['file'], vcf.SHEET_VERSION)))
    return files


def _declaration(name, format, file):
    _require(file['format'] == format, 'document_format_conflict')
    return dict(relative_path=name, format=format, sha256=file['sha256'], size_bytes=file['size_bytes'])


def _worker_result(arguments, files):
    native = arguments['mode'] == 'run_native'
    return dict(version=result_worker.OUTPUT_VERSION, mode='parse' if native else 'calculate_saved',
        stage_sheets=[dict(stage=row['stage'], sheet=_declaration(row['stage'] + '_sheet.json',
            vcf.SHEET_VERSION, row['file']) if native else None) for row in files['stage_sheets']],
        context=_declaration('context.json', contracts.CONTEXT_VERSION, files['context_file']),
        components=_declaration('components.json', vcf.COMPONENTS_VERSION, files['components_file']),
        value=_declaration('value.json', contracts.PACKET_VERSION, files['value_file']))


def _private_files(capture, files, excluded):
    references = [capture['artifact_ref'], capture['request_ref'], *capture.get('auxiliary_artifact_refs', [])]
    references.extend(row['file']['artifact_ref'] for row in files['stage_sheets'])
    references.extend(files[name]['artifact_ref'] for name in ('context_file', 'components_file'))
    return [ref for ref in dict.fromkeys(references) if ref not in excluded and ref != files['value_file']['artifact_ref']]


def _metadata_publication(registry, source_ref, *, recovery_context=None, recovery_operation_key=None):
    source = registry.store.get(source_ref)
    immutable_record(source)
    _require(source.get('record_type') == 'source' and source.get('origin') == 'tool'
        and source.get('provider') == TOOL and source.get('version') == SOURCE_VERSION
        and source.get('accession') is source.get('uri') is source.get('text_ref') is None
        and 'operand_refs' not in source, 'producer_required')
    producer = _recorded_molecular_producer_details(registry, source_ref, TOOL,
        recovery_context=recovery_context, recovery_operation_key=recovery_operation_key)
    arguments = contracts.validate_somatic_arguments(producer['arguments'])
    public = contracts.validate_somatic_return(producer['outcome']['result'])
    _require(public['source_ref'] == source_ref and producer['outcome']['record_refs'] == [source_ref]
        and arguments['mode'] in ('run_native', 'calculate_saved')
        and _same(public['selection'], arguments['selection']), 'publication_conflict')
    parents = source.get('parent_source_refs')
    if arguments['mode'] == 'run_native':
        _require(type(parents) is list and len(parents) == 1, 'capture_source_conflict')
        capture = registry.store.get(parents[0])
        immutable_record(capture)
        _require(capture.get('record_type') == 'source' and capture.get('origin') == 'tool'
            and capture.get('provider') == TOOL and capture.get('version') == CAPTURE_VERSION
            and capture.get('accession') == producer['operation_ref'], 'capture_source_conflict')
    else:
        _require(parents == [arguments['result_ref']], 'original_source_conflict')
    return dict(source=source, producer=producer, public=public, control=None,
        received_input=None, source_decision_admission=None)


def _documents(registry, files, arguments):
    context = contracts.validate_somatic_context(_document(registry, files['context_file']))
    sheets = {row['stage']: vcf.validate_vcf_sheet(_document(registry, row['file'])) for row in files['stage_sheets']}
    for stage, sheet in sheets.items():
        contracts.validate_somatic_stage_input(sheet['input'], context=context, stage=stage)
    selected = sheets[arguments['selection']['stage']]
    contracts.validate_somatic_selection(arguments['selection'], sheet=selected)
    components = vcf.validate_vcf_components(_document(registry, files['components_file']))
    _require(components['sheet_sha256'] == vcf._hash(selected), 'selected_sheet_conflict')
    packet = contracts.build_somatic_packet(context=context, selection=arguments['selection'], components=components)
    supplied = contracts.validate_somatic_packet(_document(registry, files['value_file']))
    _require(_same(packet, supplied), 'saved_value_conflict')
    return dict(context=context, sheets=sheets, components=components, value=packet)


def _saved_request(registry, arguments, control, *, store_root):
    sheet = next(row['file'] for row in control['stage_sheets'] if row['stage'] == arguments['selection']['stage'])
    return result_worker.validate_somatic_result_request(dict(version=result_worker.REQUEST_VERSION,
        mode='calculate_saved', stage_inputs=None, saved=dict(stage=arguments['selection']['stage'],
            sheet=dict(path=_ports()._path(registry, sheet, store_root=store_root), file=sheet)),
        context=contracts.validate_somatic_context(_document(registry, control['context_file'])),
        selection=arguments['selection']))


def _native_documents(documents, request):
    _require(_same(documents['context'], request['context']), 'native_document_conflict')
    for row in request['stage_inputs']:
        actual = documents['sheets'][row['stage']]['input']
        item = row['input']
        if item is None:
            _require(actual['retained_file'] is actual['original_file'] is actual['source_ref'] is None
                and actual['capture']['state'] == 'missing', 'stage_capture_conflict')
        else:
            _require(_same(actual['retained_file'], item['file']) and _same(actual['original_file'], item['file'])
                and actual['input_id'] == actual['source_ref'] == item['source_ref']
                and _same(actual['capture'], item['capture']), 'stage_capture_conflict')


def _control(registry, publication, seen):
    source, producer = publication['source'], publication['producer']
    _require(source['id'] not in seen, 'source_lineage_cycle')
    seen = {*seen, source['id']}
    control = decode_json(_publication_bytes(registry.store, source['request_ref']))
    _closed(control, _CONTROL_FIELDS)
    arguments = contracts.validate_somatic_arguments(control['arguments'])
    _require(control['version'] == CONTROL_VERSION and _same(arguments, producer['arguments'])
        and _same(control['invocation'], producer['invocation']), 'control_conflict')
    files = _file_values(registry, control)
    _require(source['artifact_ref'] == files['value_file']['artifact_ref'], 'public_file_conflict')
    input_refs = _input_refs(control['input_artifact_refs'])
    capture = _capture(registry, control['capture_source'])
    ports = _ports()
    if arguments['mode'] == 'run_native':
        checked = ports._capture_control(registry, capture, invocation=control['invocation'],
            arguments=arguments, input_artifact_refs=input_refs)
        _require(source.get('parent_source_refs') == [capture['id']]
            and control['source_admission'] is control['source_decision_admission'] is control['original_source'] is None
            and _same(control['policy'], checked['control']['policy'])
            and _same(control['selected_resource'], checked['control']['selected_resource']), 'capture_source_conflict')
        request = checked['request']
        root = checked['store_root']
    else:
        original = control['original_source']
        _closed(original, 'source_ref record_sha256')
        _require(original['source_ref'] == arguments['result_ref'] and source.get('parent_source_refs') == [original['source_ref']]
            and control['selected_resource'] is None, 'original_source_conflict')
        previous = _metadata_publication(registry, original['source_ref'])
        _require(digest(previous['source']) == original['record_sha256'], 'original_source_conflict')
        owner = _context(registry.store, control['invocation'])
        _frozen_admission(registry.store, owner, control['source_admission'], original['source_ref'], 'source', control['invocation']['decision_index'])
        _require(_same(ports._source_admission(registry, owner, original['source_ref'],
            control['invocation']['decision_index']), control['source_decision_admission']), 'source_decision_admission_conflict')
        prior, prior_documents = _control(registry, previous, seen)
        _require(_same(control['capture_source'], prior['capture_source']) and input_refs == prior['input_artifact_refs']
            and _same(files['stage_sheets'], prior['stage_sheets']) and _same(files['context_file'], prior['context_file']), 'saved_documents_conflict')
        root = ports._historical_store_root(control['worker'], control['invocation'], 'calculation')
        request = _saved_request(registry, arguments, prior, store_root=root)
    result_worker.validate_somatic_result_request(request)
    _require(ports._worker_control(control['worker'], request, contracts.RESULT_OPERATION, control['invocation'], 'calculation') == root,
        'worker_store_conflict')
    _require(_same(LocalJobPolicy(**control['policy']).to_dict(), contracts.POLICY)
        and _same(control['worker']['selection']['policy'], control['policy']), 'action_policy_conflict')
    _require(control['worker']['observation'].get('state') == 'returned'
        and type(control['worker']['observation']['metadata'].get('native_returncode')) is int
        and control['worker']['observation']['metadata']['native_returncode'] == 0, 'result_worker_failed')
    _require(control['worker']['result_sha256'] == digest(_worker_result(arguments, files)), 'worker_result_conflict')
    _require(source.get('auxiliary_artifact_refs') == _private_files(capture, files, input_refs), 'private_files_conflict')
    documents = _documents(registry, files, arguments)
    _require(_same(contracts.project_somatic_return(documents['value'], source['id']), publication['public']), 'public_packet_conflict')
    if arguments['mode'] == 'run_native':
        _native_documents(documents, request)
    return control, documents


def _read_somatic_variant_publication(registry, context, reader, source_ref, *,
        recovery_operation_key=None, require_documents=False, before_decision_index=None):
    EpisodeReturnRecords(registry.store, context.run_id, failure_prefix='somatic_variant_').authenticate(context)
    _require(type(require_documents) is bool, 'document_selection_invalid')
    publication = _metadata_publication(registry, source_ref,
        recovery_context=context if recovery_operation_key is not None else None,
        recovery_operation_key=recovery_operation_key)
    invocation = publication['producer']['invocation']
    own = (recovery_operation_key is not None and invocation['operation_key'] == recovery_operation_key
        and (invocation['run_id'], invocation['episode_id']) == (context.run_id, context.episode_id))
    cutoff = _current_cutoff(registry, context) if before_decision_index is None else before_decision_index
    _require(type(cutoff) is int and cutoff >= 0, 'source_cutoff_invalid')
    if not own:
        publication['received_input'] = _admit(registry.store, reader, context, source_ref, 'source', cutoff)
        active = registry._current_invocation.get()
        if before_decision_index is not None or active is not None and active[0] is context:
            publication['source_decision_admission'] = _ports()._source_admission(registry, context, source_ref, cutoff)
    packet = contracts.validate_somatic_packet(decode_json(_publication_bytes(registry.store, publication['source']['artifact_ref'])))
    _require(_same(contracts.project_somatic_return(packet, source_ref), publication['public']), 'public_packet_conflict')
    if require_documents:
        publication['control'], _ = _control(registry, publication, set())
    return publication


def read_retained_somatic_variant_publication(registry, context, reader, source_ref, *, recovery_operation_key=None):
    with registry.store.read_snapshot():
        return _read_somatic_variant_publication(registry, context, reader, source_ref,
            recovery_operation_key=recovery_operation_key)['public']


def read_somatic_variant_action_result(registry, context, arguments, operation_key, *, reader):
    arguments = contracts.validate_somatic_arguments(arguments)
    active = registry._current_invocation.get()
    recovery = context if active is not None and active[0] is context and active[4] == operation_key else None
    details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
        recovery_context=recovery, recovery_operation_key=operation_key if recovery is not None else None)
    outcome = details['outcome']
    _require(outcome.get('status') in ('completed', 'partial') and type(outcome.get('result')) is dict, 'action_result_unavailable')
    public = contracts.validate_somatic_return(outcome['result'])
    _require(outcome.get('record_refs') == [public['source_ref']], 'action_source_conflict')
    redisplay = arguments['mode'] == 'read_stored'
    with registry.store.read_snapshot():
        publication = _read_somatic_variant_publication(registry, context, reader, public['source_ref'],
            recovery_operation_key=None if redisplay else operation_key,
            before_decision_index=details['invocation']['decision_index'])
        if redisplay:
            _require(public['source_ref'] == arguments['result_ref'] and outcome.get('changed_record_refs') == [], 'action_source_conflict')
        else:
            _require(publication['producer']['operation_ref'] == details['operation_ref']
                and _same(public['selection'], arguments['selection']), 'action_source_conflict')
        _require(_same(publication['public'], public), 'action_source_conflict')
    return public


def validate_somatic_variant_fact(registry, context, reader, value):
    value = contracts.validate_somatic_return(value)
    with registry.store.read_snapshot():
        expected = _read_somatic_variant_publication(registry, context, reader, value['source_ref'])['public']
        _require(_same(expected, value), 'selected_fact_conflict')
        return expected


def _capture_component(registry, directory, declaration, name, format):
    _closed(declaration, 'relative_path format sha256 size_bytes')
    _require(declaration['relative_path'] == name and declaration['format'] == format, 'component_declaration_conflict')
    file = capture_native_file(registry.store, directory=str(directory), relative_path=name,
        format=format, media_type='application/json')
    _require(type(declaration['size_bytes']) is int and all(file[key] == declaration[key]
        for key in ('sha256', 'size_bytes')), 'component_identity_conflict')
    return file


def _publish(registry, arguments, invocation, prepared, result, worker, directory):
    """Retain a Source in the same transaction as its original ToolOperation."""
    _require(registry.store.db.in_transaction, 'publication_transaction_required')
    arguments = contracts.validate_somatic_arguments(arguments)
    _require(arguments['mode'] in ('run_native', 'calculate_saved'), 'producer_mode_invalid')
    context, reader = authenticate_molecular_invocation(registry, TOOL, arguments, invocation['scope'], invocation['operation_key'])
    _require(_same(_invocation(context, invocation['operation_key']), invocation), 'invocation_conflict')
    _closed(prepared, _PREPARED_FIELDS)
    result = result_worker.validate_somatic_result_output(result)
    _require(result['mode'] == ('parse' if arguments['mode'] == 'run_native' else 'calculate_saved')
        and worker['result_sha256'] == digest(result), 'worker_result_conflict')
    capture = prepared['capture_source']
    immutable_record(capture)
    _require(_same(registry.store.get(capture['id']), capture), 'capture_source_conflict')
    input_refs = _input_refs(prepared['input_artifact_refs'])
    ports = _ports()
    if arguments['mode'] == 'run_native':
        _require(prepared['stage_sheets'] is prepared['context_file'] is prepared['original_source']
            is prepared['source_admission'] is prepared['source_decision_admission'] is None, 'native_preparation_conflict')
        checked = ports._capture_control(registry, capture, invocation=invocation,
            arguments=arguments, input_artifact_refs=input_refs)
        _require(_same(prepared['policy'], checked['control']['policy'])
            and _same(prepared['selected_resource'], checked['control']['selected_resource']), 'action_policy_conflict')
        request = checked['request']
    else:
        original = prepared['original_source']
        _closed(original, 'source_ref record_sha256')
        _require(original['source_ref'] == arguments['result_ref'] and prepared['selected_resource'] is None, 'original_source_conflict')
        previous = _read_somatic_variant_publication(registry, context, reader, arguments['result_ref'],
            require_documents=True, before_decision_index=invocation['decision_index'])
        prior = previous['control']
        _require(digest(previous['source']) == original['record_sha256']
            and _same(previous['received_input'], prepared['source_admission'])
            and _same(previous['source_decision_admission'], prepared['source_decision_admission'])
            and _same(prepared['stage_sheets'], prior['stage_sheets'])
            and _same(prepared['context_file'], prior['context_file'])
            and _same(dict(source_ref=capture['id'], record_sha256=digest(capture)), prior['capture_source'])
            and input_refs == prior['input_artifact_refs'], 'saved_preparation_conflict')
        request = _saved_request(registry, arguments, prior,
            store_root=ports._historical_store_root(worker, invocation, 'calculation'))
    result_worker.validate_somatic_result_request(request)
    root = ports._worker_control(worker, request, contracts.RESULT_OPERATION, invocation, 'calculation')
    _require(worker['observation'].get('state') == 'returned'
        and type(worker['observation']['metadata'].get('native_returncode')) is int
        and worker['observation']['metadata']['native_returncode'] == 0, 'result_worker_failed')
    _require(_same(LocalJobPolicy(**prepared['policy']).to_dict(), contracts.POLICY)
        and _same(worker['selection']['policy'], prepared['policy'])
        and str(directory) == worker['selection']['cwd'], 'action_policy_conflict')
    if arguments['mode'] == 'run_native':
        _require(root == checked['store_root'], 'worker_store_conflict')
        stage_sheets = [dict(stage=row['stage'], file=_capture_component(registry, directory,
            row['sheet'], row['stage'] + '_sheet.json', vcf.SHEET_VERSION)) for row in result['stage_sheets']]
    else:
        stage_sheets = prepared['stage_sheets']
    files = dict(stage_sheets=stage_sheets)
    for name, format in (('context', contracts.CONTEXT_VERSION), ('components', vcf.COMPONENTS_VERSION), ('value', contracts.PACKET_VERSION)):
        files[name + '_file'] = _capture_component(registry, directory, result[name], name + '.json', format)
    files = _file_values(registry, files)
    _require(_same(_worker_result(arguments, files), result), 'worker_result_conflict')
    documents = _documents(registry, files, arguments)
    if arguments['mode'] == 'run_native':
        _native_documents(documents, request)
    else:
        _require(_same(files['context_file'], prepared['context_file']), 'saved_context_conflict')
    control = dict(version=CONTROL_VERSION, arguments=arguments, invocation=invocation,
        capture_source=dict(source_ref=capture['id'], record_sha256=digest(capture)), **files,
        input_artifact_refs=input_refs, source_admission=prepared['source_admission'],
        source_decision_admission=prepared['source_decision_admission'], original_source=prepared['original_source'],
        policy=prepared['policy'], selected_resource=prepared['selected_resource'], worker=worker)
    control_ref = registry.store.artifact(canonical(control), 'application/json')
    source = registry._put('source', dict(provider=TOOL, accession=None, uri=None,
        artifact_ref=files['value_file']['artifact_ref'], text_ref=None, request_ref=control_ref,
        version=SOURCE_VERSION, retrieved_at=datetime.now(timezone.utc).isoformat(),
        parent_source_refs=[capture['id']] if arguments['mode'] == 'run_native' else [arguments['result_ref']],
        auxiliary_artifact_refs=_private_files(capture, files, input_refs)), origin='tool')
    return contracts.project_somatic_return(documents['value'], source['id'])

