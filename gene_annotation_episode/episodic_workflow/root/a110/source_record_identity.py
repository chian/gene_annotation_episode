"""A110 immutable source-record identity used by received File admission."""
from .domain import ContractError, identity


def immutable_record(record):
    payload = {k: v for k, v in record.items() if k not in {'id', 'record_type', 'origin'}}
    kind = record['record_type']
    if kind == 'input':
        # materials.create_problem / library_targets.bind hash the original
        # input payload directly, before adding caller origin metadata.
        expected = identity('input', payload)
        if record['origin'] != 'caller':
            raise ContractError('site_record_identity_conflict')
    elif kind == 'read_subject':
        # A read subject is resolved from fixed library membership, rather than
        # stored as an independently hashed scientific record.
        from .library_targets import read_ref
        expected = read_ref(record['library_ref'], record['member_ref'])
        if record['origin'] != 'caller':
            raise ContractError('site_record_identity_conflict')
    else:
        expected = identity(kind, {'origin': record['origin'], 'record': payload})
    if record['id'] != expected:
        raise ContractError('site_record_identity_conflict')

