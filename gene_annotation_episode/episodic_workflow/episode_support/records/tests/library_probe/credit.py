"""Credit: one per plan step; a step that published a measurement earns it only when the read-only reader
finds the measurement received (the library function ``received_measurement`` run on ``records``)."""
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.publication import (
    received_measurement)


def credit(summary, records):
    total = 0.0
    for outcome in summary['outcomes'][:summary['steps']]:
        done = outcome['outcome']
        if isinstance(done, dict) and 'measurement_ref' in done:
            received_measurement(records, done['measurement_ref'])
        total += 1.0
    return total
