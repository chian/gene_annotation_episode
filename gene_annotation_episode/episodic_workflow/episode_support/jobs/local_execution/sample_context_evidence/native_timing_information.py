"""Publish and read host-owned native execution receipts in the Store.

No native work, shared-history access, child-private action or continuation
decision occurs here.
"""
import json

from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.execution_recording import NativeMeasurement


def record_native_measurement(store, measurement, *, operation, operands):
    """Publish host-owned provenance; neither work nor a statistical write."""
    from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import canonical
    if type(measurement) is not NativeMeasurement:
        raise TypeError('typed_native_measurement_required')
    with store.transaction():
        artifact = store.artifact(canonical(measurement.as_record()), 'application/json')
        return store.put('native_execution', {
            'representation': 'native_execution_receipt_v2', 'operation': operation,
            'measurement_artifact_ref': artifact, 'operands': operands}, origin='tool')['id']


def read_measurement(store, reference):
    record = store._require(reference, {'native_execution'})
    return NativeMeasurement.from_record(json.loads(store.get_artifact(record['measurement_artifact_ref'])))
