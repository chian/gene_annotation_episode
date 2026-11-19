"""The publication step of the A104 results episode: an acquired AppService bundle as records on the shared Store.

After a download unit retains a usable ``AcquisitionReceipt``, the episode publishes the handoff's acquisitions
through ``BVBRCAppServiceService.publish``; this module is that service's ``publication_callback``
(``AppServicePublication``, built by the results binding over the run's shared Store). It

- re-reads and authenticates the original task from the handoff receipt (``ResultInputs.original_task``) and
  every ``AcquisitionReceipt`` the ``PublicationInputs`` name (the prior ones and the current one);
- builds the ``bvbrc_appservice_artifact_bundle_v1`` bundle of those acquisitions (``build_artifact_bundle``).
  The request carries no query rows, so this publication binds none (``query_bindings`` is empty); an adapter
  that requires them reports them missing;
- when the selector selects a scientific adapter, runs that installed adapter once over the bundle, the
  verified bytes of every content it names and the supplied evidence values, and retains its sheet and
  components as Store ``source`` records (``ContentBinding`` each);
- publishes one ``source`` record of provider ``bvbrc_appservice.publication`` and version
  ``bvbrc_appservice_acquired_bundle_v1``: its artifact is the canonical bundle, its text the canonical
  publication envelope (the run and episode, operation key, scope, the original handoff and selector, the
  ``PublicationInputs``, the current acquisition's origin and the ``AdapterResult``).

``read_publication`` reads such a record back into the ``bvbrc_appservice_acquired_bundle_v1`` body its
readers project (``source_ref``/``reference``: the record; ``publication``: the bundle's ``ContentBinding``,
``result_record_refs``, ``adapter_result`` and ``origin``; ``publication_inputs``; ``assignment``;
``record_refs``; ``bundle``) and ``read_adapter_contents`` the saved sheet and components it binds. Nothing
here makes a request, assigns credit or chooses an adapter.
"""
from __future__ import annotations

from copy import deepcopy
import json

from gene_annotation_episode.episodic_workflow.episode_support.forms.service_calls.evolutionary_history_evidence.bvbrc_appservice_contracts import _same, download_request, validate_contract
from gene_annotation_episode.episodic_workflow.episode_support.readers.service_calls.evolutionary_history_evidence.bvbrc_appservice_readers import _bounded_capture, _headers, validate_bundle
from gene_annotation_episode.episodic_workflow.episode_support.forms.evolutionary_history_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.forms.evolutionary_history_evidence.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.held_inputs import read_receipt
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.evolutionary_history_evidence.appservice_acquisition_values import (
    _DOWNLOAD, _diagnostic, _original_object, _publication, _qualifications, _require, _selection, _task, _unique,
    _usable)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.result_inputs import ResultInputs

RESULT_VERSION = 'bvbrc_appservice_acquired_bundle_v1'
PUBLICATION_PROVIDER = 'bvbrc_appservice.publication'
SHEET_PROVIDER = 'bvbrc_appservice.adapter_sheet'
COMPONENTS_PROVIDER = 'bvbrc_appservice.adapter_components'
_ADAPTER_FIELDS = ('adapter_id', 'adapter_version', 'status', 'facts', 'missing_requirements', 'diagnostics')


# -- the artifact bundle (pure) --------------------------------------------------------------------------------
def _acquisition(row, inputs, task):
    _require(type(row) is dict and set(row) == {"receipt_ref", "receipt"}
             and type(row["receipt_ref"]) is str and bool(row["receipt_ref"]), "acquisition_dependency_invalid")
    ref, receipt = row["receipt_ref"], validate_contract("AcquisitionReceipt", row["receipt"])
    args, call = _selection(receipt["snapshot"], inputs)
    artifact, binding = receipt["artifact"], receipt["snapshot"]
    _require(receipt["origin"]["name"] == _DOWNLOAD and receipt["origin"]["arguments_sha256"] == digest(args)
             and receipt["original_handoff_ref"] == inputs["original_handoff_ref"]
             and receipt["selector_sha256"] == digest(inputs["selector"]), "publication_dependency_conflict")
    _require(_same(receipt["object_selection"], args["object"])
             and _same(receipt["capability_selection"], args["capability"])
             and _same(receipt["requirement_ids"], args["requirement_ids"])
             and ("requirement_ids" not in artifact or _same(artifact["requirement_ids"], args["requirement_ids"]))
             and artifact["role"] == args["role"] and _same(artifact["declared_format"], args["declared_format"]),
             "publication_requirement_conflict")
    _require(artifact["task_association"]["task_id"] == task["task_id"], "original_task_mismatch")
    _original_object(args["object"], artifact["workspace_object"], inputs["request"])
    _require(artifact["source_ref"] == binding["source_ref"] == binding["content"]["source_ref"]
             and artifact["raw_artifact_ref"] == binding["content"]["artifact_ref"]
             and artifact["sha256"] == binding["content"]["sha256"]
             and artifact["byte_count"] == binding["content"]["byte_count"]
             and artifact["transfer"]["receipt_ref"] == ref
             and _same(artifact["transfer"]["requested_range"], args["byte_range"]), "acquisition_source_conflict")
    transport = binding["transport"]
    _require(type(transport.get("status")) is int and 100 <= transport["status"] <= 599
             and type(transport.get("body_complete")) is bool
             and type(transport.get("received_body_bytes")) is int
             and transport["received_body_bytes"] == artifact["byte_count"]
             and transport.get("effective_url") == call["url"] and transport.get("automatic_redirects") is False
             and type(transport.get("request")) is dict and transport["request"].get("method") == "GET"
             and transport["request"].get("url") == call["url"], "acquisition_transport_conflict")
    _require(not artifact["transfer"]["body_complete"] or transport["body_complete"], "acquisition_transport_conflict")
    complete, diagnostics = _bounded_capture(download_request(call, arguments=args), transport,
        artifact["byte_count"], _headers(transport, []))
    _require(not artifact["transfer"]["body_complete"] or complete, "acquisition_transport_conflict")
    _require(not diagnostics or receipt["status"] != "ok", "acquisition_transport_conflict")
    _require(transport["status"] in (200, 206) or receipt["status"] == "failed", "acquisition_status_conflict")
    return ref, receipt


def _representation(artifact):
    # A new metadata/association receipt does not make the same object's bytes
    # independent. Every original provenance field stays in the actual member.
    return {"object": {key: artifact["workspace_object"][key] for key in ("path", "uuid", "type")},
            "task_id": artifact["task_association"]["task_id"], "sha256": artifact["sha256"],
            "byte_count": artifact["byte_count"], "observed_range": artifact["transfer"]["observed_range"]}


def _missing(requirement, receipts):
    if not receipts:
        reason = "output_bytes_missing"
    elif all(row["status"] == "failed" for row in receipts):
        reason = "download_failed"
    elif all(row["status"] == "invalid" for row in receipts):
        reason = "download_invalid"
    elif any(not row["artifact"]["transfer"]["body_complete"]
             or row["artifact"]["transfer"]["object_complete"] == "no" for row in receipts):
        reason = "download_incomplete"
    else:
        reason = "object_completeness_unproven"
    return {"requirement_id": requirement["requirement_id"], "kind": "output_bytes", "role": requirement["role"],
            "source_refs": list(dict.fromkeys(row["artifact"]["source_ref"] for row in receipts)), "reason_code": reason}


def build_artifact_bundle(publication_inputs, *, original_task, acquisitions, input_bindings, query_bindings):
    """The bundle of the ordered, authenticated prior and current acquisitions of one handoff.

    Repeated refs must retain the same value. Only the current acquisition's hash equals the current inputs.
    Missing requirements use the closed reason set in ``_missing``. Scientific format validity and projection
    completeness belong to the separately bound scientific adapter, not to this builder.
    """
    inputs = _publication(publication_inputs)
    task = validate_contract("OriginalTask", original_task)
    _task(task, inputs["request"])
    _require(type(acquisitions) is list and type(input_bindings) is list and type(query_bindings) is list,
             "publication_dependency_conflict")
    _require(_same(input_bindings, inputs["request"]["input_bindings"]), "publication_input_bindings_conflict")
    artifacts, diagnostics, refs, seen, selected = [], [], [], {}, []
    current = None
    for index, row in enumerate(acquisitions):
        ref, receipt = _acquisition(row, inputs, task)
        if ref in seen:
            _require(_same(receipt, seen[ref]), "publication_dependency_conflict")
            diagnostics.append(_diagnostic("duplicate_acquisition_receipt", f"/acquisitions/{index}",
                                            severity="qualification", refs=[ref]))
        else:
            seen[ref] = receipt
            refs.append(ref)
        if ref not in inputs["prior_acquisition_receipt_refs"]:
            _require(current in (None, ref) and _same(receipt["snapshot"], inputs["current_snapshot"])
                     and receipt["publication_inputs_sha256"] == digest(inputs), "publication_dependency_conflict")
            current = ref
        else:
            _require(not _same(receipt["snapshot"], inputs["current_snapshot"]), "publication_dependency_conflict")
        if not receipt["requirement_ids"]:
            diagnostics.append(_diagnostic("unselected_artifact_retained", f"/acquisitions/{index}",
                                            severity="qualification", refs=[ref]))
            continue
        selected.append(receipt)
        artifact = receipt["artifact"]
        if receipt["status"] != "failed":
            for earlier in artifacts:
                if _same(_representation(earlier), _representation(artifact)):
                    diagnostics.append(_diagnostic("duplicate_artifact_representation", f"/acquisitions/{index}",
                        severity="qualification", refs=[earlier["transfer"]["receipt_ref"], ref]))
                    break
            artifacts.append(deepcopy(artifact))
            diagnostics.extend(_qualifications(artifact))
        if receipt["failure"] is not None:
            failure = receipt["failure"]
            diagnostics.append(_diagnostic(failure["code"], phase=failure["phase"], refs=[ref]))
    _require(refs == [*inputs["prior_acquisition_receipt_refs"], *([current] if current is not None else [])],
             "publication_dependency_conflict")
    missing = []
    for requirement in inputs["selector"]["requirements"]:
        candidates = [row for row in selected if requirement["requirement_id"] in row["requirement_ids"]]
        if requirement["required"] and not any(_usable(row) for row in candidates):
            missing.append(_missing(requirement, candidates))
    if not missing:
        status = "ok"
    elif (selected and all(row["status"] == "failed" for row in selected)
          and all(row["reason_code"] == "download_failed" for row in missing)):
        status = "failed"
    elif (selected and all(row["status"] == "invalid" for row in selected)
          and all(row["reason_code"] == "download_invalid" for row in missing)):
        status = "invalid"
    else:
        status = "partial"
    bundle = {"version": "bvbrc_appservice_artifact_bundle_v1", "original_task": task,
        "artifacts": artifacts, "input_bindings": input_bindings, "query_bindings": query_bindings,
        "supplied_scientific_metadata": inputs["supplied_evidence"], "acquisition_receipt_refs": refs,
        "requested_selector_sha256": digest(inputs["selector"]), "status": status,
        "missing_requirements": missing, "diagnostics": _unique(diagnostics)}
    if "supplied_contents" in inputs["selector"]:
        bundle["supplied_contents"] = deepcopy(inputs["selector"]["supplied_contents"])
    return validate_bundle(bundle)


def _bundle_contents(bundle):
    """Every ``ContentBinding`` the bundle names whose bytes an adapter reads."""
    rows = [{'source_ref': member['source_ref'], 'artifact_field': 'artifact_ref',
             'artifact_ref': member['raw_artifact_ref'], 'sha256': member['sha256'], 'byte_count': member['byte_count']}
            for member in bundle['artifacts']]
    rows += bundle.get('supplied_contents', [])
    rows += [binding['content'] for binding in bundle['input_bindings'] if binding['content'] is not None]
    rows += [evidence['content'] for evidence in bundle['supplied_scientific_metadata']]
    return rows


# -- publication on the shared Store -----------------------------------------------------------------------------
class AppServicePublication:
    """The ``publication_callback`` of the results binding's AppService services, over the run's shared Store."""

    def __init__(self, store):
        self._store = store

    def _content(self, value, provider, parents):
        """Retain one adapter value as a Store source; its ``ContentBinding``."""
        raw = canonical(value).encode('utf-8')
        artifact = self._store.artifact(raw, 'application/json')
        reference = self._store.put('source', {
            'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': None,
            'request_ref': None, 'version': None, 'retrieved_at': None,
            'parent_source_refs': list(parents)}, origin='tool')['id']
        return {'source_ref': reference, 'artifact_field': 'artifact_ref', 'artifact_ref': artifact,
                'sha256': digest(value), 'byte_count': len(raw)}

    def __call__(self, snapshot, *, publication_inputs, operation_key, scope, acquisition_receipt_ref, adapter):
        store = self._store
        inputs = validate_contract('PublicationInputs', publication_inputs)
        scope = store.validate_scope(plain(scope))
        handoff = read_receipt(store, inputs['original_handoff_ref'], 'TaskHandoff')
        holder = ResultInputs(store, owner=handoff['original_job_owner'],
                              resource_id=handoff['original_task']['resource_id'], request=inputs['request'],
                              handoff_ref=inputs['original_handoff_ref'], selector=inputs['selector'], held={})
        task = holder.original_task()
        refs = [*inputs['prior_acquisition_receipt_refs'], acquisition_receipt_ref]
        acquisitions = [{'receipt_ref': ref, 'receipt': read_receipt(store, ref, 'AcquisitionReceipt')} for ref in refs]
        current = acquisitions[-1]['receipt']
        _require(current['origin']['operation_key'] == operation_key and _usable(current)
                 and current['snapshot']['content']['sha256'] == snapshot.sha256, 'publication_acquisition_not_usable')
        bundle = build_artifact_bundle(inputs, original_task=task, acquisitions=acquisitions,
                                       input_bindings=deepcopy(inputs['request']['input_bindings']), query_bindings=[])
        selection = inputs['adapter']
        _require((selection is None) == (adapter is None), 'publication_adapter_conflict')
        with store.transaction():
            adapter_result, saved_refs = None, []
            if selection is not None:
                raw = {}
                for binding in _bundle_contents(bundle):
                    raw[binding['artifact_ref']] = holder.content_bytes(binding)
                result = adapter.consume_bundle(
                    bundle, artifact_bytes=raw,
                    supplied_values=holder.supplied_values(bundle['supplied_scientific_metadata']),
                    requested_form=deepcopy(inputs['selector']['requested_schema']),
                    parameters=deepcopy(selection['parameters']))
                result = json.loads(canonical(result))
                _require(result['adapter_id'] == selection['adapter_id']
                         and result['adapter_version'] == selection['adapter_version'], 'publication_adapter_conflict')
                contents = {}
                for name, provider in (('sheet', SHEET_PROVIDER), ('components', COMPONENTS_PROVIDER)):
                    contents[name + '_content'] = None if result[name] is None else self._content(
                        result[name], provider, refs)
                    if result[name] is not None:
                        saved_refs.append(contents[name + '_content']['source_ref'])
                adapter_result = validate_contract('AdapterResult', {
                    **{key: result[key] for key in _ADAPTER_FIELDS}, **contents})
            envelope = {'version': RESULT_VERSION, 'run_id': current['origin']['run_id'],
                        'episode_id': current['origin']['episode_id'], 'operation_key': operation_key,
                        'scope': scope, 'assignment': {'original_handoff_ref': inputs['original_handoff_ref'],
                                                       'selector': inputs['selector']},
                        'publication_inputs': inputs, 'origin': current['origin'], 'adapter_result': adapter_result,
                        'content_record_refs': saved_refs}
            artifact = store.artifact(canonical(bundle), 'application/json')
            text = store.artifact(canonical(envelope), 'application/json')
            reference = store.put('source', {
                'provider': PUBLICATION_PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact,
                'text_ref': text, 'request_ref': None, 'version': RESULT_VERSION, 'retrieved_at': None,
                'parent_source_refs': [*refs, *saved_refs]}, origin='tool')['id']
        return {'status': bundle['status'], 'publication_ref': reference, 'record_refs': [reference, *saved_refs],
                'adapter_status': None if adapter_result is None else adapter_result['status']}


# -- reading a publication back -----------------------------------------------------------------------------------
def _canonical_json(store, artifact_ref, code):
    raw = store.get_artifact(artifact_ref)
    value = json.loads(raw)
    _require(raw == canonical(value).encode('utf-8'), code)
    return value


def read_publication(store, reference):
    """The ``bvbrc_appservice_acquired_bundle_v1`` body of one publication record on the shared Store."""
    record = store.get(reference)
    _require(record.get('record_type') == 'source' and record.get('provider') == PUBLICATION_PROVIDER
             and record.get('version') == RESULT_VERSION and record.get('text_ref') is not None,
             'publication_record_invalid')
    bundle = validate_bundle(_canonical_json(store, record['artifact_ref'], 'publication_bundle_not_canonical'))
    envelope = _canonical_json(store, record['text_ref'], 'publication_envelope_not_canonical')
    _require(type(envelope) is dict and envelope.get('version') == RESULT_VERSION and set(envelope) == {
        'version', 'run_id', 'episode_id', 'operation_key', 'scope', 'assignment', 'publication_inputs', 'origin',
        'adapter_result', 'content_record_refs'}, 'publication_envelope_invalid')
    inputs = validate_contract('PublicationInputs', envelope['publication_inputs'])
    origin = validate_contract('ReceiptOrigin', envelope['origin'])
    saved = envelope['adapter_result']
    saved = None if saved is None else validate_contract('AdapterResult', saved)
    _require(bundle['requested_selector_sha256'] == digest(inputs['selector'])
             and _same(envelope['assignment'], {'original_handoff_ref': inputs['original_handoff_ref'],
                                                'selector': inputs['selector']})
             and origin['operation_key'] == envelope['operation_key'], 'publication_envelope_invalid')
    raw = store.get_artifact(record['artifact_ref'])
    content = {'source_ref': reference, 'artifact_field': 'artifact_ref', 'artifact_ref': record['artifact_ref'],
               'sha256': digest(bundle), 'byte_count': len(raw)}
    return {'version': RESULT_VERSION, 'source_ref': reference, 'reference': reference,
            'run_id': envelope['run_id'], 'episode_id': envelope['episode_id'], 'scope': envelope['scope'],
            'assignment': envelope['assignment'], 'publication_inputs': inputs,
            'publication': {'bundle_content': content, 'result_record_refs': [reference], 'adapter_result': saved,
                            'origin': origin},
            'record_refs': [reference, *envelope['content_record_refs']], 'bundle': bundle}


def read_adapter_contents(store, body):
    """The saved adapter sheet and components a publication body binds (each None when unbound)."""
    saved = body['publication']['adapter_result']
    _require(saved is not None, 'publication_adapter_result_absent')
    values = []
    for name in ('sheet', 'components'):
        binding = saved[name + '_content']
        if binding is None:
            values.append(None)
            continue
        _require(binding['source_ref'] in body['record_refs'], 'publication_content_not_bound')
        record = store.get(binding['source_ref'])
        _require(record.get('record_type') == 'source'
                 and record.get(binding['artifact_field']) == binding['artifact_ref'], 'publication_content_conflict')
        value = _canonical_json(store, binding['artifact_ref'], 'publication_content_not_canonical')
        _require(digest(value) == binding['sha256'] and len(canonical(value).encode('utf-8')) == binding['byte_count'],
                 'publication_content_conflict')
        values.append(value)
    return tuple(values)


__all__ = ['AppServicePublication', 'COMPONENTS_PROVIDER', 'PUBLICATION_PROVIDER', 'RESULT_VERSION', 'SHEET_PROVIDER',
           'build_artifact_bundle', 'read_adapter_contents', 'read_publication']
