"""Supply authenticated, explicitly selected records to GenomeAlignment C.

This collector reads the existing Store. Scientific extraction stays in the
pure provider. A task-info receipt does not grant its native log to a receiver.
"""
from copy import deepcopy
import hashlib

from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_appservice_records import PROVIDER, VERSION
from .execution_contracts import canonical, digest


def _require(condition, code):
    if not condition:
        raise ValueError('appservice_genome_alignment_' + code)


def collect_retained_records(publications, context, inputs, bundle, *, current_acquisition):
    """Return the original receipt tuple and exact supplied artifact bytes.

    Only the current just-published acquisition may precede runtime completion.
    Its original action, transport and receipt are still authenticated. Prior
    records require normal completed-action custody before this decision.
    """
    host, store = publications.host, publications.store
    host.custody.authenticate(context)
    inputs = validate_contract('PublicationInputs', inputs)
    bundle = validate_contract('ArtifactBundle', bundle)
    task = bundle['original_task']
    _require(task['required_application_id'] == task['native_application_id'] == 'GenomeAlignment',
        'application_conflict')
    _require(current_acquisition.get('contract') == 'AcquisitionReceipt', 'current_acquisition_required')
    current = host.records.read(current_acquisition['source_ref'], require_completed=False)
    _require(canonical(current) == canonical(current_acquisition), 'current_acquisition_conflict')
    value, reference = current['value'], current['source_ref']
    origin = value['origin']
    before = int(origin['operation_key'].rsplit(':', 1)[1])
    _require(origin['run_id'] == context.run_id and origin['episode_id'] == context.episode_id
        and context.role == 'results'
        and value['original_handoff_ref'] == inputs['original_handoff_ref']
        and canonical(value['snapshot']) == canonical(inputs['current_snapshot'])
        and value['publication_inputs_sha256'] == digest(inputs)
        and bundle['acquisition_receipt_refs'] == [*inputs['prior_acquisition_receipt_refs'], reference],
        'current_acquisition_conflict')

    original = host.read_handoff(inputs['original_handoff_ref'], context.scope)
    _require(canonical(original['task_handoff']['original_task']) == canonical(task)
        and original['assignment']['resource_id'] == task['resource_id']
        and canonical(original['assignment']['request']) == canonical(inputs['request']),
        'original_task_conflict')

    raw, explicit_contents = {}, []

    def add_bytes(binding, data):
        binding = validate_contract('ContentBinding', binding)
        _require(len(data) == binding['byte_count']
            and hashlib.sha256(data).hexdigest() == binding['sha256'], 'content_binding_conflict')
        key = binding['artifact_ref']
        _require(key not in raw or raw[key] == data, 'content_bytes_conflict')
        raw[key] = data

    for binding in bundle.get('supplied_contents', []):
        add_bytes(binding, host.custody.content(context, binding, before=before))
        explicit_contents.append(binding)
    for evidence in bundle['supplied_scientific_metadata']:
        host.custody.evidence(context, evidence, before=before)
        binding = evidence['content']
        add_bytes(binding, host.custody.content(context, binding, before=before))
        explicit_contents.append(binding)

    result, seen, identity_receipts = [], set(), set()

    def append_record(record, *, is_current=False):
        ref, kind, value = record['source_ref'], record['contract'], record['value']
        if ref in seen:
            return
        _require(kind in {'TaskHandoff', 'TaskInfoReceipt', 'AcquisitionReceipt', 'WorkspaceReceipt'},
            'receipt_contract_conflict')
        if not is_current:
            host.custody.possession(context, ref, before=before)
        common = value if kind == 'AcquisitionReceipt' else value['receipt']
        snapshot = common['snapshot']
        _require(snapshot is not None, 'receipt_snapshot_required')
        if kind == 'TaskHandoff':
            _require(ref == inputs['original_handoff_ref']
                and canonical(value['original_task']) == canonical(task), 'original_task_conflict')
        elif kind != 'WorkspaceReceipt':
            _require(value['original_handoff_ref'] == inputs['original_handoff_ref'], 'receipt_task_conflict')
            if kind == 'TaskInfoReceipt':
                _require(value['task_id'] == task['task_id'], 'receipt_task_conflict')
            else:
                _require(value['artifact']['task_association']['task_id'] == task['task_id'],
                    'receipt_task_conflict')
        producer = host.custody.context(common['origin']['episode_id'])
        _require(producer.role in {'launch_api', 'results'}, 'receipt_request_conflict')
        if producer.role == 'results':
            _require(producer.assignment['handoff_ref'] == inputs['original_handoff_ref'], 'receipt_task_conflict')
        resource = (producer.assignment.get('resource_id') if producer.role == 'launch_api'
            else host.read_target(producer.assignment['handoff_ref'], producer.scope)['resource_id'])
        _require(common['origin']['run_id'] == context.run_id and resource == task['resource_id']
            and canonical(snapshot['selected_operands']['native_operands']['request'])
                == canonical(inputs['request']), 'receipt_request_conflict')

        source = host.records._source(ref, provider=PROVIDER, origin='tool', version=VERSION)
        envelope = store.get_artifact(source['artifact_ref'])
        binding = validate_contract('ContentBinding', {'source_ref': ref, 'artifact_field': 'artifact_ref',
            'artifact_ref': source['artifact_ref'], 'sha256': hashlib.sha256(envelope).hexdigest(),
            'byte_count': len(envelope)})
        if not is_current:
            envelope = host.custody.content(context, binding, before=before)
        add_bytes(binding, envelope)

        native_binding = snapshot['content']
        if kind != 'TaskInfoReceipt':
            # Original submission and selected output bytes are dependencies
            # already authenticated by the real host receipt reader. This is
            # not a grant of arbitrary source data mentioned inside a receipt.
            add_bytes(native_binding, store.get_artifact(native_binding['artifact_ref']))
        elif ref in identity_receipts:
            _require(value['file'] == 'job_result_id', 'receipt_task_conflict')
            add_bytes(native_binding, store.get_artifact(native_binding['artifact_ref']))
        elif any(canonical(native_binding) == canonical(selected) for selected in explicit_contents):
            add_bytes(native_binding, host.custody.content(context, native_binding, before=before))
        # Otherwise retain the receipt without its unreceived native content.
        # C reports its local content_missing requirement; no log is acquired.
        result.append({'receipt_content': binding, 'record': deepcopy(record)})
        seen.add(ref)

    append_record(host.records.read(inputs['original_handoff_ref']))
    for ref in bundle['acquisition_receipt_refs']:
        append_record(current if ref == reference else host.records.read(ref), is_current=ref == reference)
    # This is the actual selected manifest-identity chain, not a traversal of
    # references inside arbitrary scientific metadata. A get metadata row can
    # supply the path/type omitted by the task's UUID-only job_result_id file.
    for retained in tuple(result):
        record = retained['record']
        if record['contract'] != 'AcquisitionReceipt':
            continue
        acquisition = record['value']
        selection, artifact = acquisition['object_selection'], acquisition['artifact']
        link = artifact['task_association']
        if selection['kind'] != 'receipt_row' or link['kind'] != 'task_info_object':
            continue
        metadata = host.records.read(selection['receipt_ref'])
        _require(metadata['contract'] == 'WorkspaceReceipt' and metadata['value']['method'] == 'Workspace.get'
            and artifact['workspace_object']['metadata_receipt_ref'] == metadata['source_ref'],
            'receipt_task_conflict')
        rows = [row for row in metadata['value']['rows'] if row['pointer'] == selection['row_pointer']]
        _require(len(rows) == 1 and rows[0]['valid']
            and all(rows[0][key] == artifact['workspace_object'][key] for key in ('path', 'uuid', 'type')),
            'receipt_task_conflict')
        info_ref = link['evidence_ref']
        _require({'kind': 'task_info_object', 'receipt_ref': info_ref} in metadata['value']['requested_objects'],
            'receipt_task_conflict')
        info = host.records.read(info_ref)
        _require(info['contract'] == 'TaskInfoReceipt' and info['value']['file'] == 'job_result_id'
            and info['value']['reported_object_uuid'] == artifact['workspace_object']['uuid'],
            'receipt_task_conflict')
        append_record(metadata)
        identity_receipts.add(info_ref)
        append_record(info)
    for evidence in bundle['supplied_scientific_metadata']:
        ref = evidence['content']['source_ref']
        source = store.get(ref)
        if source.get('provider') != PROVIDER or source.get('version') != VERSION:
            continue
        record = host.records.read(ref)
        _require(record['contract'] in {'TaskInfoReceipt', 'AcquisitionReceipt', 'WorkspaceReceipt'},
            'receipt_contract_conflict')
        append_record(record)
    return tuple(result), raw


__all__ = ['collect_retained_records']
