"""Strict saved private-descriptor admission before reconstructing owners."""
from collections.abc import Mapping
import json

from .method_loop.durable import DurableExecutionError, canonical


def _failure(code, reference):
    return DurableExecutionError(code, affected_refs=[reference])


def _json_object(value, reference):
    if not isinstance(value, Mapping):
        raise _failure('unavailable_binding', reference)
    try:
        return json.loads(canonical(value))
    except (ValueError, TypeError, OverflowError) as error:
        raise _failure('unavailable_binding', reference) from error


def _same_record(actual, saved, reference):
    if canonical(actual) != canonical(saved):
        raise _failure('identity_conflict', reference)


def admit_descriptors(descriptors, catalog):
    """Validate every saved identity and counterpart before construction."""
    if not isinstance(descriptors, (tuple, list)):
        raise _failure('unavailable_binding', 'episode_bindings')
    admitted, seen = [], set()
    for value in descriptors:
        record = _json_object(value, 'episode_bindings')
        name = record.get('binding_id')
        reference = name if isinstance(name, str) and name else 'episode_bindings'
        if not isinstance(name, str) or name not in catalog:
            raise _failure('unavailable_binding', reference)
        if name in seen:
            raise _failure('identity_conflict', reference)
        seen.add(name)
        declaration = catalog[name]
        fields = {'version', 'binding_id', 'configuration'}
        if declaration['fingerprinted']:
            fields.add('implementation_sha256')
        if set(record) != fields or record['version'] != declaration['version']:
            raise _failure('unavailable_binding', reference)
        configuration = record['configuration']
        required, optional = set(declaration['required']), set(declaration['optional'])
        if (not isinstance(configuration, dict) or not required <= configuration.keys()
                or configuration.keys() - required - optional):
            raise _failure('unavailable_binding', reference)
        if declaration['fingerprinted']:
            fingerprint = record['implementation_sha256']
            if (type(fingerprint) is not str or len(fingerprint) != 64
                    or any(character not in '0123456789abcdef' for character in fingerprint)):
                raise _failure('unavailable_binding', reference)
        admitted.append(record)
    for record in admitted:
        name = record['binding_id']
        parent = catalog[name]['parent']
        if parent != 'legacy_annotation' and parent not in seen:
            raise _failure('unavailable_binding', name + ':commissioning_parent')
    return admitted


def verify_owner(binding, record, declaration, *, axis_package):
    """The executing counterpart and every persisted operand must match."""
    name = record['binding_id']
    if (type(binding).__module__ != axis_package + '.' + name.replace('/', '.') + '.episode'
            or type(binding).__name__ != declaration['owner_class']
            or binding.binding_path != name
            or binding.commissioning_parent != declaration['parent']
            or binding.roles != tuple(declaration['roles'])
            or binding.entry_roles != tuple(declaration['entry_roles'])):
        raise _failure('identity_conflict', name)
    _same_record(binding.as_record(), record, name)
