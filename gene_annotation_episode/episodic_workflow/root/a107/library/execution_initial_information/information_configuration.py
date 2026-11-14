"""Own-axis, caller-declared construction for initial information only."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from ...communication import plain
from ...execution_service_setup import ExecutionServiceFactory
from .factory_readers import construct_factory_information_readers
from .information_authority import OriginalInformationSetup, InitialInformationCatalog

VERSION = 'execution_initial_information_configuration_v1'


def _copy(value):
    return json.loads(json.dumps(plain(value), allow_nan=False))


class InitialInformationConfiguration:
    """Explicit original factory setups, independent of episode availability.

    `global_authority` means the named original factory's established global
    context. It is not inferred from the number or equality of registered
    children. An explicit multi-factory setup instead names each recipient.
    """
    def __init__(self, authorities, recipients=(), *, global_authority=None):
        if not isinstance(authorities, (tuple, list)) or not authorities:
            raise TypeError('initial_information_factory_authorities_required')
        self.authorities = []
        seen = set()
        for identity, factory in authorities:
            if (not isinstance(identity, str) or not identity or identity in seen
                    or type(factory) is not ExecutionServiceFactory):
                raise ValueError('initial_information_factory_authority_invalid')
            seen.add(identity)
            self.authorities.append((identity, factory))
        self.recipients = _copy(recipients)
        if not isinstance(self.recipients, list):
            raise TypeError('initial_information_recipient_declarations_required')
        if global_authority is not None and (global_authority not in seen
                or len(seen) != 1 or self.recipients):
            raise ValueError('initial_information_global_factory_ambiguous')
        self.global_authority = global_authority
        self._original_record = self._record()

    def _record(self):
        return {'version': VERSION, 'axis': 'A107',
            'authorities': [{'authority_id': identity, 'factory_definition': _copy(factory.as_record())}
                for identity, factory in self.authorities],
            'recipients': deepcopy(self.recipients), 'global_authority': self.global_authority}

    def as_record(self):
        result = self._record()
        if result != self._original_record:
            raise ValueError('initial_information_factory_configuration_changed')
        return result

    @classmethod
    def from_record(cls, record):
        value = _copy(record)
        if (not isinstance(value, dict) or set(value) != {
                'version', 'axis', 'authorities', 'recipients', 'global_authority'}
                or value['version'] != VERSION or value['axis'] != 'A107'
                or not isinstance(value['authorities'], list)):
            raise ValueError('initial_information_original_configuration_required')
        authorities = []
        for row in value['authorities']:
            if not isinstance(row, dict) or set(row) != {'authority_id', 'factory_definition'}:
                raise ValueError('initial_information_factory_authority_invalid')
            factory = ExecutionServiceFactory.from_record(row['factory_definition'])
            if _copy(factory.as_record()) != row['factory_definition']:
                raise ValueError('initial_information_factory_configuration_changed')
            authorities.append((row['authority_id'], factory))
        result = cls(authorities, value['recipients'], global_authority=value['global_authority'])
        if result.as_record() != value:
            raise ValueError('initial_information_original_configuration_required')
        return result

    @classmethod
    def original_global_factory(cls, factory, *, authority_id='original-global-execution-factory'):
        return cls([(authority_id, factory)], global_authority=authority_id)

    def construct(self, *, store, run_id, directory, tool_registry, services):
        self.as_record()
        setups = []
        for identity, factory in self.authorities:
            readers = construct_factory_information_readers(factory, store=store,
                run_id=run_id, directory=directory, tool_registry=tool_registry, services=services)
            setups.append(OriginalInformationSetup.capture(identity, factory, readers))
        return InitialInformationCatalog(setups, self.recipients, global_authority=self.global_authority)
