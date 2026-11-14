"""Root selection identities alongside unchanged private binding descriptors.

Candidate interface only: this index does not authenticate a request, select an
axis, construct a binding, or implement structural-path traversal. The caller
must validate the original commission and saved request before restoring its
selection. Returned objects are the actual registered bindings, never wrappers.
"""
from __future__ import annotations

import json


SELECTION_VERSION = 'root_private_binding_selection_v1'


def _json(value):
    """An exact finite JSON tree; reject key coercion and arbitrary objects."""
    def check(item):
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise TypeError('root_binding_string_keys_required')
            for child in item.values():
                check(child)
        elif type(item) is list:
            for child in item:
                check(child)
        elif item is not None and type(item) not in (str, bool, int, float):
            raise TypeError('root_binding_json_values_required')
    check(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def _name(value, label):
    if type(value) is not str or not value:
        raise ValueError('root_binding_' + label + '_required')
    return value


def _path(value):
    _name(value, 'path')
    if any(not part or part in {'.', '..'} for part in value.split('/')):
        raise ValueError('root_binding_path_invalid')
    return value


class PrivateBindingOwners:
    """Index explicitly supplied (root owner, original private path) entries.

    ``owners`` comes from the root's literal commissioned-owner catalogue, not
    from a private descriptor, model response, module name, or role. This helper
    does not replace EpisodeBindingRegistry's complete protocol/edge validation.
    Legacy bindings with no private path stay with that original registry.
    """

    def __init__(self, *, owners, entries):
        if type(owners) is not tuple or not owners:
            raise ValueError('root_binding_declared_owners_required')
        for owner in owners:
            _name(owner, 'owner')
        if len(set(owners)) != len(owners):
            raise ValueError('root_binding_duplicate_owner')
        allowed = frozenset(owners)
        by_key, by_path, by_object, saved = {}, {}, {}, []
        for owner, binding in entries:
            _name(owner, 'owner')
            if owner not in allowed:
                raise ValueError('root_binding_owner_not_declared:' + owner)
            path = _path(getattr(binding, 'binding_path', None))
            key = owner, path
            if key in by_key:
                raise ValueError('root_binding_duplicate_owner_path:' + owner + ':' + path)
            if id(binding) in by_object:
                raise ValueError('root_binding_object_has_multiple_registrations')
            descriptor = binding.as_record()
            if type(descriptor) is not dict:
                raise TypeError('root_binding_descriptor_object_required')
            encoded = _json(descriptor)
            record = {'version': SELECTION_VERSION, 'owner': owner,
                      'binding_path': path, 'descriptor': json.loads(encoded)}
            by_key[key] = binding, encoded
            by_path.setdefault(path, []).append(key)
            by_object[id(binding)] = key
            saved.append(record)
        self._by_key = by_key
        self._by_path = by_path
        self._by_object = by_object
        self._saved = _json(saved)

    def resolve(self, path, *, owner=None):
        """Ownerless historical lookup succeeds only for exactly one entry."""
        path = _path(path)
        if owner is None:
            matches = self._by_path.get(path, ())
            if len(matches) != 1:
                raise LookupError('root_binding_path_requires_unique_owner:' + path)
            key = matches[0]
        else:
            key = _name(owner, 'owner'), path
        try:
            binding, recorded = self._by_key[key]
        except KeyError as error:
            raise LookupError('root_binding_owner_path_not_registered:' + str(key)) from error
        if getattr(binding, 'binding_path', None) != path or _json(binding.as_record()) != recorded:
            raise ValueError('root_binding_registered_descriptor_changed')
        return binding

    def selection(self, owner, path):
        binding = self.resolve(path, owner=owner)
        key = self._by_object[id(binding)]
        return {'version': SELECTION_VERSION, 'owner': key[0],
                'binding_path': key[1], 'descriptor': json.loads(self._by_key[key][1])}

    def restore_selection(self, record, *, expected_owner=None, expected_path=None):
        """Compare an already authenticated saved selection to the live owner.

        This is structural/descriptor validation, not Journal authentication.
        The caller must also check the original run, episode, parent, request,
        selected annotation axis, assignment, scope and commissioning identity.
        """
        if (type(record) is not dict or set(record) !=
                {'version', 'owner', 'binding_path', 'descriptor'} or
                record['version'] != SELECTION_VERSION):
            raise ValueError('root_binding_selection_invalid')
        _json(record)
        owner, path = record['owner'], record['binding_path']
        if expected_owner is not None and owner != expected_owner:
            raise ValueError('root_binding_selected_owner_conflict')
        if expected_path is not None and path != expected_path:
            raise ValueError('root_binding_selected_path_conflict')
        actual = self.selection(owner, path)
        if _json(record) != _json(actual):
            raise ValueError('root_binding_selected_descriptor_conflict')
        return self.resolve(path, owner=owner)

    def as_record(self):
        """Separate root metadata; never replace the private descriptor list."""
        for owner, path in self._by_key:
            self.resolve(path, owner=owner)
        return json.loads(self._saved)

    def validate_saved(self, records):
        """Exact owner/path/descriptor list, including order and membership."""
        if _json(records) != _json(self.as_record()):
            raise ValueError('root_binding_saved_owner_map_conflict')


__all__ = ['PrivateBindingOwners', 'SELECTION_VERSION']
