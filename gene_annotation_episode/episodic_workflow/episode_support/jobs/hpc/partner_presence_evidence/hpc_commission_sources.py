"""Immutable received work definitions for the existing shared HPC episode.

Scientific tools may freeze new operands without changing a running binding's
static configuration. Only a host-issued grant, for the original scope and
configured resource, can supply such a commission. This adds no scheduler.
"""
from __future__ import annotations

import json

from episode_runtime import TableDeclaration

from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_campaign import validate_commission
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.hpc_queue import digest


PROVIDER = 'host.hpc.commission'
VERSION = 'hpc_received_commission_v1'
COMMISSION_SOURCES = TableDeclaration(name='hpc_commission_sources', columns=('source_ref', 'body'), key=('source_ref',),
                                      record_refs=('source_ref',))


def publish(store, commission, *, scope, resources):
    """Write the commission as a source record and its row; both are the Episode's own."""
    scope = store.validate_scope(scope)
    body = {'version': VERSION, 'scope': scope,
            'commission': validate_commission(commission, resources),
            'resource_sha256': digest(resources[commission['resource_id']])}
    artifact = store.artifact(canonical(body), 'application/json')
    reference = store.put('source', {'provider': PROVIDER, 'accession': digest(body), 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': VERSION,
        'retrieved_at': None, 'operand_refs': scope['subject_refs']}, origin='tool')['id']
    store.table(COMMISSION_SOURCES).put({'source_ref': reference, 'body': body})
    return reference


def read(store, reference, *, scope, resources):
    record = store.get(reference)
    rows = store.table(COMMISSION_SOURCES).select({'source_ref': reference})
    if (record['record_type'] != 'source' or record.get('provider') != PROVIDER
            or record['origin'] != 'tool' or record.get('version') != VERSION or not rows):
        raise ValueError('original_host_hpc_commission_grant_required')
    body = rows[0]['body']
    if json.loads(store.get_artifact(record['artifact_ref'])) != body or body['scope'] != store.validate_scope(scope):
        raise ValueError('received_hpc_commission_scope_or_bytes_conflict')
    commission = validate_commission(body['commission'], resources)
    if body['resource_sha256'] != digest(resources[commission['resource_id']]):
        raise ValueError('received_hpc_commission_resource_changed')
    return commission
