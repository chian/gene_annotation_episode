"""A107 original factory authority for received API reports, separately declared.

An authority supplies configured readers. Actual values and reference grants
still require the original saved immediate-child return and admission records.
"""
from copy import deepcopy
import json

from ...communication import plain
from ...execution_service_setup import ExecutionServiceFactory
from ..execution_initial_information.factory_readers import construct_factory_information_readers
from ..execution_initial_information.information_authority import OriginalInformationSetup
from .received_api_reports import ReceivedAPIReports

CONFIGURATION_VERSION = 'a107_received_api_configuration_v1'
CATALOG_VERSION = 'a107_received_api_authority_v1'
ANNOTATION = '@annotation'


def copy(value):
    return json.loads(json.dumps(plain(value), allow_nan=False))


class ReceivedAPIConfiguration:
    def __init__(self, authorities, recipients=(), *, original_global_authority=None):
        if not isinstance(authorities, (tuple, list)) or not authorities:
            raise TypeError('received_api_original_factories_required')
        self.authorities = tuple(authorities)
        names = []
        for name, factory in self.authorities:
            if (not isinstance(name, str) or not name or name.strip() != name
                    or name in names or type(factory) is not ExecutionServiceFactory):
                raise ValueError('received_api_factory_authority_invalid')
            names.append(name)
        if not isinstance(recipients, (list, tuple)):
            raise TypeError('received_api_recipient_declarations_required')
        self.recipients = copy(recipients)
        seen = set()
        for row in self.recipients:
            if (not isinstance(row, dict) or set(row) != {'recipient', 'authority_id'}
                    or not isinstance(row['recipient'], str) or not row['recipient']
                    or row['recipient'] in seen or row['authority_id'] not in names):
                raise ValueError('received_api_recipient_authority_invalid')
            seen.add(row['recipient'])
        if original_global_authority is not None and (
                len(names) != 1 or original_global_authority not in names or self.recipients):
            raise ValueError('received_api_original_global_authority_ambiguous')
        self.original_global_authority = original_global_authority
        self.original = self._record()

    def _record(self):
        return {'version': CONFIGURATION_VERSION, 'axis': 'A107',
            'authorities': [{'authority_id': name, 'factory_definition': copy(factory.as_record())}
                for name, factory in self.authorities],
            'recipients': deepcopy(self.recipients),
            'original_global_authority': self.original_global_authority}

    def as_record(self):
        value = self._record()
        if value != self.original:
            raise ValueError('received_api_original_factory_changed')
        return value

    @classmethod
    def from_record(cls, record):
        value = copy(record)
        if (not isinstance(value, dict) or set(value) != {'version', 'axis', 'authorities',
                'recipients', 'original_global_authority'} or value['version'] != CONFIGURATION_VERSION
                or value['axis'] != 'A107' or not isinstance(value['authorities'], list)):
            raise ValueError('received_api_original_configuration_required')
        authorities = []
        for row in value['authorities']:
            if not isinstance(row, dict) or set(row) != {'authority_id', 'factory_definition'}:
                raise ValueError('received_api_factory_authority_invalid')
            factory = ExecutionServiceFactory.from_record(row['factory_definition'])
            if copy(factory.as_record()) != row['factory_definition']:
                raise ValueError('received_api_original_factory_changed')
            authorities.append((row['authority_id'], factory))
        result = cls(authorities, value['recipients'],
            original_global_authority=value['original_global_authority'])
        if result.as_record() != value:
            raise ValueError('received_api_original_configuration_required')
        return result

    @classmethod
    def original_global_factory(cls, factory, *, authority_id='original-global-execution-factory'):
        return cls([(authority_id, factory)], original_global_authority=authority_id)

    def construct(self, *, store, run_id, directory, tool_registry, services):
        setups = []
        for name, factory in self.authorities:
            readers = construct_factory_information_readers(factory, store=store, run_id=run_id,
                directory=directory, tool_registry=tool_registry, services=services)
            setups.append(OriginalInformationSetup.capture(name, factory, readers))
        return ReceivedAPICatalog(self, setups)


class ReceivedAPICatalog:
    def __init__(self, configuration, setups):
        if type(configuration) is not ReceivedAPIConfiguration:
            raise TypeError('received_api_explicit_configuration_required')
        self.configuration = configuration
        self.definition = configuration.as_record()
        self.setups = {}
        for setup in setups:
            if type(setup) is not OriginalInformationSetup or setup.authority_id in self.setups:
                raise TypeError('received_api_original_setup_required')
            setup.check()
            self.setups[setup.authority_id] = setup
        if set(self.setups) != {row['authority_id'] for row in self.definition['authorities']}:
            raise ValueError('received_api_original_setup_required')
        for name, factory in configuration.authorities:
            if self.setups[name].factory is not factory:
                raise ValueError('received_api_original_factory_object_required')
        self.recipients = {row['recipient']: row['authority_id'] for row in configuration.recipients}

    def setup_for(self, recipient):
        if self.configuration.as_record() != self.definition:
            raise ValueError('received_api_original_factory_changed')
        authority = self.configuration.original_global_authority
        if authority is None:
            try:
                authority = self.recipients[recipient]
            except KeyError as error:
                raise ValueError('received_api_recipient_provenance_missing:' + str(recipient)) from error
        setup = self.setups[authority]
        setup.check()
        return setup

    def configured(self, recipient):
        # Schema declaration is configuration-only and can precede creation of
        # a prospective child's saved context. No received value is read here.
        return ReceivedAPIReports(self.setup_for(recipient).readers.api_execution)

    def received(self, recipient, context):
        setup = self.setup_for(recipient)
        setup.readers.authenticate_context_identity(context)
        return ReceivedAPIReports(setup.readers.api_execution)

    def validate_consumers(self, registry, annotation_consumer):
        if not callable(annotation_consumer):
            raise TypeError('received_api_annotation_consumer_required')
        for recipient in self.recipients:
            if recipient == ANNOTATION:
                continue
            binding = registry.for_binding_path(recipient)
            if not callable(getattr(binding, 'received_api_reports', None)):
                raise ValueError('received_api_private_recipient_missing:' + recipient)
        for binding in registry._bindings:
            recipient = getattr(binding, 'binding_path', None)
            if callable(getattr(binding, 'received_api_reports', None)):
                setup = self.setup_for(recipient)
                if getattr(binding, 'initial_information_requires_authority', False):
                    if (binding.store is not setup.readers.store or binding.run_id != setup.readers.run_id
                            or binding.directory != setup.readers.directory):
                        raise ValueError('received_api_recipient_setup_conflict:' + recipient)
                    for field in ('resources', 'initial_information', 'handoff_unit',
                            'acquired_record_unit', 'log_window_bytes', 'log_roles'):
                        if copy(getattr(binding, field)) != setup.factory_record[field]:
                            raise ValueError('received_api_recipient_configuration_conflict:' + recipient + ':' + field)
                    if setup.readers.api_execution is not None and (
                            binding.api_execution.tools is not setup.readers.api_execution.tools
                            or binding.api_execution.received_input_reader != setup.readers.api_execution.received_input_reader):
                        raise ValueError('received_api_recipient_api_setup_conflict:' + recipient)
        self.setup_for(ANNOTATION)

    def as_record(self):
        return {'version': CATALOG_VERSION, 'axis': 'A107', 'configuration': self.configuration.as_record(),
            'authorities': [setup.as_record() for setup in self.setups.values()]}

    def check_saved(self, value):
        if copy(value) != self.as_record():
            raise ValueError('received_api_original_catalog_required')
