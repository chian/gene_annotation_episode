"""Immutable received work definitions for the existing shared HPC episode.

Scientific tools may freeze new operands without changing a running binding's
static configuration. Only a host-issued grant, for the original scope and
configured resource, can supply such a commission. This adds no scheduler.
"""
from __future__ import annotations

import json

from .domain import canonical
from .hpc_campaign import validate_commission
from .hpc_queue import digest


PROVIDER = 'host.hpc.commission'
VERSION = 'hpc_received_commission_v1'


def publish(store, commission, *, scope, resources):
    scope = store.validate_scope(scope)
    body = {'version': VERSION, 'scope': scope,
            'commission': validate_commission(commission, resources),
            'resource_sha256': digest(resources[commission['resource_id']])}
    store.db.execute('CREATE TABLE IF NOT EXISTS hpc_commission_sources '
                     '(source_ref TEXT PRIMARY KEY, body TEXT NOT NULL)')
    artifact = store.artifact(canonical(body), 'application/json')
    reference = store.put('source', {'provider': PROVIDER, 'accession': digest(body), 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': VERSION,
        'retrieved_at': None, 'operand_refs': scope['subject_refs']}, origin='tool')['id']
    store.db.execute('INSERT OR IGNORE INTO hpc_commission_sources VALUES(?,?)', (reference, canonical(body)))
    return reference


def read(store, reference, *, scope, resources):
    record = store.get(reference)
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE name='hpc_commission_sources'").fetchone()
    row = store.db.execute('SELECT body FROM hpc_commission_sources WHERE source_ref=?',
                           (reference,)).fetchone() if exists else None
    if (record['record_type'] != 'source' or record.get('provider') != PROVIDER
            or record['origin'] != 'tool' or record.get('version') != VERSION or row is None):
        raise ValueError('original_host_hpc_commission_grant_required')
    body = json.loads(row[0])
    if json.loads(store.get_artifact(record['artifact_ref'])) != body or body['scope'] != store.validate_scope(scope):
        raise ValueError('received_hpc_commission_scope_or_bytes_conflict')
    commission = validate_commission(body['commission'], resources)
    if body['resource_sha256'] != digest(resources[commission['resource_id']]):
        raise ValueError('received_hpc_commission_resource_changed')
    return commission
