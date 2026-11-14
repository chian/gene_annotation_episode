"""Candidate: explicit A110 factory-owned initial-information custody.

This file is a source-only proposal. It is not imported by application code.
The renderer receives authenticated reader ports from the exact setup event;
neither a saved role nor equal callback values selects a reader authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from collections.abc import Mapping
import json

from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.execution_service_setup import ExecutionServiceFactory

AXIS = 'A110'
VERSION = 'execution_initial_information_authority_v1'
CATALOG_VERSION = 'execution_initial_information_catalog_v2'
FACTORY_ID = 'gene_annotation_episode.episodic_workflow.root.a110.execution_service_setup.ExecutionServiceFactory'
ANNOTATION_RECIPIENT = '@annotation'


def _copy(value):
    return json.loads(json.dumps(plain(value), sort_keys=True, allow_nan=False))


def _name(value, code):
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(code)
    return value


@dataclass(frozen=True)
class OriginalInformationSetup:
    """One concrete setup event, independent of any registered episode role.

    `factory` is the actual own-axis configuration object used by construction.
    `readers` is the concrete original reader bundle created by that setup, not
    a provider binding selected by walking the episode tree. Bundle construction
    is the separate, audited factory-reader extraction described in the handoff.
    The object-identity check below prevents pooling two separate setup events
    merely because their configuration or rendered values happen to be equal.
    """
    authority_id: str
    factory: ExecutionServiceFactory
    readers: object
    factory_record: dict
    reader_record: dict

    @classmethod
    def capture(cls, authority_id, factory, readers):
        _name(authority_id, 'initial_information_authority_id_required')
        if type(factory) is not ExecutionServiceFactory:
            raise TypeError('initial_information_actual_axis_factory_required')
        # The literal private bundle type is deliberately not loaded from a
        # descriptor. It is supplied by the reviewed reader-construction file.
        from .information_readers import FactoryInformationReaders
        if type(readers) is not FactoryInformationReaders or readers.factory is not factory:
            raise TypeError('initial_information_original_reader_setup_required')
        record = _copy(factory.as_record())
        readers.validate_original_setup(record)
        return cls(authority_id, factory, readers, record, _copy(readers.as_record()))

    def check(self):
        if _copy(self.factory.as_record()) != self.factory_record:
            raise ValueError('initial_information_factory_changed')
        self.readers.validate_original_setup(self.factory_record)
        if _copy(self.readers.as_record()) != self.reader_record:
            raise ValueError('initial_information_reader_binding_changed')

    def as_record(self):
        self.check()
        return {'version': VERSION, 'axis': AXIS, 'authority_id': self.authority_id,
            'factory': FACTORY_ID, 'definition': deepcopy(self.factory_record),
            'reader_binding': deepcopy(self.reader_record)}


class InitialInformationCatalog:
    """Exact recipient declarations, with no role/family/descendant fallback."""
    def __init__(self, setups, recipients, *, global_authority=None):
        self._setups = {}
        for setup in setups:
            if type(setup) is not OriginalInformationSetup:
                raise TypeError('initial_information_actual_setup_required')
            setup.check()
            if setup.authority_id in self._setups:
                raise ValueError('initial_information_duplicate_authority')
            self._setups[setup.authority_id] = setup
        if not isinstance(recipients, (tuple, list)):
            raise TypeError('initial_information_recipient_declarations_required')
        if global_authority is not None and (global_authority not in self._setups
                or len(self._setups) != 1 or recipients):
            raise ValueError('initial_information_global_factory_ambiguous')
        self.global_authority = global_authority
        self._recipients = {}
        for row in recipients:
            if not isinstance(row, Mapping) or set(row) != {'recipient', 'authority_id'}:
                raise ValueError('initial_information_recipient_declaration_invalid')
            recipient = _name(row['recipient'], 'initial_information_recipient_required')
            authority_id = _name(row['authority_id'], 'initial_information_authority_id_required')
            if recipient in self._recipients:
                raise ValueError('initial_information_ambiguous_recipient')
            if authority_id not in self._setups:
                raise ValueError('initial_information_authority_unavailable')
            self._recipients[recipient] = authority_id

    def validate_consumers(self, registry, *, annotation_consumer):
        """Every declaration names an actual privately declared consumer."""
        if annotation_consumer is not None and not callable(annotation_consumer):
            raise TypeError('initial_information_annotation_consumer_required')
        for recipient in self._recipients:
            if recipient == ANNOTATION_RECIPIENT:
                if annotation_consumer is None:
                    raise ValueError('initial_information_annotation_consumer_missing')
                continue
            binding = registry.for_binding_path(recipient)
            callback = getattr(binding, 'initial_information', None)
            if callback is not None and not callable(callback) and getattr(binding, 'initial_information_requires_authority', False):
                callback = getattr(binding, 'initial_information_consumer', callback)
            if not callable(callback):
                raise ValueError('initial_information_private_consumer_missing:' + recipient)
        for binding in registry._bindings:
            callback = getattr(binding, 'initial_information', None)
            if callback is not None and not callable(callback) and getattr(binding, 'initial_information_requires_authority', False):
                callback = getattr(binding, 'initial_information_consumer', callback)
            if callable(callback):
                recipient = getattr(binding, 'binding_path', None)
                if self.global_authority is None and recipient not in self._recipients:
                    raise ValueError('initial_information_recipient_provenance_missing:' + str(recipient))
                if getattr(binding, 'initial_information_requires_authority', False):
                    authority = self.global_authority if self.global_authority is not None else self._recipients[recipient]
                    setup = self._setups[authority]
                    definition = setup.factory_record
                    if (binding.store is not setup.readers.store or binding.run_id != setup.readers.run_id
                            or binding.directory != setup.readers.directory):
                        raise ValueError('initial_information_recipient_setup_conflict:' + recipient)
                    for name in ('resources', 'initial_information', 'handoff_unit',
                            'acquired_record_unit', 'log_window_bytes', 'log_roles'):
                        if _copy(getattr(binding, name)) != definition[name]:
                            raise ValueError('initial_information_recipient_configuration_conflict:' + recipient + ':' + name)
                    if getattr(setup.readers, 'api_execution', None) is not None:
                        if (binding.api_execution.tools is not setup.readers.api_execution.tools
                                or binding.api_execution.received_input_reader != setup.readers.api_execution.received_input_reader):
                            raise ValueError('initial_information_recipient_api_setup_conflict:' + recipient)
        if self.global_authority is None and annotation_consumer is not None and ANNOTATION_RECIPIENT not in self._recipients:
            raise ValueError('initial_information_recipient_provenance_missing:@annotation')

    def readers(self, recipient, context):
        try:
            setup = self._setups[self.global_authority] if self.global_authority is not None else self._setups[self._recipients[recipient]]
        except KeyError as error:
            raise ValueError('initial_information_recipient_provenance_missing:' + str(recipient)) from error
        setup.check()
        setup.readers.authenticate_context_identity(context)
        return setup.readers

    def as_record(self):
        return {'version': CATALOG_VERSION, 'axis': AXIS,
            'authorities': [setup.as_record() for setup in self._setups.values()],
            'recipients': [{'recipient': key, 'authority_id': value}
                for key, value in self._recipients.items()], 'global_authority': self.global_authority}

    def original_global_information(self, context):
        if self.global_authority is None:
            raise ValueError('initial_information_recipient_provenance_missing')
        from .original_global_information import initial_information
        return initial_information(context, self.readers('@original-global-recipient', context))

    def check_saved(self, original):
        # Preserve exact original descriptors. Do not discard implementation
        # fields, compare only a convenient subset, or use a hash-alias table.
        if _copy(original) != self.as_record():
            raise ValueError('initial_information_original_catalog_required')


def reopen_information_catalog(record, *, original_setups):
    """Check actual rebuilt setup, before any context callback is entered.

    Workflow already reconstructs the explicit caller service factory before
    assembling its registry. That same source-bound factory must reconstruct
    these setups, using the actual Store/run/directory/tool registry. Saved
    module names are compared to the literal identity, never imported.
    """
    value = _copy(record)
    if (not isinstance(value, dict) or set(value) != {'version', 'axis', 'authorities', 'recipients', 'global_authority'}
            or value['version'] != CATALOG_VERSION or value['axis'] != AXIS
            or not isinstance(value['authorities'], list)):
        raise ValueError('initial_information_original_catalog_required')
    if not isinstance(original_setups, (tuple, list)):
        raise TypeError('initial_information_actual_setup_required')
    rebuilt = {}
    for setup in original_setups:
        if type(setup) is not OriginalInformationSetup:
            raise TypeError('initial_information_actual_setup_required')
        if setup.authority_id in rebuilt:
            raise ValueError('initial_information_duplicate_authority')
        rebuilt[setup.authority_id] = setup
    setups = []
    for authority in value['authorities']:
        if (not isinstance(authority, dict) or set(authority) != {
                'version', 'axis', 'authority_id', 'factory', 'definition', 'reader_binding'}
                or authority['version'] != VERSION or authority['axis'] != AXIS
                or authority['factory'] != FACTORY_ID):
            raise ValueError('initial_information_original_authority_required')
        try:
            setup = rebuilt.pop(authority['authority_id'])
        except KeyError as error:
            raise ValueError('initial_information_authority_unavailable') from error
        if setup.as_record() != authority:
            raise ValueError('initial_information_original_authority_required')
        setups.append(setup)
    if rebuilt:
        raise ValueError('initial_information_unrecorded_authority')
    result = InitialInformationCatalog(setups, value['recipients'], global_authority=value['global_authority'])
    result.check_saved(value)
    return result
