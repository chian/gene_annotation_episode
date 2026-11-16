"""Explicit A110 factory provenance for received result readers.

Configuration selects a reader. Original saved typed reports, counterpart
identities and receipt admissions alone establish received facts and grants.
"""
from copy import deepcopy
import json
from pathlib import Path
from ...communication import plain
from ...method_loop.identities import EpisodeRef
from ...execution_service_setup import ExecutionServiceFactory
from .historical_receiving_owner import HistoricalReceivedExecutionOwner
from .ordinary_fba_reader_custody import OrdinaryFBAReaderCustody
VERSION = 'a110_received_execution_configuration_v1'
CATALOG_VERSION = 'a110_received_execution_catalog_v1'
FACTORY = 'gene_annotation_episode.episodic_workflow.root.a110.execution_service_setup.ExecutionServiceFactory'
ANNOTATION = '@annotation'

def copy(value):
    return json.loads(json.dumps(plain(value), allow_nan=False))

class ReceivedExecutionConfiguration:

    def __init__(self, authorities, recipients=(), *, original_global_authority=None):
        if not isinstance(authorities, (list, tuple)) or not authorities:
            raise TypeError('received_execution_original_factories_required')
        self.authorities = tuple(authorities)
        names = set()
        for name, factory in self.authorities:
            if not isinstance(name, str) or not name or name.strip() != name or (name in names) or (type(factory) is not ExecutionServiceFactory):
                raise ValueError('received_execution_factory_authority_invalid')
            names.add(name)
        if not isinstance(recipients, (list, tuple)):
            raise TypeError('received_execution_recipient_declarations_required')
        self.recipients = copy(recipients)
        seen = set()
        for row in self.recipients:
            if not isinstance(row, dict) or set(row) != {'recipient', 'authority_id'} or (not isinstance(row['recipient'], str)) or (not row['recipient']) or (row['recipient'] in seen) or (row['authority_id'] not in names):
                raise ValueError('received_execution_recipient_authority_invalid')
            seen.add(row['recipient'])
        if original_global_authority is not None and (len(names) != 1 or original_global_authority not in names or self.recipients):
            raise ValueError('received_execution_original_global_authority_ambiguous')
        self.original_global_authority = original_global_authority
        self.original = self._record()

    def _record(self):
        return {'version': VERSION, 'axis': 'A110', 'authorities': [{'authority_id': name, 'factory_definition': copy(factory.as_record())} for name, factory in self.authorities], 'recipients': deepcopy(self.recipients), 'original_global_authority': self.original_global_authority}

    def as_record(self):
        value = self._record()
        if value != self.original:
            raise ValueError('received_execution_original_factory_changed')
        return value

    @classmethod
    def from_record(cls, record):
        value = copy(record)
        if not isinstance(value, dict) or set(value) != {'version', 'axis', 'authorities', 'recipients', 'original_global_authority'} or value['version'] != VERSION or (value['axis'] != 'A110') or (not isinstance(value['authorities'], list)):
            raise ValueError('received_execution_original_configuration_required')
        authorities = []
        for row in value['authorities']:
            if not isinstance(row, dict) or set(row) != {'authority_id', 'factory_definition'}:
                raise ValueError('received_execution_factory_authority_invalid')
            factory = ExecutionServiceFactory.from_record(row['factory_definition'])
            if copy(factory.as_record()) != row['factory_definition']:
                raise ValueError('received_execution_original_factory_changed')
            authorities.append((row['authority_id'], factory))
        result = cls(authorities, value['recipients'], original_global_authority=value['original_global_authority'])
        if result.as_record() != value:
            raise ValueError('received_execution_original_configuration_required')
        return result

    @classmethod
    def original_global_factory(cls, factory, *, authority_id='original-global-execution-factory'):
        return cls([(authority_id, factory)], original_global_authority=authority_id)

    def construct(self, *, store, run_id, directory, tool_registry, services):
        directory = Path(directory)
        setups = {}
        for name, factory in self.authorities:
            record = copy(factory.as_record())
            owner = HistoricalReceivedExecutionOwner(services, store=store, run_id=run_id, directory=directory, resources=record['resources'], initial_information=record['initial_information'], tool_registry=tool_registry, handoff_unit=record['handoff_unit'], acquired_record_unit=record['acquired_record_unit'], log_window_bytes=record['log_window_bytes'], log_roles=record['log_roles'], require_private_yield=record.get('require_private_execution_yield', False), results_yield_profiles=record.get('results_yield_profiles'), task_yield_profiles=record.get('task_yield_profiles'))
            setups[name] = ReceivedExecutionSetup(factory, owner)
        return ReceivedExecutionCatalog(self, setups)

class ReceivedExecutionSetup:

    def __init__(self, factory, owner):
        if type(factory) is not ExecutionServiceFactory or type(owner) is not HistoricalReceivedExecutionOwner:
            raise TypeError('received_execution_actual_factory_setup_required')
        self.factory, self.owner = (factory, owner)
        self.original_ports = (owner.store, owner.tool_registry, owner.services)
        self.ordinary_fba_port = OrdinaryFBAReaderCustody(owner)
        self.factory_record = copy(factory.as_record())
        self.reader_record = self._record()

    def _record(self):
        owner = self.owner
        if any((actual is not original for actual, original in zip((owner.store, owner.tool_registry, owner.services), self.original_ports))):
            raise ValueError('received_execution_original_service_ports_changed')
        return {'version': 'a110_received_execution_setup_v1', 'factory': FACTORY, 'factory_definition': copy(self.factory.as_record()), 'run_id': owner.run_id, 'directory': str(owner.directory), 'progress_binding': copy(owner.job_progress_provider.as_record()), 'ordinary_fba_reader': self.ordinary_fba_port.as_record(owner)}

    def check(self):
        if copy(self.factory.as_record()) != self.factory_record:
            raise ValueError('received_execution_original_factory_changed')
        owner = self.owner
        for field in ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'):
            if copy(getattr(owner, field)) != self.factory_record[field]:
                raise ValueError('received_execution_reader_configuration_changed:' + field)
        if owner.private_yield_binding is not self.factory_record.get('require_private_execution_yield', False):
            raise ValueError('received_execution_reader_configuration_changed:private_yield_binding')
        for field in ('results_yield_profiles', 'task_yield_profiles'):
            original = self.factory_record.get(field)
            expected = {} if original is None else original
            if copy(getattr(owner, field)) != expected:
                raise ValueError('received_execution_reader_configuration_changed:' + field)
        if self._record() != self.reader_record:
            raise ValueError('received_execution_reader_implementation_changed')
        return owner

    def authenticate_context_identity(self, context):
        owner = self.check()
        if context.run_id != owner.run_id or not context.path or context.role != context.path[-1][0] or (EpisodeRef(context.run_id, context.path).episode_id != context.episode_id):
            raise ValueError('received_execution_recipient_identity_conflict')
        return owner

    def as_record(self):
        self.check()
        return deepcopy(self.reader_record)

class ReceivedExecutionCatalog:

    def __init__(self, configuration, setups):
        if type(configuration) is not ReceivedExecutionConfiguration:
            raise TypeError('received_execution_explicit_configuration_required')
        self.configuration, self.setups = (configuration, dict(setups))
        self.definition = configuration.as_record()
        if set(self.setups) != {name for name, factory in configuration.authorities}:
            raise ValueError('received_execution_original_setup_required')
        for name, factory in configuration.authorities:
            setup = self.setups[name]
            if type(setup) is not ReceivedExecutionSetup or setup.factory is not factory:
                raise TypeError('received_execution_original_factory_object_required')
            setup.check()
        self.recipients = {row['recipient']: row['authority_id'] for row in configuration.recipients}

    def setup_for(self, recipient):
        if self.configuration.as_record() != self.definition:
            raise ValueError('received_execution_original_factory_changed')
        name = self.configuration.original_global_authority
        if name is None:
            try:
                name = self.recipients[recipient]
            except KeyError as error:
                raise ValueError('received_execution_recipient_provenance_missing:' + str(recipient)) from error
        setup = self.setups[name]
        setup.check()
        return setup

    def configured(self, recipient):
        return self.setup_for(recipient).check()

    def received(self, recipient, context):
        return self.setup_for(recipient).authenticate_context_identity(context)

    def validate_consumers(self, registry, annotation_consumer):
        if not callable(annotation_consumer):
            raise TypeError('received_execution_annotation_consumer_required')
        for recipient in self.recipients:
            if recipient == ANNOTATION:
                continue
            binding = registry.for_binding_path(recipient)
            if not callable(getattr(binding, 'received_execution_information', None)):
                raise ValueError('received_execution_private_recipient_missing:' + recipient)
        for binding in registry._bindings:
            if not callable(getattr(binding, 'received_execution_information', None)):
                continue
            setup = self.setup_for(binding.binding_path)
            if not getattr(binding, 'received_execution_requires_authority', False):
                continue
            owner = setup.owner
            if binding.store is not owner.store or binding.run_id != owner.run_id or binding.directory != owner.directory:
                raise ValueError('received_execution_recipient_setup_conflict:' + binding.binding_path)
            for field in ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'):
                if copy(getattr(binding, field)) != setup.factory_record[field]:
                    raise ValueError('received_execution_recipient_configuration_conflict:' + binding.binding_path + ':' + field)
            if binding.private_yield_binding is not setup.factory_record.get('require_private_execution_yield', False):
                raise ValueError('received_execution_recipient_configuration_conflict:' + binding.binding_path + ':private_yield_binding')
            for field in ('results_yield_profiles', 'task_yield_profiles'):
                original = setup.factory_record.get(field)
                if copy(getattr(binding, field)) != ({} if original is None else original):
                    raise ValueError('received_execution_recipient_configuration_conflict:' + binding.binding_path + ':' + field)
            if binding.tool_registry is not owner.tool_registry or binding.services is not owner.services:
                raise ValueError('received_execution_original_service_ports_required:' + binding.binding_path)
        self.setup_for(ANNOTATION)

    def as_record(self):
        return {'version': CATALOG_VERSION, 'axis': 'A110', 'configuration': self.configuration.as_record(), 'authorities': [{'authority_id': name, 'setup': setup.as_record()} for name, setup in self.setups.items()]}

    def check_saved(self, record):
        if copy(record) != self.as_record():
            raise ValueError('received_execution_original_catalog_required')
