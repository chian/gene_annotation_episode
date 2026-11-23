"""The calls the A102 derived-publication test makes inside the probe episode."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence import credit
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.scoring import A102ScoringUnavailable
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.derived_publications import DERIVED_PUBLICATIONS
from gene_annotation_episode.episodic_workflow.episode_support.tools.structural_homology_evidence.evidence_operations import VERSION


def publish_and_read(ctx, provider):
    """A native sheet the Episode publishes with its row of permitted use, then read back for credit."""
    store = ctx.store
    body = {'schema': 'a102_probe_sheet', 'target_ref': 'input_probe', 'features': [1, 2, 3]}
    artifact = store.artifact(json.dumps(body, sort_keys=True), 'application/json')
    source = store.put('source', {'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact,
                                  'text_ref': artifact, 'request_ref': None, 'version': VERSION, 'retrieved_at': None},
                       origin='tool')['id']
    store.table(DERIVED_PUBLICATIONS).put({'source_ref': source, 'body': body, 'permitted_use': 'a102_scoring'})
    unregistered = store.put('source', {'provider': provider, 'accession': 'unregistered', 'uri': None,
                                        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                                        'version': VERSION, 'retrieved_at': None}, origin='tool')['id']
    return {'read': credit._received_task_sheet(store, source, {source}, provider) == body,
            'not_received': credit._received_task_sheet(store, source, set(), provider),
            'other_provider': credit._received_task_sheet(store, source, {source}, 'native.a102.contrast'),
            'unregistered': _refused(lambda: credit._received_task_sheet(store, unregistered, {unregistered}, provider))}


def _refused(call):
    try:
        call()
    except A102ScoringUnavailable as error:
        return str(error)
