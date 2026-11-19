"""The publication step of the A106 results episode: an acquired AppService bundle as records on the shared Store.

After a download unit retains a usable ``AcquisitionReceipt``, the episode publishes the handoff's acquisitions
through ``BVBRCAppServiceService.publish``; this module is that service's ``publication_callback``
(``AppServicePublication``, built by the results binding over the run's shared Store). It

- re-reads and authenticates the original task from the handoff receipt (``ResultInputs.original_task``) and
  every ``AcquisitionReceipt`` the ``PublicationInputs`` name (the prior ones and the current one);
- builds the ``bvbrc_appservice_artifact_bundle_v1`` bundle of those acquisitions (``build_artifact_bundle``).
  The request carries no query rows, so this publication binds none (``query_bindings`` is empty); an adapter
  that requires them reports them missing (``bvbrc_appservice_bundle_values.build_artifact_bundle``);
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

from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.bvbrc_appservice_bundle_values import _require, _usable, build_artifact_bundle
from gene_annotation_episode.episodic_workflow.episode_support.forms.service_calls.perturbation_evidence.bvbrc_appservice_contracts import _same, validate_contract
from gene_annotation_episode.episodic_workflow.episode_support.readers.service_calls.perturbation_evidence.bvbrc_appservice_readers import validate_bundle
from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.bvbrc_application_facts import RESULT_VERSION
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.held_inputs import read_receipt
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.result_inputs import ResultInputs

PUBLICATION_PROVIDER = 'bvbrc_appservice.publication'
SHEET_PROVIDER = 'bvbrc_appservice.adapter_sheet'
COMPONENTS_PROVIDER = 'bvbrc_appservice.adapter_components'
_ADAPTER_FIELDS = ('adapter_id', 'adapter_version', 'status', 'facts', 'missing_requirements', 'diagnostics')


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
           'read_adapter_contents', 'read_publication']
