from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, identity

def immutable_record(record):
    payload = {k: v for k, v in record.items() if k not in {'id', 'record_type', 'origin'}}
    kind = record['record_type']
    if kind == 'input':
        expected = identity('input', payload)
        if record['origin'] != 'caller':
            raise ContractError('site_record_identity_conflict')
    elif kind == 'read_subject':
        from gene_annotation_episode.episodic_workflow.root.a110.library_targets import read_ref
        expected = read_ref(record['library_ref'], record['member_ref'])
        if record['origin'] != 'caller':
            raise ContractError('site_record_identity_conflict')
    else:
        expected = identity(kind, {'origin': record['origin'], 'record': payload})
    if record['id'] != expected:
        raise ContractError('site_record_identity_conflict')
