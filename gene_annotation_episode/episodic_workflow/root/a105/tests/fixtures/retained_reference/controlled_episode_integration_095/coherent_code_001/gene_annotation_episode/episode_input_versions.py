"""Read C1 record/byte identities without changing resource input constraints.

C9 resource rows pin revisions and sequence bytes. They remain in the resource
assignment; this boundary independently pins their semantic records and byte
artifacts for commission production and worker reconstruction.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib

from method_loop.durable import content_digest

from .domain import ContractError


def _reference(value):
    if not isinstance(value, str) or not value:
        raise ValueError('commission_input_reference_must_be_nonempty_text')
    return value


def _resource_row(value):
    if (not isinstance(value, Mapping)
            or set(value) != {'reference', 'version', 'content_sha256'}):
        raise ValueError('invalid_resource_input_version_fields')
    _reference(value['reference'])
    version, digest = value['version'], value['content_sha256']
    if version is not None and (not isinstance(version, str) or not version):
        raise ValueError('invalid_resource_input_version')
    if digest is not None and (not isinstance(digest, str) or len(digest) != 64
            or any(character not in '0123456789abcdef' for character in digest)):
        raise ValueError('invalid_resource_input_digest')
    return value['reference']


def pin_commission_inputs(store, references, *, resource_input_versions=()):
    """Return ordered, distinct C1 pins from actual Store records and bytes.

    Resource rows supply references only: their revision/byte expectations are
    neither copied into record pins nor refreshed. Resource execution retains
    responsibility for checking those original constraints.
    """
    if not isinstance(references, (list, tuple)):
        raise ValueError('commission_input_references_must_be_array')
    if not isinstance(resource_input_versions, (list, tuple)):
        raise ValueError('resource_input_versions_must_be_array')
    references = [_reference(reference) for reference in references]
    resource_references = [_resource_row(row) for row in resource_input_versions]
    pins, seen = [], set()

    with store.read_snapshot():
        def add(reference):
            if reference in seen:
                return
            record = store.get(reference)
            version = record.get('version')
            digest = (hashlib.sha256(store.get_artifact(reference)).hexdigest()
                if record['record_type'] == 'artifact' else content_digest(record))
            pins.append({'reference': reference,
                'version': None if version is None else str(version),
                'content_sha256': digest})
            seen.add(reference)

        for reference in references:
            add(reference)
        for reference in resource_references:
            add(reference)
            record = store.get(reference)
            artifact = record.get('sequence_ref')
            if record['record_type'] != 'artifact' and artifact is not None:
                artifact = _reference(artifact)
                if store.get(artifact)['record_type'] != 'artifact':
                    raise ContractError('resource_input_sequence_ref_must_be_artifact')
                add(artifact)
    return pins


__all__ = ['pin_commission_inputs']
