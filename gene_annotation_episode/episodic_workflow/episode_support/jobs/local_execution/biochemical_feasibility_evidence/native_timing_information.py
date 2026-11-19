"""Host-owned native execution receipts: publish one and read its measurement back."""
import json

from episode_runtime import TableDeclaration
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.execution_recording import NativeMeasurement

NATIVE_MEASUREMENTS = TableDeclaration(name='native_measurements',
                                       columns=('operation', 'operands', 'measurement_artifact_ref'),
                                       key=('measurement_artifact_ref',), record_refs=('measurement_artifact_ref',))


def record_native_measurement(store, measurement, *, operation, operands):
    """Publish host-owned provenance; neither work nor a statistical write."""
    from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import canonical
    if type(measurement) is not NativeMeasurement:
        raise TypeError('typed_native_measurement_required')
    with store.transaction():
        artifact = store.artifact(canonical(measurement.as_record()), 'application/json')
        return store.table(NATIVE_MEASUREMENTS).put({
            'operation': operation, 'operands': operands, 'measurement_artifact_ref': artifact})['id']


def read_measurement(store, reference):
    row = store.table(NATIVE_MEASUREMENTS).get(reference)
    return NativeMeasurement.from_record(json.loads(store.get_artifact(row['measurement_artifact_ref'])))
