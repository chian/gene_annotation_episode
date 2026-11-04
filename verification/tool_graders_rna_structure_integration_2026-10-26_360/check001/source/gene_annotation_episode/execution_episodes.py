"""One explicit launch family for the shared episode loop.

The binding routes a selected concrete assignment. Resource operations and
result reads contain no model, resource selection or investigation loop.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from .communication import plain, validate_form
from .domain import identity
from .execution_contracts import canonical, checked, digest, obj
from .launch_instructions import SELECTION_SCHEMA, retain_inherited_selection
from .practical_execution_operations import confined
from .practical_execution_records import (ASSIGNMENT_SCHEMA, validate_assignment,
                                         validate_completion_proof, GENERIC_REQUESTED_JOB_SCHEMA)
from .practical_execution_state import _immutable, _read
from .practical_receipt_information import PracticalReceiptInformation
from .practical_resource_episodes import PracticalResourceEpisodes, operation_catalog
from .resource_records import INPUT_VERSION_SCHEMA
from .native_hmmer_acquisition import is_native_hmmer_target
from .native_blast_acquisition import is_native_blast_target
from .native_blast_database_acquisition import is_native_blast_database_target
from .native_blast_standard_database_acquisition import is_standard_blast_database_target
from .native_infernal_acquisition import is_native_infernal_target
from .native_infernal_preparation_acquisition import is_native_infernal_preparation_target
from .native_hmmer_preparation_acquisition import is_native_hmmer_preparation_target
from .native_rna_structure_acquisition import is_native_rna_structure_target


VERSION = 'execution_episodes_v1'
LAUNCH_VERSION = 'execution_launch_assignment_v1'
RESULTS_VERSION = 'execution_results_assignment_v1'
RESULT_PROVIDER = 'episode.execution_result'
ROLES = ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results')
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}
ROLE_KINDS = {'launch_api': 'api', 'launch_local': 'local', 'launch_hpc': 'hpc'}
TEXT = {'type': 'string', 'minLength': 1}
OFFSET = {'type': 'integer', 'minimum': 0}
LIMIT = {'type': 'integer', 'minimum': 1}
FILE_LIMIT = {**LIMIT, 'maximum': 1024*1024}
NATIVE_RESULT_ORIGIN = {
    'content_location': 'current_resource_filesystem',
    'attempt_output_version': 'unverified',
    'window_consistency': 'separate_reads_no_atomic_file_snapshot',
    'completion_basis': 'requested_acquisition_and_observed_successful_attempt',
}
NATIVE_RESULT_ORIGIN_SCHEMA = obj({key: {'type': 'string', 'enum': [value]}
                                  for key, value in NATIVE_RESULT_ORIGIN.items()})
RESULTS_SCHEMA = obj({'version': {'const': RESULTS_VERSION}, 'handoff_ref': TEXT,
                      'selector': {'type': 'object'}})
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1,
    'uniqueItems': True, 'items': TEXT}, 'path': TEXT, 'offset': OFFSET, 'limit': LIMIT}, [])


def launch_operation_catalog():
    """Declared launch operations, without a target/resource observation."""
    return [{'name': 'execution.capabilities', 'description':
        'Read the actual caller-bound resource configuration and already recorded inventory; no discovery or selection.',
        'input_schema': obj({})}]


def native_result_operation_catalog():
    """Actual local/PBS acquisition operators; execution still requires a target."""
    return [
        {'name': 'execution.results.status', 'description': 'Observe the exact handed-off physical attempt once.',
         'input_schema': obj({})},
        {'name': 'execution.results.collect', 'description':
            'Observe the original attempt and acquire bounded first windows of the requested paths.', 'input_schema': obj({})},
        {'name': 'execution.results.read', 'description':
            'Acquire one selected bounded byte window within the original requested paths and interval.',
         'input_schema': obj({'path': TEXT, 'offset': OFFSET, 'limit': FILE_LIMIT})}]


def _outcome(result=None, *, references=(), code=None):
    return {'status': 'invalid' if code else 'completed', 'record_refs': list(references),
        'changed_record_refs': list(references), 'result': result,
        'feedback': None if code is None else {'category': 'arguments_or_reference', 'code': code}}


class ExecutionEpisodes:
    roles = ROLES
    entry_roles = ('launch', 'results')
    replaces_default_instructions = True

    def __init__(self, services, *, store, directory, run_id, resources, initial_information,
                 tool_registry, handoff_unit, acquired_record_unit, log_window_bytes, log_roles):
        self.services, self.store, self.directory = services, store, Path(directory)
        self.run_id, self.tool_registry = run_id, tool_registry
        self.resources = json.loads(canonical(resources))
        self.initial_information = json.loads(canonical(initial_information))
        if (not isinstance(self.resources, dict) or not self.resources
                or any(not isinstance(key, str) or not key or not isinstance(value, dict)
                    or value.get('kind') not in KINDS for key, value in self.resources.items())):
            raise ValueError('explicit_execution_resources_required')
        if (not isinstance(self.initial_information, dict)
                or not set(self.initial_information) <= set(self.resources)):
            raise ValueError('initial_inventory_resource_not_bound')
        for unit in (handoff_unit, acquired_record_unit):
            if type(unit) not in (int, float) or not math.isfinite(unit) or unit <= 0:
                raise ValueError('explicit_positive_operational_credit_units_required')
        if (type(log_window_bytes) is not int or log_window_bytes < 1
                or not isinstance(log_roles, (tuple, list))
                or any(not isinstance(role, str) or not role for role in log_roles)):
            raise ValueError('explicit_execution_log_selection_required')
        self.handoff_unit, self.acquired_record_unit = handoff_unit, acquired_record_unit
        self.log_window_bytes, self.log_roles = log_window_bytes, tuple(log_roles)
        self._practical = {}
        for resource_id, configuration in self.resources.items():
            kind = KINDS[configuration['kind']]
            if 'native_rna_structure' in configuration:
                from .native_rna_structure_contracts import validate_rna_structure_bindings
                if kind != 'local':
                    raise ValueError('native_rna_structure_resource_execution_binding_unfinished:' + kind)
                validate_rna_structure_bindings(configuration['native_rna_structure'])
            if 'native_blast_standard_database' in configuration and kind != 'hpc':
                raise ValueError('native_blast_standard_database_hpc_resource_required')
            if 'native_blast_database' in configuration and kind != 'hpc':
                raise ValueError('native_blast_database_hpc_resource_required')
            if 'native_hmmer' in configuration and kind != 'local':
                raise ValueError('native_hmmer_resource_execution_binding_unfinished:' + kind)
            if 'native_hmmer' in configuration:
                from .native_hmmer_tool_info import validate_native_hmmer_bindings
                validate_native_hmmer_bindings(configuration['native_hmmer'])
            if 'native_blast' in configuration and kind != 'local':
                raise ValueError('native_blast_resource_execution_binding_unfinished:' + kind)
            if 'native_blast' in configuration:
                from .native_blast_tool_info import validate_native_blast_bindings
                validate_native_blast_bindings(configuration['native_blast'])
            if 'native_infernal' in configuration and kind != 'local':
                raise ValueError('native_infernal_resource_execution_binding_unfinished:' + kind)
            if 'native_infernal' in configuration:
                from .native_infernal_tool_info import validate_native_infernal_bindings
                validate_native_infernal_bindings(configuration['native_infernal'])
            if 'native_infernal_preparation' in configuration:
                from .native_infernal_preparation_tool_info import validate_native_infernal_preparation_bindings
                if kind != 'local':
                    raise ValueError('native_infernal_preparation_resource_execution_binding_unfinished:' + kind)
                validate_native_infernal_preparation_bindings(configuration['native_infernal_preparation'])
            if 'native_hmmer_preparation' in configuration:
                from .native_hmmer_preparation_tool_info import validate_native_hmmer_preparation_bindings
                if kind != 'local':
                    raise ValueError('native_hmmer_preparation_resource_execution_binding_unfinished:' + kind)
                validate_native_hmmer_preparation_bindings(configuration['native_hmmer_preparation'])
            if kind != 'api':
                inventory = self.initial_information.get(resource_id)
                self._practical[resource_id] = PracticalResourceEpisodes(services,
                    directory=self.directory, resources={kind: configuration}, store=store,
                    initial_information={} if inventory is None else {kind: inventory})
        from .api_service_execution import APIServiceExecution
        api_resources = {key: value for key, value in self.resources.items()
                         if KINDS[value['kind']] == 'api'}
        self.api_execution = None if not api_resources else APIServiceExecution(store,
            run_id=run_id, directory=self.directory, configuration=api_resources,
            tool_registry=tool_registry, handoff_unit=handoff_unit,
            acquired_record_unit=acquired_record_unit)
        from .execution_progress import ExecutionProgressProvider
        self.job_progress_provider = ExecutionProgressProvider(store, run_id=run_id,
            directory=self.directory, resources=self.resources, api_execution=self.api_execution,
            log_window_bytes=log_window_bytes, log_roles=self.log_roles)
        self.native_rna_structure_results = self.native_rna_structure_returns = None
        if any(configuration.get('native_rna_structure') for configuration in self.resources.values()):
            from .native_rna_structure_results import NativeRNAStructureResults
            from .native_rna_structure_returns import NativeRNAStructureReturns
            self.native_rna_structure_results = NativeRNAStructureResults(self)
            self.native_rna_structure_returns = NativeRNAStructureReturns(self)
        from .native_hmmer_results import NativeHMMERResults
        self.native_hmmer_results = NativeHMMERResults(self)
        self.native_blast_results = self.native_blast_returns = None
        self.native_blast_standard_database_results = self.native_blast_standard_database_returns = None
        if any(configuration.get('native_blast_standard_database') for configuration in self.resources.values()):
            from .native_blast_standard_database_results import StandardBLASTDatabaseResults
            from .native_blast_standard_database_returns import StandardBLASTDatabaseReturns
            self.native_blast_standard_database_results = StandardBLASTDatabaseResults(self)
            self.native_blast_standard_database_returns = StandardBLASTDatabaseReturns(self)
        self.native_blast_database_results = self.native_blast_database_returns = None
        if any(configuration.get('native_blast_database') for configuration in self.resources.values()):
            from .native_blast_database_results import NativeBLASTDatabaseResults
            from .native_blast_database_returns import NativeBLASTDatabaseReturns
            self.native_blast_database_results = NativeBLASTDatabaseResults(self)
            self.native_blast_database_returns = NativeBLASTDatabaseReturns(self)
        if any(configuration.get('native_blast') for configuration in self.resources.values()):
            from .native_blast_results import NativeBLASTResults
            from .native_blast_returns import NativeBLASTReturns
            self.native_blast_results = NativeBLASTResults(self)
            self.native_blast_returns = NativeBLASTReturns(self)
        self.native_infernal_results = self.native_infernal_returns = None
        if any(configuration.get('native_infernal') for configuration in self.resources.values()):
            from .native_infernal_results import NativeInfernalResults
            from .native_infernal_returns import NativeInfernalReturns
            self.native_infernal_results = NativeInfernalResults(self)
            self.native_infernal_returns = NativeInfernalReturns(self)
        self.native_infernal_preparation_results = self.native_infernal_preparation_returns = None
        if any(configuration.get('native_infernal_preparation') for configuration in self.resources.values()):
            from .native_infernal_preparation_results import NativeInfernalPreparationResults
            from .native_infernal_preparation_returns import NativeInfernalPreparationReturns
            self.native_infernal_preparation_results = NativeInfernalPreparationResults(self)
            self.native_infernal_preparation_returns = NativeInfernalPreparationReturns(self)
        self.native_hmmer_preparation_results = self.native_hmmer_preparation_returns = None
        if any(configuration.get('native_hmmer_preparation') for configuration in self.resources.values()):
            from .native_hmmer_preparation_results import NativeHmmerPreparationResults
            from .native_hmmer_preparation_returns import NativeHmmerPreparationReturns
            self.native_hmmer_preparation_results = NativeHmmerPreparationResults(self)
            self.native_hmmer_preparation_returns = NativeHmmerPreparationReturns(self)

    def as_record(self):
        return {'binding_id': 'execution_episodes', 'version': VERSION, 'configuration': {
            'resources': deepcopy(self.resources), 'initial_information': deepcopy(self.initial_information),
            'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit,
            'log_window_bytes': self.log_window_bytes, 'log_roles': list(self.log_roles)}}

    def credit_kind(self, role):
        if role not in self.roles:
            raise ValueError('unknown_execution_episode_role')
        return 'operational'

    def child_roles(self, role):
        return tuple(ROLE_KINDS) if role == 'launch' else ()

    def _request_schema(self, resource_id, *, selected):
        kind = KINDS[self.resources[resource_id]['kind']]
        schema = deepcopy(self.api_execution.assignment_schema(resource_id)
            if kind == 'api' else ASSIGNMENT_SCHEMA)
        if schema.get('type') != 'object' or not isinstance(schema.get('properties'), dict):
            raise ValueError('concrete_execution_assignment_schema_required')
        schema['properties']['resource_id'] = {'type': 'string', 'const': resource_id}
        if kind != 'api':
            schema['properties']['resource_kind'] = {'type': 'string', 'const': kind}
            alternatives = []
            rna = self.resources[resource_id].get('native_rna_structure', [])
            if rna:
                from .native_rna_structure_tool_info import rna_structure_tool_contracts
                alternatives.extend(row['input_schema'] for row in rna_structure_tool_contracts(
                    rna, resource_kind=kind, resource_id=resource_id))
            database = self.resources[resource_id].get('native_blast_standard_database')
            if database:
                from .native_blast_standard_database_tool_info import standard_blast_database_tool_contracts
                alternatives.extend(row['input_schema'] for row in standard_blast_database_tool_contracts(
                    database['bindings'], resource_kind=kind, resource_id=resource_id))
            database = self.resources[resource_id].get('native_blast_database')
            if database:
                from .native_blast_database_tool_info import native_blast_database_tool_contracts
                alternatives.extend(row['input_schema'] for row in native_blast_database_tool_contracts(
                    database['bindings'], resource_kind=kind, resource_id=resource_id))
            native = self.resources[resource_id].get('native_hmmer', [])
            if native:
                from .native_hmmer_tool_info import native_hmmer_tool_contracts
                alternatives.extend(row['input_schema'] for row in native_hmmer_tool_contracts(
                    native, resource_kind=kind, resource_id=resource_id))
            blast = self.resources[resource_id].get('native_blast', [])
            if blast:
                from .native_blast_tool_info import native_blast_tool_contracts
                alternatives.extend(row['input_schema'] for row in native_blast_tool_contracts(
                    blast, resource_kind=kind, resource_id=resource_id))
            infernal = self.resources[resource_id].get('native_infernal', [])
            if infernal:
                from .native_infernal_tool_info import native_infernal_tool_contracts
                alternatives.extend(row['input_schema'] for row in native_infernal_tool_contracts(
                    infernal, resource_kind=kind, resource_id=resource_id))
            preparation = self.resources[resource_id].get('native_infernal_preparation', [])
            if preparation:
                from .native_infernal_preparation_tool_info import native_infernal_preparation_tool_contracts
                alternatives.extend(row['input_schema'] for row in native_infernal_preparation_tool_contracts(
                    preparation, resource_kind=kind, resource_id=resource_id))
            hmmer_preparation = self.resources[resource_id].get('native_hmmer_preparation', [])
            if hmmer_preparation:
                from .native_hmmer_preparation_tool_info import native_hmmer_preparation_tool_contracts
                alternatives.extend(row['input_schema'] for row in native_hmmer_preparation_tool_contracts(
                    hmmer_preparation, resource_kind=kind, resource_id=resource_id))
            if alternatives:
                schema['properties']['requested_job'] = {
                    'anyOf': [deepcopy(GENERIC_REQUESTED_JOB_SCHEMA), *alternatives]}
            else:
                schema['properties']['requested_job'] = deepcopy(GENERIC_REQUESTED_JOB_SCHEMA)
        if selected and 'resource_id' not in schema['required']:
            schema['required'].append('resource_id')
        return schema

    def assignment_schema(self, role):
        self.credit_kind(role)
        if role == 'results':
            return deepcopy(RESULTS_SCHEMA)
        if role == 'launch':
            schema = obj({'version': {'const': LAUNCH_VERSION},
                'requests': {'type': 'object', 'properties': {key: self._request_schema(key, selected=False)
                    for key in self.resources}, 'minProperties': 1, 'additionalProperties': False},
                'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)},
                'constraints': {'type': 'object'}})
            schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
            return schema
        alternatives = [self._request_schema(key, selected=True) for key, config in self.resources.items()
                        if KINDS[config['kind']] == ROLE_KINDS[role]]
        return {'anyOf': alternatives} if alternatives else {'not': {}}

    def _validate_request(self, value, *, resource_id=None):
        resource_id = resource_id or value.get('resource_id')
        if resource_id not in self.resources:
            raise ValueError('execution_resource_not_bound')
        config = self.resources[resource_id]
        kind = KINDS[config['kind']]
        value = (self.api_execution.validate_assignment(value)
            if kind == 'api' else validate_assignment(value))
        if value.get('resource_id', resource_id) != resource_id:
            raise ValueError('execution_resource_identity_conflict')
        if kind != 'api':
            if value['resource_kind'] != kind:
                raise ValueError('execution_resource_kind_conflict')
            confined(value['workspace'], config['workspace'])
            operations = self._practical[resource_id]._operations(kind)
            validator = getattr(operations, 'validate_assignment', None)
            if validator is not None:
                # The launch request map already names this resource. A
                # resource child later receives that same explicit identity.
                validator({**value, 'resource_id': resource_id})
            operations.validate_action(value, 'practical.inspect', {})
            if value['inventory_snapshot']:
                from .execution_inventory import validate_snapshot
                validate_snapshot(value['inventory_snapshot'], tool_map={entry['name']: entry
                    for entry in operation_catalog(kind)})
        return value

    def _launch(self, value, *, scope=None):
        value = checked(value, self.assignment_schema('launch'), 'invalid_execution_launch_assignment')
        for resource_id, request in value['requests'].items():
            self._validate_request(request, resource_id=resource_id)
            if scope is not None and KINDS[self.resources[resource_id]['kind']] == 'api':
                self.api_execution.validate_assignment(request, scope=scope)
        self._constraints(value['constraints'])
        return value

    @staticmethod
    def _constraints(constraints):
        for key in ('allowed_resource_ids', 'allowed_kinds'):
            if key in constraints and (not isinstance(constraints[key], list)
                    or any(not isinstance(item, str) or not item for item in constraints[key])):
                raise ValueError('invalid_execution_resource_constraints')

    def _permitted(self, assignment, resource_id):
        constraints = assignment['constraints']
        kind = KINDS[self.resources[resource_id]['kind']]
        return (resource_id in assignment['requests']
            and ('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids'])
            and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds'])
            and ('resource_id' not in constraints or resource_id == constraints['resource_id'])
            and ('kind' not in constraints or kind == constraints['kind']))

    def allowed_children(self, parent, caller_capabilities):
        if parent.role != 'launch':
            return ()
        assignment = self._launch(plain(parent.assignment))
        return tuple(role for role, kind in ROLE_KINDS.items() if any(
            KINDS[configuration['kind']] == kind and self._permitted(assignment, resource_id)
            for resource_id, configuration in self.resources.items()))

    def _versions(self, versions, scope):
        for supplied in versions:
            record = self.store.get(supplied['reference'])
            if not self.store.reference_subset([supplied['reference']], plain(scope)):
                raise ValueError('execution_input_outside_assigned_scope')
            if supplied['version'] is not None and str(record.get('revision')) != supplied['version']:
                raise ValueError('execution_input_version_conflict')
            if supplied['content_sha256'] is not None:
                artifact = (record['id'] if record['record_type'] == 'artifact' else
                    record.get('sequence_ref', record.get('artifact_ref')))
                if artifact is None or hashlib.sha256(self.store.get_artifact(artifact)).hexdigest() != supplied['content_sha256']:
                    raise ValueError('execution_input_version_conflict')

    def _match_request(self, assignment, selected):
        resource_id = selected.get('resource_id')
        if resource_id not in self.resources or not self._permitted(assignment, resource_id):
            raise ValueError('execution_resource_selection_conflict')
        expected = deepcopy(assignment['requests'][resource_id])
        expected['resource_id'] = resource_id
        retain_inherited_selection(assignment.get('launch_instructions'), selected.get('launch_instructions'))
        retain_inherited_selection(expected.get('launch_instructions'), selected.get('launch_instructions'))
        if ({key: value for key, value in selected.items() if key != 'launch_instructions'} !=
                {key: value for key, value in expected.items() if key != 'launch_instructions'}):
            raise ValueError('execution_original_request_conflict')
        selectors = {'allowed_resource_ids', 'allowed_kinds', 'resource_id', 'kind'}
        for key, value in assignment['constraints'].items():
            if key not in selectors and selected['constraints'].get(key) != value:
                raise ValueError('execution_parent_constraint_conflict')

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role), 'invalid_execution_assignment')
        if role == 'launch':
            selected = self._launch(selected, scope=scope)
            self._versions(selected['immutable_input_versions'], scope)
            from .native_blast_database_result_publication import validate_native_job_inputs
            from .native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
            for request in selected['requests'].values():
                validate_native_job_inputs(self.store, parent, request)
                validate_standard_blast_job_inputs(self.store, parent, request)
                from .native_rna_structure_result_publication import validate_rna_structure_job_inputs
                validate_rna_structure_job_inputs(self.store, parent, request)
            return selected
        if role == 'results':
            target = self.job_progress_provider.targets.read_target(selected['handoff_ref'], scope)
            self._selector(selected, target)
            if is_native_rna_structure_target(target):
                from .native_rna_structure_result_publication import validate_rna_structure_selected_inputs
                validate_rna_structure_selected_inputs(self.store, parent, selected['selector'],
                    handoff_ref=selected['handoff_ref'], returns=self.native_rna_structure_returns)
            if is_standard_blast_database_target(target):
                from .native_blast_standard_database_result_publication import validate_standard_blast_selected_inputs
                validate_standard_blast_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'])
            if is_native_blast_database_target(target):
                from .native_blast_database_result_publication import validate_selected_inputs
                validate_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'])
            from .bvbrc_data_host import is_bvbrc_request
            if target['resource_kind'] == 'api' and is_bvbrc_request(target['assignment'].get('request')):
                self.api_execution.bvbrc_data.validate_inputs(parent, selected['selector'],
                    request=target['assignment']['request'])
            return selected
        selected = self._validate_request(selected)
        if ROLE_KINDS[role] == 'api':
            selected = self.api_execution.validate_assignment(selected, scope=scope)
        if ROLE_KINDS[role] != KINDS[self.resources[selected['resource_id']]['kind']]:
            raise ValueError('execution_resource_kind_conflict')
        if parent.role != 'launch':
            raise ValueError('resource_child_role_owned_by_launch')
        original = self._launch(plain(parent.assignment))
        self._match_request(original, selected)
        self._versions(original['immutable_input_versions'], scope)
        from .native_blast_database_result_publication import validate_native_job_inputs
        from .native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
        validate_native_job_inputs(self.store, parent, selected)
        validate_standard_blast_job_inputs(self.store, parent, selected)
        from .native_rna_structure_result_publication import validate_rna_structure_job_inputs
        validate_rna_structure_job_inputs(self.store, parent, selected)
        return selected

    def _delegate(self, context):
        assignment = self._validate_request(plain(context.assignment))
        return self.api_execution if context.role == 'launch_api' else self._practical[assignment['resource_id']]

    def initialize(self, context):
        if context.role in ROLE_KINDS:
            self._check_parent_inputs(context)
            return self._delegate(context).initialize(context)
        if context.role == 'launch':
            value = self._launch(plain(context.assignment), scope=context.scope)
            self._versions(value['immutable_input_versions'], context.scope)
        else:
            target = self._target(context)
            self._selector(plain(context.assignment), target)
            if target['resource_kind'] == 'api':
                return self.api_execution.initialize(context)
            self._result_directory(context)

    def _check_parent_inputs(self, context):
        if len(context.path) < 2 or context.path[-2][0] != 'launch':
            return
        row = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND path=?',
            (self.run_id, canonical(context.path[:-1]))).fetchone()
        if row is not None:
            original = self._launch(json.loads(row['request'])['message']['episode_assignment'])
            self._match_request(original, plain(context.assignment))
            self._versions(original['immutable_input_versions'], context.scope)
            from .native_blast_database_result_publication import validate_native_job_inputs
            from .native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
            validate_native_job_inputs(self.store, context, plain(context.assignment))
            validate_standard_blast_job_inputs(self.store, context, plain(context.assignment))
            from .native_rna_structure_result_publication import validate_rna_structure_job_inputs
            validate_rna_structure_job_inputs(self.store, context, plain(context.assignment))
            return
        raise ValueError('execution_original_launch_assignment_unavailable')

    def state(self, context):
        """Expose the original practical state for its original resource role."""
        if context.role not in {'launch_local', 'launch_hpc'}:
            raise ValueError('practical_resource_role_required')
        return self._delegate(context).state(context)

    def _resource_information(self, resource_id):
        config = self.resources[resource_id]
        capability = next(value for value in self.capabilities() if value['resource_id'] == resource_id)
        value = {'resource_id': resource_id, 'resource_kind': KINDS[config['kind']],
            'availability': capability['availability'], 'tool_names': capability['tool_names'],
            **{key: deepcopy(config[key]) for key in ('workspace', 'policy', 'account', 'python_executable',
                'service', 'base_url') if key in config},
            'inventory_snapshot': deepcopy(self.initial_information.get(resource_id))}
        if config['kind'] == 'api':
            facts = {}
            for entry in self.api_execution.capabilities(resource_id):
                reported = entry.get('configuration', {})
                for name in ('ncbi_contact_configured', 'provider_rate_state_configured'):
                    if name not in reported:
                        continue
                    actual = reported[name]
                    if type(actual) is not bool:
                        raise ValueError('api_configuration_fact_must_be_boolean')
                    if name in facts and facts[name] != actual:
                        raise ValueError('api_configuration_fact_conflict')
                    facts[name] = actual
            if facts:
                value['api_configuration_facts'] = facts
        return value

    def initial_decision_context(self, context):
        value = {'execution_resource_capabilities': [self._resource_information(key) for key in self.resources],
            'execution_initial_information': deepcopy(self.initial_information),
            'received_bvbrc_values': [] if self.api_execution is None else
                self.api_execution.received_bvbrc_context(context)}
        if self._forwards_minhash_reports(context.role):
            value['received_minhash_values'] = self.api_execution.minhash.received_context(context)
        if self.native_rna_structure_returns is not None and context.role in {'annotation', 'scientific_process'}:
            value['received_rna_structure_values'] = self.native_rna_structure_returns.received_context(context)
        return value

    def capabilities(self):
        """Configured operation availability, with no deployment/authentication probe."""
        return [{'resource_id': key, 'kind': KINDS[configuration['kind']],
            'availability': 'unknown', 'observed_at': 'caller_configuration',
            'provenance_refs': [], 'knowledge_entry_ids': [],
            'tool_names': [entry['name'] for entry in (
                self.api_execution.capabilities(key) if KINDS[configuration['kind']] == 'api'
                else operation_catalog(KINDS[configuration['kind']]))]}
            for key, configuration in self.resources.items()]

    def resource_tool_contracts(self):
        """Information for commissioning the actual configured resource owners.

        These declarations do not enable direct scientific invocation. The
        original launch/results assignment still supplies the job and selector;
        only the selected resource episode can execute each operation.
        """
        contracts = {}
        for resource_id, configuration in self.resources.items():
            kind = KINDS[configuration['kind']]
            resource_role = {'api': 'launch_api', 'local': 'launch_local', 'hpc': 'launch_hpc'}[kind]
            launch = (self.api_execution.operation_contracts(resource_id, 'launch_api')
                      if kind == 'api' else operation_catalog(kind))
            results = (self.api_execution.operation_contracts(resource_id, 'results')
                       if kind == 'api' else native_result_operation_catalog())
            for entry_role, owner_role, entries in (
                    ('launch', resource_role, launch), ('results', 'results', results)):
                for entry in entries:
                    key = entry['name'], kind
                    route = {'entry_role': entry_role, 'resource_id': resource_id,
                             'resource_role': owner_role}
                    if key not in contracts:
                        contracts[key] = {name: deepcopy(entry[name])
                            for name in ('name', 'description', 'input_schema')}
                        if 'instructions' in entry:
                            contracts[key]['instructions'] = entry['instructions']
                        contracts[key].update(resources=kind,
                            invocation_route={'kind': 'commission', 'routes': []})
                    elif canonical(contracts[key]['input_schema']) != canonical(entry['input_schema']):
                        raise ValueError('execution_resource_operation_contract_conflict:' + entry['name'])
                    if route not in contracts[key]['invocation_route']['routes']:
                        contracts[key]['invocation_route']['routes'].append(route)
            if kind == 'api':
                service = self.api_execution.services.get(resource_id)
                if (service is not None and service.service == 'bvbrc_appservice'
                        and ('bvbrc_homology', '1') in service.scientific_adapters):
                    from .bvbrc_homology_tool_info import homology_tool_contracts
                    for entry in homology_tool_contracts(resource_id=resource_id,
                            assignment_schema=self.api_execution.assignment_schema(resource_id)):
                        key = entry['name'], kind
                        if key not in contracts:
                            contracts[key] = entry
                        else:
                            prior = contracts[key]
                            prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                            prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                if service is not None and service.service == 'bvbrc_appservice':
                    if ('bvbrc_genome_alignment', '1') in service.scientific_adapters:
                        from .bvbrc_genome_alignment_tool_info import genome_alignment_tool_contracts
                        for entry in genome_alignment_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id)):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    if ('bvbrc_comparative_systems', '1') in service.scientific_adapters:
                        from .bvbrc_comparative_systems_tool_info import comparative_systems_tool_contracts
                        for entry in comparative_systems_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id)):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    if ('bvbrc_fastqutils', '2') in service.scientific_adapters:
                        from .bvbrc_fastqutils_tool_info import fastqutils_tool_contracts
                        for entry in fastqutils_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id)):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    proteome_versions = tuple(version for version in ('1', '2')
                        if ('bvbrc_proteome', version) in service.scientific_adapters)
                    if proteome_versions:
                        from .bvbrc_proteome_tool_info import proteome_tool_contracts
                        for entry in proteome_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id),
                                adapter_versions=proteome_versions):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    for provider in ('bvbrc_msa', 'bvbrc_metacats'):
                        if (provider, '1') not in service.scientific_adapters:
                            continue
                        from .bvbrc_alignment_tool_info import alignment_tool_contracts
                        for entry in alignment_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id),
                                provider=provider):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    for provider in ('bvbrc_gene_tree', 'bvbrc_codon_tree'):
                        if (provider, '1') not in service.scientific_adapters:
                            continue
                        from .bvbrc_phylogeny_tool_info import phylogeny_tool_contracts
                        for entry in phylogeny_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id),
                                provider=provider):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
            native_entries = []
            if configuration.get('native_rna_structure'):
                from .native_rna_structure_tool_info import rna_structure_tool_contracts
                native_entries.extend(rna_structure_tool_contracts(configuration['native_rna_structure'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_blast_standard_database'):
                from .native_blast_standard_database_tool_info import standard_blast_database_tool_contracts
                native_entries.extend(standard_blast_database_tool_contracts(configuration['native_blast_standard_database']['bindings'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_blast_database'):
                from .native_blast_database_tool_info import native_blast_database_tool_contracts
                native_entries.extend(native_blast_database_tool_contracts(configuration['native_blast_database']['bindings'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_hmmer'):
                from .native_hmmer_tool_info import native_hmmer_tool_contracts
                native_entries.extend(native_hmmer_tool_contracts(configuration['native_hmmer'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_blast'):
                from .native_blast_tool_info import native_blast_tool_contracts
                native_entries.extend(native_blast_tool_contracts(configuration['native_blast'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_infernal'):
                from .native_infernal_tool_info import native_infernal_tool_contracts
                native_entries.extend(native_infernal_tool_contracts(configuration['native_infernal'],
                    resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_infernal_preparation'):
                from .native_infernal_preparation_tool_info import native_infernal_preparation_tool_contracts
                native_entries.extend(native_infernal_preparation_tool_contracts(
                    configuration['native_infernal_preparation'], resource_kind=kind, resource_id=resource_id))
            if configuration.get('native_hmmer_preparation'):
                from .native_hmmer_preparation_tool_info import native_hmmer_preparation_tool_contracts
                native_entries.extend(native_hmmer_preparation_tool_contracts(
                    configuration['native_hmmer_preparation'], resource_kind=kind, resource_id=resource_id))
            for entry in native_entries:
                key = entry['name'], kind
                if key in contracts:
                    # Different deployment software must remain explicit in
                    # the bound request schema; combine actual alternatives.
                    prior = contracts[key]
                    if prior['description'] != entry['description']:
                        raise ValueError('execution_native_instruction_conflict:' + entry['name'])
                    sections = prior.setdefault('_native_instruction_sections', {
                        route['resource_id']: prior['instructions']
                        for route in prior['invocation_route']['routes']})
                    sections[resource_id] = entry['instructions']
                    if len(set(sections.values())) > 1:
                        prior['instructions'] = '\n\n'.join('Resource '+key+':\n'+value
                            for key, value in sections.items())
                    schemas = prior.setdefault('_native_schemas', [prior['input_schema']])
                    if entry['input_schema'] not in schemas:
                        schemas.append(entry['input_schema'])
                    prior['input_schema'] = {'anyOf': deepcopy(schemas)}
                    prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                else:
                    contracts[key] = deepcopy(entry)
        for entry in contracts.values():
            entry.pop('_native_schemas', None)
            entry.pop('_native_instruction_sections', None)
        return [contracts[key] for key in sorted(contracts)]

    def permitted_common_actions(self, context):
        if context.role == 'launch':
            return ('tool', 'reason', 'child', 'wait', 'redeliver_report')
        if context.role == 'launch_api':
            assignment = self._validate_request(plain(context.assignment))
            if assignment['version'] == 'api_service_assignment_v1':
                return ('tool', 'wait')
        elif context.role == 'results':
            target = self._target(context)
            if (target['resource_kind'] == 'api'
                    and target['assignment']['version'] == 'api_service_assignment_v1'):
                return ('tool', 'wait')
        return ('tool',)

    def instructions(self, context):
        if context.role in {'launch_local', 'launch_hpc'}:
            return self._delegate(context).instructions(context)
        if context.role == 'launch_api':
            assignment = self._validate_request(plain(context.assignment))
            service = assignment['service']
            return (f'Carry out the assigned work through {service} using one selected operation each turn. '
                'Keep the original inputs, request, resource and parent constraints fixed. Choose useful '
                'preparation, service requests, observations or repair from the actual available operations '
                'and received outcomes. Distinguish an immediate returned response from a service job that '
                'continues remotely. Preserve the actual request or job identity and submission uncertainty; '
                'a missing reply does not establish that no job was created. Establish the requested usable '
                'monitoring/results handoff from recorded service facts. The configured controller governs '
                'continuation; verified original handoff completion gives exact zero future credit.')
        if context.role == 'results':
            return ('Acquire the original selected execution results through the original handoff. Choose bounded '
                'status or requested file/page reads using actual preceding outcomes. Preserve partial bytes and '
                'native scores. Native paths expose the current resource filesystem: the exact attempt observation '
                'does not establish that current file bytes were produced by that attempt. Separate read windows '
                'are not an atomic file snapshot. The scientific parent interprets the returned records. Original work, resource '
                'and selector stay fixed. Only actual complete acquisition establishes this endpoint.')
        return ('Choose which permitted concrete execution request to commission on an explicit resource_id. '
            'Capabilities, recorded inventory and timing information inform the choice. Preserve the original '
            'job, immutable inputs, constraints and pinned instructions. A resource child owns iterative execution '
            'in the shared loop. Receive its requested typed handoff; no infrastructure chooses an approach. '
            'Actual received usable handoff completes this launch endpoint with exact zero future credit.')

    def decision_context(self, context, current_view):
        if context.role in {'launch_local', 'launch_hpc'}:
            return self._delegate(context).decision_context(context, current_view)
        value = {'execution_assignment': plain(context.assignment),
                 'execution_progress': self.facts(context, {})}
        if context.role == 'results':
            value['execution_target'] = self._target(context)
            value['execution_target_description'] = self.job_progress_provider.targets.describe_target(
                value['execution_target']['handle'], context.scope,
                selector=plain(context.assignment)['selector'])
            from .bvbrc_data_host import is_bvbrc_request
            if value['execution_target']['resource_kind'] == 'api' and is_bvbrc_request(
                    value['execution_target']['assignment'].get('request')):
                value['own_bvbrc_values'] = self.api_execution.bvbrc_data.own_values(context)
        if context.role == 'launch_api':
            callback = getattr(self.api_execution, 'decision_context', None)
            if callback is not None:
                value.update(callback(context, current_view))
        return value

    def _target(self, context):
        assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        return self.job_progress_provider.targets.read_target(assignment['handoff_ref'], context.scope)

    def _selector(self, assignment, target):
        if is_native_rna_structure_target(target):
            if self.native_rna_structure_results is None:
                raise ValueError('native_rna_structure_results_binding_unavailable')
            from .rna_structure_result_views import validate_rna_structure_result_selector
            return validate_rna_structure_result_selector(assignment['selector'],
                mode=target['assignment']['requested_job']['native_rna_structure']['mode'])
        if target['resource_kind'] == 'api':
            return self.api_execution.validate_result_selector(target, assignment['selector'])
        if is_standard_blast_database_target(target):
            if self.native_blast_standard_database_results is None:
                raise ValueError('native_blast_standard_database_results_binding_unavailable')
            from .native_blast_standard_database_result_views import validate_standard_blast_database_selector
            return validate_standard_blast_database_selector(assignment['selector'],
                program=target['assignment']['requested_job']['native_blast_standard_database']['program'])
        if is_native_blast_database_target(target):
            if self.native_blast_database_results is None:
                raise ValueError('native_blast_database_results_binding_unavailable')
            from .native_blast_database_result_views import validate_native_blast_database_result_selector
            return validate_native_blast_database_result_selector(assignment['selector'],
                program=target['assignment']['requested_job']['native_blast_database']['program'])
        if is_native_hmmer_preparation_target(target):
            if self.native_hmmer_preparation_results is None:
                raise ValueError('native_hmmer_preparation_results_binding_unavailable')
            from .hmmer_preparation_result_views import validate_preparation_result_selector
            job = target['assignment']['requested_job']['native_hmmer_preparation']
            return validate_preparation_result_selector(assignment['selector'], program=job['program'], mode=job['mode'])
        if is_native_hmmer_target(target):
            from .hmmer_native_result_views import validate_native_hmmer_result_selector
            return validate_native_hmmer_result_selector(assignment['selector'],
                program=target['assignment']['requested_job']['native_hmmer']['program'])
        if is_native_blast_target(target):
            if self.native_blast_results is None:
                raise ValueError('native_blast_results_binding_unavailable')
            from .blast_pairwise_result_views import validate_native_blast_result_selector
            return validate_native_blast_result_selector(assignment['selector'],
                program=target['assignment']['requested_job']['native_blast']['program'])
        if is_native_infernal_target(target):
            if self.native_infernal_results is None:
                raise ValueError('native_infernal_results_binding_unavailable')
            from .infernal_native_result_views import validate_native_infernal_result_selector
            return validate_native_infernal_result_selector(assignment['selector'],
                program=target['assignment']['requested_job']['native_infernal']['program'])
        if is_native_infernal_preparation_target(target):
            if self.native_infernal_preparation_results is None:
                raise ValueError('native_infernal_preparation_results_binding_unavailable')
            from .infernal_preparation_result_views import validate_preparation_result_selector
            job = target['assignment']['requested_job']['native_infernal_preparation']
            return validate_preparation_result_selector(assignment['selector'], program=job['program'], mode=job['mode'])
        value = checked(assignment['selector'], NATIVE_SELECTOR_SCHEMA, 'invalid_execution_native_selector')
        paths = list(value.get('paths', []))
        if 'path' in value:
            if value['path'] in paths:
                raise ValueError('ambiguous_execution_results_selector')
            paths.append(value['path'])
        if not paths or ('offset' in value or 'limit' in value) and 'path' not in value:
            raise ValueError('execution_results_paths_required')
        for path in paths:
            confined(path, target['assignment']['workspace'])
        return value

    def catalog(self, context):
        if context.role in ROLE_KINDS:
            return self._delegate(context).catalog(context)
        if context.role == 'launch':
            return launch_operation_catalog()
        target = self._target(context)
        if is_native_rna_structure_target(target):
            self._selector(plain(context.assignment), target)
            from .native_rna_structure_results import operation_catalog as rna_result_catalog
            return rna_result_catalog()
        if is_standard_blast_database_target(target):
            self._selector(plain(context.assignment), target)
            from .native_blast_standard_database_results import operation_catalog as database_catalog
            return database_catalog()
        if is_native_blast_database_target(target):
            selector = self._selector(plain(context.assignment), target)
            from .native_blast_database_results import operation_catalog as database_catalog
            return database_catalog(selector)
        if target['resource_kind'] == 'api':
            return self.api_execution.catalog(context)
        if is_native_hmmer_preparation_target(target):
            if self.native_hmmer_preparation_results is None:
                raise ValueError('native_hmmer_preparation_results_binding_unavailable')
            from .native_hmmer_preparation_results import operation_catalog as hmmer_preparation_result_catalog
            return hmmer_preparation_result_catalog()
        if is_native_hmmer_target(target):
            from .native_hmmer_results import operation_catalog as hmmer_result_catalog
            return hmmer_result_catalog()
        if is_native_blast_target(target):
            if self.native_blast_results is None:
                raise ValueError('native_blast_results_binding_unavailable')
            from .native_blast_results import operation_catalog as blast_result_catalog
            return blast_result_catalog()
        if is_native_infernal_target(target):
            if self.native_infernal_results is None:
                raise ValueError('native_infernal_results_binding_unavailable')
            from .native_infernal_results import operation_catalog as infernal_result_catalog
            return infernal_result_catalog()
        if is_native_infernal_preparation_target(target):
            if self.native_infernal_preparation_results is None:
                raise ValueError('native_infernal_preparation_results_binding_unavailable')
            from .native_infernal_preparation_results import operation_catalog as preparation_result_catalog
            return preparation_result_catalog()
        return native_result_operation_catalog()

    async def execute(self, context, tool_name, arguments, operation_key):
        if context.role in ROLE_KINDS:
            self._check_parent_inputs(context)
            return await self._delegate(context).execute(context, tool_name, arguments, operation_key)
        try:
            catalog = {entry['name']: entry for entry in self.catalog(context)}
            if tool_name not in catalog:
                raise ValueError('execution_operation_not_available')
            arguments = checked(arguments, catalog[tool_name]['input_schema'], 'invalid_execution_operation_arguments')
            if context.role == 'launch':
                return _outcome(self.initial_decision_context(context))
            target = self._target(context)
            if is_native_rna_structure_target(target):
                return await self.native_rna_structure_results.execute(context, target, tool_name, arguments, operation_key)
            if is_standard_blast_database_target(target):
                return await self.native_blast_standard_database_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_blast_database_target(target):
                return await self.native_blast_database_results.execute(context, target, tool_name, arguments, operation_key)
            if target['resource_kind'] == 'api':
                return await self.api_execution.execute(context, tool_name, arguments, operation_key)
            if is_native_hmmer_preparation_target(target):
                return await self.native_hmmer_preparation_results.execute(
                    context, target, tool_name, arguments, operation_key)
            if is_native_hmmer_target(target):
                return await self.native_hmmer_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_blast_target(target):
                return await self.native_blast_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_infernal_target(target):
                return await self.native_infernal_results.execute(context, target, tool_name, arguments, operation_key)
            if is_native_infernal_preparation_target(target):
                return await self.native_infernal_preparation_results.execute(
                    context, target, tool_name, arguments, operation_key)
            return await self._execute_native_results(context, target, tool_name, arguments, operation_key)
        except (ValueError, TypeError) as error:
            return _outcome(code=str(error))

    def _result_directory(self, context):
        directory = self.directory/'execution-results'/digest([context.run_id, context.episode_id])
        directory.mkdir(parents=True, exist_ok=True)
        manifest = {'run_id': context.run_id, 'episode_id': context.episode_id,
            'assignment': plain(context.assignment), 'scope': plain(context.scope)}
        _immutable(directory/'assignment.json', manifest)
        return directory

    def _windows(self, selector):
        values = {path: (0, None) for path in selector.get('paths', [])}
        if 'path' in selector:
            values[selector['path']] = (selector.get('offset', 0), selector.get('limit'))
        return values

    def _selected_result_action(self, episode_id, key, name, arguments):
        prefix = self.run_id+':'+episode_id+':'
        suffix = key.removeprefix(prefix)
        if not key.startswith(prefix) or not suffix.isdecimal() or str(int(suffix)) != suffix:
            raise ValueError('execution_result_selected_action_missing')
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? '
            'AND episode_id=? AND decision_index=?', (self.run_id, episode_id, int(suffix))).fetchone()
        if row is None:
            raise ValueError('execution_result_selected_action_missing')
        action = json.loads(row['action'])
        if action.get('kind') != 'tool' or action.get('tool') != name or action.get('arguments') != arguments:
            raise ValueError('execution_result_selected_action_conflict')
        return row

    async def _execute_native_results(self, context, target, tool_name, arguments, operation_key):
        self._selected_result_action(context.episode_id, operation_key, tool_name, arguments)
        selector = self._selector(plain(context.assignment), target)
        requested = self._windows(selector)
        windows = []
        if tool_name == 'execution.results.read':
            if arguments['path'] not in requested:
                raise ValueError('execution_results_selector_conflict')
            start, length = requested[arguments['path']]
            if (arguments['offset'] < start or length is not None
                    and arguments['offset'] + arguments['limit'] > start + length):
                raise ValueError('execution_results_selector_conflict')
            windows = [arguments]
        elif tool_name == 'execution.results.collect':
            windows = [{'path': path, 'offset': start,
                'limit': min(self.log_window_bytes, 1024*1024, length) if length is not None
                    else min(self.log_window_bytes, 1024*1024)}
                for path, (start, length) in requested.items()]
        directory = self._result_directory(context)
        key = digest(operation_key)
        intent = {'operation_key': operation_key, 'tool_name': tool_name, 'arguments': arguments,
            'target': target, 'assignment': plain(context.assignment)}
        receipt_path = directory/(key+'.receipt.json')
        if receipt_path.exists():
            _immutable(directory/(key+'.intent.json'), intent)
            body = _read(receipt_path)
        else:
            previous = self.store.db.execute('SELECT decision_index FROM runtime_actions WHERE run_id=? '
                'AND episode_id=? AND result IS NOT NULL ORDER BY decision_index DESC',
                (self.run_id, context.episode_id))
            for row in previous:
                if self._proof_for_action(context, f'{self.run_id}:{context.episode_id}:{row[0]}') is not None:
                    raise ValueError('execution_results_assignment_already_completed')
            _immutable(directory/(key+'.intent.json'), intent)
            observation_path = directory/(key+'.observation.json')
            if not observation_path.exists():
                observed = self.job_progress_provider.targets.observe_target(target,
                    operation_key=operation_key)
                _immutable(observation_path, observed)
            observation = _read(observation_path)
            acquired, failures = [], []
            for index, window in enumerate(windows):
                path = directory/(key+f'.window-{index}.json')
                if not path.exists():
                    try:
                        data = self.job_progress_provider.targets.read_file(target, **window,
                            operation_key=operation_key+f':file:{index}')
                        value = {'window': data, 'failure': None}
                    except (ValueError, OSError) as error:
                        value = {'window': None, 'failure': {'path': window['path'],
                            'code': str(error) if isinstance(error, ValueError) else 'execution_result_file_unavailable',
                            'exception_type': type(error).__name__}}
                    _immutable(path, value)
                value = _read(path)
                if value['window'] is not None:
                    acquired.append(value['window'])
                else:
                    failures.append(value['failure'])
            body = {'version': 'execution_result_information_v2', 'run_id': context.run_id,
                'episode_id': context.episode_id, 'scope': plain(context.scope),
                'assignment': plain(context.assignment), 'operation_key': operation_key,
                'tool_name': tool_name, 'arguments': arguments, 'target': target,
                'observation': observation, 'windows': acquired, 'failures': failures,
                'acquisition_origin': deepcopy(NATIVE_RESULT_ORIGIN)}
            _immutable(receipt_path, body)
        reference = self._publish_result(context, body)
        return _outcome(body, references=[reference])

    def _publish_result(self, context, body):
        self._validate_result_body(body, context.scope)
        artifact = self.store.artifact(canonical(body), 'application/json')
        payload = {'provider': RESULT_PROVIDER, 'accession': 'execution_result_'+digest([
            context.run_id, context.episode_id, body['operation_key']]), 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
            'version': body['version'], 'retrieved_at': body['observation']['observed_at']}
        return self.store.put('source', payload, origin='tool')['id']

    def _validate_result_body(self, body, scope):
        fields = {'version', 'run_id', 'episode_id', 'scope', 'assignment', 'operation_key',
            'tool_name', 'arguments', 'target', 'observation', 'windows', 'failures', 'acquisition_origin'}
        if (not isinstance(body, dict) or set(body) != fields
                or body['version'] != 'execution_result_information_v2' or body['run_id'] != self.run_id
                or body['acquisition_origin'] != NATIVE_RESULT_ORIGIN):
            raise ValueError('invalid_execution_result_information')
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        target = self.job_progress_provider.targets.read_target(body['assignment']['handoff_ref'], scope)
        if canonical(target) != canonical(body['target']):
            raise ValueError('execution_result_original_target_conflict')
        selector = self._selector(body['assignment'], target)
        requested = self._windows(selector)
        row = self._selected_result_action(body['episode_id'], body['operation_key'], body['tool_name'], body['arguments'])
        episode = self.store.db.execute('SELECT request,path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id, body['episode_id'])).fetchone()
        if episode is not None:
            message = json.loads(episode['request'])['message']
            if (message.get('episode_assignment') != body['assignment'] or message['scope'] != body['scope']
                    or json.loads(episode['path'])[-1][0] != 'results'):
                raise ValueError('execution_result_original_assignment_conflict')
        for window in body['windows']:
            if window['path'] not in requested:
                raise ValueError('execution_result_selector_conflict')
            raw = base64.b64decode(window['bytes_base64'], validate=True)
            start, length = requested[window['path']]
            if (window['offset'] < start or window['returned_bytes'] != len(raw)
                    or length is not None and window['offset']+len(raw) > start+length
                    or window['size_bytes'] < 0):
                raise ValueError('execution_result_window_conflict')
        # The immutable receiver journal, rather than model assertions or a
        # forged Store artifact, owns this selected acquisition.
        directory = self.directory/'execution-results'/digest([self.run_id, body['episode_id']])
        path = directory/(digest(body['operation_key'])+'.receipt.json')
        if not path.exists() or canonical(_read(path)) != canonical(body):
            raise ValueError('execution_result_original_receipt_conflict')
        return row

    def _read_result(self, reference, scope):
        source = self.store.get(reference)
        if source.get('provider') != RESULT_PROVIDER:
            return None
        raw = self.store.get_artifact(source['artifact_ref'])
        body = json.loads(raw)
        row = self._validate_result_body(body, scope)
        payload = {'provider': RESULT_PROVIDER, 'accession': 'execution_result_'+digest([
            body['run_id'], body['episode_id'], body['operation_key']]), 'uri': None,
            'artifact_ref': source['artifact_ref'], 'text_ref': source['artifact_ref'], 'request_ref': None,
            'version': body['version'], 'retrieved_at': body['observation']['observed_at']}
        expected = identity('source', {'origin': 'tool', 'record': payload})
        if (reference != expected or raw != canonical(body).encode()
                or {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}} != payload):
            raise ValueError('execution_result_source_identity_conflict')
        if row['result'] is not None:
            outcome = json.loads(row['result'])
            if (outcome.get('status') != 'completed' or outcome.get('result') != body
                    or reference not in outcome.get('record_refs', [])):
                raise ValueError('execution_result_saved_outcome_conflict')
        return body

    def _selection(self, context, supplied=None):
        if supplied is None and self.services is not None:
            callback = getattr(self.services, 'record_selection', None)
            supplied = None if callback is None else callback(context)
        if supplied is None:
            from .episode_receipts import EpisodeReceipts
            table = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_receipt_inheritance'").fetchone()
            if table and self.store.db.execute('SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
                    (self.run_id, context.episode_id)).fetchone():
                receipts = EpisodeReceipts(self.store, self.run_id)
                supplied = {'run_id': self.run_id, 'episode_id': context.episode_id,
                    'known_record_refs': list(receipts.known(context.episode_id)),
                    'initial_known_record_refs': list(receipts.known(context.episode_id, baseline=True))}
            else:
                rows = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
                    'AND result IS NOT NULL ORDER BY decision_index', (self.run_id, context.episode_id))
                supplied = {'run_id': self.run_id, 'episode_id': context.episode_id,
                    'known_record_refs': list(dict.fromkeys(ref for row in rows
                        for ref in json.loads(row[0]).get('record_refs', []))), 'initial_known_record_refs': []}
        supplied = plain(supplied)
        if supplied.get('run_id') != self.run_id or supplied.get('episode_id') != context.episode_id:
            raise ValueError('execution_receiver_identity_conflict')
        for key in ('known_record_refs', 'initial_known_record_refs'):
            if not isinstance(supplied.get(key), list) or any(not isinstance(ref, str) or not ref for ref in supplied[key]):
                raise ValueError('execution_receiver_references_required')
        if not set(supplied['initial_known_record_refs']) <= set(supplied['known_record_refs']):
            raise ValueError('execution_initial_references_must_be_known')
        return supplied

    def _context_target(self, context, target):
        if context.role == 'launch':
            self._match_request(self._launch(plain(context.assignment)), target['assignment'])
        elif context.role in ROLE_KINDS:
            if canonical(target['assignment']) != canonical(context.assignment):
                raise ValueError('execution_handoff_assignment_conflict')
        elif context.role == 'results' and target != self._target(context):
            raise ValueError('execution_result_target_conflict')
        return target

    def _received(self, context, selection=None):
        selection = self._selection(context, selection)
        handoffs, results = {}, {}
        for reference in dict.fromkeys(selection['known_record_refs']):
            source = self.store.get(reference)
            if source.get('provider') == RESULT_PROVIDER:
                if source.get('version') in {'native_hmmer_bundle_v1', 'native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_standard_database_bundle_v1', 'native_infernal_bundle_v1',
                        'native_infernal_preparation_bundle_v1', 'native_hmmer_preparation_bundle_v1',
                        'native_rna_structure_bundle_v1'}:
                    # Original bundle acquisitions have their own exact-row
                    # receipts; they are not current-filesystem byte windows.
                    continue
                body = self._read_result(reference, context.scope)
                if context.role == 'results' and body['assignment'] != plain(context.assignment):
                    continue
                results[reference] = body
                continue
            if (source.get('provider') != 'episode.practical_receipt'
                    and not (self.api_execution is not None
                        and self.api_execution.is_handoff_source(reference))):
                continue
            try:
                target = self.job_progress_provider.targets.read_target(reference, context.scope)
            except (ValueError, KeyError):
                continue  # A preparation/status-only receipt is no handoff.
            try:
                self._context_target(context, target)
            except ValueError:
                # An inherited handoff for different work stays valid context,
                # without becoming this assignment's contribution or endpoint.
                continue
            if self.job_progress_provider.targets.returnable_handoff(target):
                handoffs[reference] = target
        return selection, handoffs, results

    def _forwards_bvbrc_reports(self, role):
        return (role in {'annotation', 'scientific_process'} and self.api_execution is not None
            and any(service.service == 'bvbrc_data' for service in self.api_execution.services.values()))

    def _forwards_minhash_reports(self, role):
        return (role in {'annotation', 'scientific_process'} and self.api_execution is not None
            and any(service.service == 'bvbrc_minhash' for service in self.api_execution.services.values()))

    def received_report_sources(self, role):
        result = {}
        if self.native_rna_structure_returns is not None and role in {'annotation', 'scientific_process'}:
            from .rna_structure_result_views import rna_structure_fact_sources
            result.update(rna_structure_fact_sources())
        if self.native_blast_standard_database_returns is not None and role in {'annotation', 'scientific_process'}:
            from .native_blast_standard_database_result_views import standard_blast_database_fact_sources
            result.update(standard_blast_database_fact_sources())
        if self.native_blast_database_returns is not None and role in {'annotation', 'scientific_process'}:
            from .native_blast_database_result_views import native_blast_database_fact_sources
            result.update(native_blast_database_fact_sources())
        if self.native_hmmer_preparation_returns is not None and role in {'annotation', 'scientific_process'}:
            from .hmmer_preparation_result_views import preparation_fact_sources
            result.update(preparation_fact_sources())
        if self.native_infernal_preparation_returns is not None and role in {'annotation', 'scientific_process'}:
            from .infernal_preparation_result_views import preparation_fact_sources
            result.update(preparation_fact_sources())
        if self._has_rfam() and role in {'annotation', 'scientific_process'}:
            from .rfam_batch_returns import rfam_fact_sources
            result.update(rfam_fact_sources())
        if self.native_blast_returns is not None and role in {'annotation', 'scientific_process'}:
            from .blast_pairwise_result_views import native_blast_fact_sources
            result.update(native_blast_fact_sources())
            result['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
        if self.native_infernal_returns is not None and role in {'annotation', 'scientific_process'}:
            from .infernal_native_result_views import native_infernal_fact_sources
            result.update(native_infernal_fact_sources())
            result['execution_infernal_result_refs'] = self._infernal_reference_source()
        if self._forwards_bvbrc_reports(role):
            from .bvbrc_data_views import bvbrc_data_fact_sources
            result.update(bvbrc_data_fact_sources())
        if self._forwards_minhash_reports(role):
            from .bvbrc_minhash_views import minhash_fact_sources
            result.update(minhash_fact_sources())
        if self._has_appservice() and role in {'annotation', 'scientific_process'}:
            result.update(self._appservice_sources())
        return result

    def received_report_facts(self, context):
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        if self.native_rna_structure_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_rna_structure_returns.received_facts(context, schema))
        if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_standard_database_returns.received_facts(context, schema))
        if self.native_blast_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_database_returns.received_facts(context, schema))
        if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_hmmer_preparation_returns.received_facts(context, schema))
        if self.native_infernal_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_infernal_preparation_returns.received_facts(context, schema))
        if self._has_rfam() and context.role in {'annotation', 'scientific_process'}:
            result.update(self.api_execution.rfam_returns.received_facts(context, schema))
        if self.native_blast_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_returns.received_facts(context, schema))
        if self.native_infernal_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_infernal_returns.received_facts(context, schema))
        if self._forwards_bvbrc_reports(context.role):
            result.update(self.api_execution.bvbrc_data.received_facts(context, schema))
        if self._forwards_minhash_reports(context.role):
            result.update(self.api_execution.minhash.received_facts(context, schema))
        if self._has_appservice() and context.role in {'annotation', 'scientific_process'}:
            # Execution roles already supply their own/received support facts
            # through facts(); only the scientific roles need this forwarding.
            if any(node.get('x-source') == 'bvbrc_appservice_support_refs'
                    for node in schema.get('properties', {}).values()):
                result['bvbrc_appservice_support_refs'] = self.api_execution.appservice.received_support_refs(context)
            result.update(self.api_execution.homology_returns.received_facts(context, schema))
            result.update(self.api_execution.phylogeny_returns.received_facts(context, schema))
            result.update(self.api_execution.alignment_returns.received_facts(context, schema))
            result.update(self.api_execution.genome_alignment_returns.received_facts(context, schema))
            proteome = self.api_execution.proteome_returns.received_facts(context, schema)
            if set(result).intersection(proteome):
                raise ValueError('received_report_fact_conflict')
            result.update(proteome)
            comparative = self.api_execution.comparative_systems_returns.received_facts(context, schema)
            if set(result).intersection(comparative):
                raise ValueError('received_report_fact_conflict')
            result.update(comparative)
            fastqutils = self.api_execution.fastqutils_returns.received_facts(context, schema)
            if set(result).intersection(fastqutils):
                raise ValueError('received_report_fact_conflict')
            result.update(fastqutils)
        return result

    def resolve_received_reference(self, context, reference, namespace):
        if self.native_rna_structure_results is not None:
            # This callback precedes Workflow's generic Store fallback, even
            # for ordinary scientific receivers and old expanded receipts.
            access = self.native_rna_structure_results.retained_reference_access(context, reference, namespace)
            if access is not None:
                return access
            if context.role in {'annotation', 'scientific_process'}:
                resolved = self.native_rna_structure_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
        if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_blast_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_infernal_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_infernal_preparation_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_rfam() and context.role in {'annotation', 'scientific_process'}:
            resolved = self.api_execution.rfam_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_blast_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_infernal_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_infernal_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_appservice():
            from .bvbrc_homology_returns import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                # Results owns its publication. The normal role resolver below
                # validates those facts; there is no child return to consult.
                if context.role == 'results':
                    return None
                return self.api_execution.homology_returns.resolve_received(context, reference, namespace)
            from .bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
            if namespace in PHYLOGENY_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.phylogeny_returns.resolve_received(context, reference, namespace)
            from .bvbrc_alignment_returns import IDENTIFIER_NAMESPACES as ALIGNMENT_NAMESPACES
            if namespace in ALIGNMENT_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.alignment_returns.resolve_received(context, reference, namespace)
            from .bvbrc_genome_alignment_returns import IDENTIFIER_NAMESPACES as GENOME_ALIGNMENT_NAMESPACES
            if namespace in GENOME_ALIGNMENT_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.genome_alignment_returns.resolve_received(context, reference, namespace)
            from .bvbrc_proteome_returns import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
            if namespace in PROTEOME_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.proteome_returns.resolve_received(context, reference, namespace)
            from .bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
            if namespace in COMPARATIVE_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.comparative_systems_returns.resolve_received(context, reference, namespace)
            from .bvbrc_fastqutils_returns import IDENTIFIER_NAMESPACES as FASTQUTILS_NAMESPACES
            if namespace in FASTQUTILS_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.fastqutils_returns.resolve_received(context, reference, namespace)
            resolved = self.api_execution.appservice.resolve(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._forwards_bvbrc_reports(context.role):
            resolved = self.api_execution.bvbrc_data.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._forwards_minhash_reports(context.role):
            resolved = self.api_execution.minhash.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        for results in (self.native_hmmer_preparation_results, self.native_infernal_preparation_results):
            if results is not None:
                resolved = results.retained_reference_access(context, reference, namespace)
                if resolved is not None:
                    return resolved
        return None

    def validate_received_report(self, context, form, schema):
        if self.native_rna_structure_returns is not None:
            self.native_rna_structure_returns.validate_received_report(context, form, schema)
        if self.native_blast_standard_database_returns is not None:
            self.native_blast_standard_database_returns.validate_received_report(context, form, schema)
        if self.native_blast_database_returns is not None:
            self.native_blast_database_returns.validate_received_report(context, form, schema)
        if self.native_hmmer_preparation_returns is not None:
            self.native_hmmer_preparation_returns.validate_received_report(context, form, schema)
        if self.native_infernal_preparation_returns is not None:
            self.native_infernal_preparation_returns.validate_received_report(context, form, schema)
        if self._has_rfam():
            self.api_execution.rfam_returns.validate_received_report(context, form, schema)
        if self.native_blast_returns is not None:
            self.native_blast_returns.validate_received_report(context, form, schema)
        if self.native_infernal_returns is not None:
            self.native_infernal_returns.validate_received_report(context, form, schema)
        if self._has_appservice():
            self.api_execution.appservice.validate_received_report(context, form, schema)
            self.api_execution.homology_returns.validate_received_report(context, form, schema)
            self.api_execution.phylogeny_returns.validate_received_report(context, form, schema)
            self.api_execution.alignment_returns.validate_received_report(context, form, schema)
            self.api_execution.genome_alignment_returns.validate_received_report(context, form, schema)
            self.api_execution.proteome_returns.validate_received_report(context, form, schema)
            self.api_execution.comparative_systems_returns.validate_received_report(context, form, schema)
            self.api_execution.fastqutils_returns.validate_received_report(context, form, schema)
        if self._forwards_bvbrc_reports(context.role):
            self.api_execution.bvbrc_data.validate_received_report(context, form, schema)
        if self._forwards_minhash_reports(context.role):
            self.api_execution.minhash.validate_received_report(context, form, schema)

    def fact_sources(self, role):
        from .hmmer_native_result_views import native_hmmer_fact_sources
        values = native_hmmer_fact_sources()
        if self.native_rna_structure_results is not None:
            from .rna_structure_result_views import rna_structure_fact_sources
            values.update(rna_structure_fact_sources())
        if self.native_blast_standard_database_results is not None:
            from .native_blast_standard_database_result_views import standard_blast_database_fact_sources
            values.update(standard_blast_database_fact_sources())
        if self.native_blast_database_results is not None:
            from .native_blast_database_result_views import native_blast_database_fact_sources
            values.update(native_blast_database_fact_sources())
        if self.native_hmmer_preparation_results is not None:
            from .hmmer_preparation_result_views import preparation_fact_sources
            values.update(preparation_fact_sources())
        if self.native_infernal_preparation_results is not None:
            from .infernal_preparation_result_views import preparation_fact_sources
            values.update(preparation_fact_sources())
        if self._has_rfam() and role == 'results':
            from .rfam_batch_returns import rfam_fact_sources
            values.update(rfam_fact_sources())
        if self.native_blast_results is not None:
            from .blast_pairwise_result_views import native_blast_fact_sources
            values.update(native_blast_fact_sources())
            values['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
        if self.native_infernal_results is not None:
            from .infernal_native_result_views import native_infernal_fact_sources
            values.update(native_infernal_fact_sources())
            values['execution_infernal_result_refs'] = self._infernal_reference_source()
        if self._has_appservice():
            values.update(self._appservice_sources())
        from .bvbrc_data_views import bvbrc_data_fact_sources
        values.update(bvbrc_data_fact_sources())
        if self.api_execution is not None and any(service.service == 'bvbrc_minhash'
                for service in self.api_execution.services.values()):
            from .bvbrc_minhash_views import minhash_fact_sources
            values.update(minhash_fact_sources())
        if role in {'launch_local', 'launch_hpc'}:
            # Definitions are identical across actual practical resources.
            values.update(PracticalResourceEpisodes.fact_sources(None, role))
        for key, namespace, meaning in (
                ('execution_handoff_refs', 'execution_handoff', 'Qualified original handoff sources actually available to this episode, including authenticated original failed native database or RNA attempts for partial-output acquisition; failed attempts do not establish a successful native endpoint.'),
                ('execution_result_refs', 'execution_result', 'Qualified actual requested result acquisitions available to this episode. Generic native windows retain current-filesystem observations. Explicit BLAST/HMMER/Infernal/RNA producer bundles retain original attempt outputs matched by digest and requested numerical facts. RNA source delivery alone grants no auxiliary artifacts or unrequested rows.')):
            values[key] = {'type': 'array', 'meaning': meaning, 'report_schema': {
                'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference',
                'x-reference-namespace': namespace}, 'x-source': key}}
        values['execution_completed'] = {'type': 'boolean', 'meaning':
            'Whether this assignment has actual verified endpoint information. Generic native results mean requested current-filesystem acquisition plus independently observed successful exact execution, without a producing-attempt or atomic-version claim. RNA results mean complete requested original-bundle or retained-sheet delivery, including specific unavailable values; this does not assert native success. Yielding alone is false.'}
        from .native_hmmer_acquisition import ORIGIN as hmmer_origin
        values['execution_result_origin'] = {'type': ['object', 'null'], 'meaning':
            'Actual acquisition semantics: current-file windows or a complete digest-verified original BLAST/HMMER/Infernal/RNA producer bundle. RNA failed native attempts and saved-sheet recalculations return null even when qualified delivery completes.',
            'report_schema': {**obj({key: {'type': 'string', 'enum': list(dict.fromkeys([
                NATIVE_RESULT_ORIGIN[key], value]))} for key, value in hmmer_origin.items()}),
                'type': ['object', 'null'],
                'x-source': 'execution_result_origin'}}
        from .blast_result_views import BLAST_HSP_FACT_SCHEMA
        values['execution_blast_hsps'] = {'type': 'array', 'meaning':
            'Optional explicitly requested native measurements for all published HSPs of this acquired result. No automatic ranking, top-N or significance filter. target_coverage is native reference/hit coverage, not original gene-target coverage. HSP/reference records support later scoped reads; selected HSP references can instead be returned through a parent-chosen typed field. No functional assignment or annotation score.',
            'report_schema': {**deepcopy(BLAST_HSP_FACT_SCHEMA), 'x-source': 'execution_blast_hsps'}}
        return values

    def _has_appservice(self):
        return self.api_execution is not None and any(service.service == 'bvbrc_appservice'
            for service in self.api_execution.services.values())

    def _has_rfam(self):
        return self.api_execution is not None and any(service.service == 'rfam_batch'
            for service in self.api_execution.services.values())

    @staticmethod
    def _blast_reference_source():
        return {'type': 'array', 'meaning':
            'Native paired BLAST source, observation and reference records actually returned through this boundary. '
            'References alone do not deliver unrequested numerical rows.',
            'report_schema': {'type': 'array', 'uniqueItems': True,
                'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'},
                'x-source': 'execution_blast_pairwise_result_refs'}}

    @staticmethod
    def _infernal_reference_source():
        return {'type': 'array', 'meaning':
            'Infernal source, observation and model references actually returned through this episode boundary. '
            'These references alone do not deliver unrequested numerical rows.',
            'report_schema': {'type': 'array', 'uniqueItems': True,
                'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'},
                'x-source': 'execution_infernal_result_refs'}}

    @staticmethod
    def _appservice_sources():
        from .bvbrc_homology_returns import homology_fact_sources
        from .bvbrc_phylogeny_returns import phylogeny_fact_sources
        from .bvbrc_alignment_returns import alignment_fact_sources
        from .bvbrc_genome_alignment_returns import genome_alignment_fact_sources
        from .bvbrc_proteome_returns import proteome_fact_sources
        from .bvbrc_comparative_systems_returns import comparative_systems_fact_sources
        from .bvbrc_fastqutils_returns import fastqutils_fact_sources
        return {**homology_fact_sources(), **phylogeny_fact_sources(), **alignment_fact_sources(),
            **genome_alignment_fact_sources(), **proteome_fact_sources(), **comparative_systems_fact_sources(),
            **fastqutils_fact_sources(), 'bvbrc_appservice_support_refs': {'type': 'array', 'meaning':
            'Actually received AppService preparation, Workspace, upload or observation receipts; these are not scientific result acquisitions.',
            'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {
                'type': 'string', 'format': 'reference', 'x-reference-namespace': 'bvbrc_appservice_support'},
                'x-source': 'bvbrc_appservice_support_refs'}}}

    def facts(self, context, completion_snapshot):
        from .hmmer_native_result_views import FAMILY_SOURCES
        native_empty = {source: [] for source in FAMILY_SOURCES.values()}
        if self.native_rna_structure_results is not None:
            from .rna_structure_result_views import rna_structure_fact_sources
            native_empty.update({source: [] for source in rna_structure_fact_sources()})
            if self.native_rna_structure_results.applies(context):
                return {**native_empty, **self.native_rna_structure_results.facts(context)}
        if self.native_blast_standard_database_results is not None:
            from .native_blast_standard_database_results import empty_facts
            native_empty.update(empty_facts())
            if self.native_blast_standard_database_results.applies(context):
                return {**native_empty, **self.native_blast_standard_database_results.facts(context)}
        if self.native_blast_database_results is not None:
            from .native_blast_database_results import empty_facts
            native_empty.update(empty_facts())
            if self.native_blast_database_results.applies(context):
                return {**native_empty, **self.native_blast_database_results.facts(context)}
        if self.native_hmmer_preparation_results is not None:
            from .hmmer_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
            if self.native_hmmer_preparation_results.applies(context):
                return {**native_empty, **self.native_hmmer_preparation_results.facts(context)}
        if self.native_infernal_preparation_results is not None:
            from .infernal_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
            if self.native_infernal_preparation_results.applies(context):
                return {**native_empty, **self.native_infernal_preparation_results.facts(context)}
        if self.native_blast_results is not None:
            from .blast_pairwise_result_views import FAMILY_SOURCES as BLAST_SOURCES
            native_empty.update({source: [] for source in BLAST_SOURCES.values()})
            native_empty['execution_blast_pairwise_result_refs'] = []
            if self.native_blast_results.applies(context):
                return {**native_empty, **self.native_blast_results.facts(context)}
        if self.native_infernal_results is not None:
            from .infernal_native_result_views import FAMILY_SOURCES as INFERNAL_SOURCES
            native_empty.update({source: [] for source in INFERNAL_SOURCES.values()})
            native_empty['execution_infernal_result_refs'] = []
            if self.native_infernal_results.applies(context):
                return {**native_empty, **self.native_infernal_results.facts(context)}
        if self.native_hmmer_results.applies(context):
            return {**native_empty, **self.native_hmmer_results.facts(context)}
        if context.role == 'launch_api' or context.role == 'results' and self._target(context)['resource_kind'] == 'api':
            return {**native_empty, **self.api_execution.facts(context, completion_snapshot), 'execution_result_origin': None}
        extra = self._delegate(context).facts(context, completion_snapshot) if context.role in {'launch_local', 'launch_hpc'} else {}
        _, handoffs, results = self._received(context)
        if context.role in {'launch_local', 'launch_hpc'}:
            # Selected receipt publication may precede runtime result storage.
            for reference in extra['practical_receipt_refs']:
                try:
                    target = self._context_target(context,
                        self.job_progress_provider.targets.read_target(reference, context.scope))
                    if self.job_progress_provider.targets.returnable_handoff(target):
                        handoffs[reference] = target
                except ValueError:
                    pass
        completed = (extra.get('practical_completed', False) if context.role in ROLE_KINDS else
            any(self.job_progress_provider.targets.usable_handoff(target) for target in handoffs.values())
            if context.role == 'launch' else self._native_results_complete(context, list(results.values())))
        return {**native_empty, **extra, 'execution_handoff_refs': sorted(handoffs),
                **({'bvbrc_appservice_support_refs': self.api_execution.appservice.received_support_refs(context)}
                   if self._has_appservice() else {}),
                'execution_blast_hsps': [],
                'execution_result_refs': sorted(ref for ref, body in results.items() if body['windows']),
                'execution_result_origin': deepcopy(NATIVE_RESULT_ORIGIN) if any(
                    body['windows'] for body in results.values()) else None,
                'execution_completed': completed}

    def received_form_references(self, context, form, schema, operation_key):
        from .hmmer_native_result_views import FAMILY_SOURCES
        references = []
        if self._has_rfam():
            references.extend(self.api_execution.rfam_returns.record_admission(context, form, schema, operation_key))
        native_references = set()
        if self.native_rna_structure_returns is not None:
            admitted = self.native_rna_structure_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_blast_standard_database_returns is not None:
            admitted = self.native_blast_standard_database_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_blast_database_returns is not None:
            admitted = self.native_blast_database_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_hmmer_preparation_returns is not None:
            admitted = self.native_hmmer_preparation_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_infernal_preparation_returns is not None:
            admitted = self.native_infernal_preparation_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_blast_returns is not None:
            admitted = self.native_blast_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_infernal_returns is not None:
            admitted = self.native_infernal_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.api_execution is not None:
            references.extend(self.api_execution.record_bvbrc_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.minhash.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.homology_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.phylogeny_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.alignment_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.genome_alignment_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.proteome_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.comparative_systems_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.fastqutils_returns.record_admission(context, form, schema, operation_key))
        for name, declared in plain(schema).get('properties', {}).items():
            if declared.get('x-source') in FAMILY_SOURCES.values():
                for row in form[name]:
                    for reference in [row['source_ref'], row['observation_ref'], *row['reference_refs']]:
                        if reference is None:
                            continue
                        if not self.resolve(context, reference, 'execution_result'):
                            raise ValueError('execution_received_reference_unqualified')
                        references.append(reference)
            if declared.get('x-source') == 'execution_blast_hsps':
                for row in form[name]:
                    for field in ('hsp_ref', 'reference_ref'):
                        reference = row[field]
                        if not self.resolve(context, reference, 'execution_result'):
                            raise ValueError('execution_received_reference_unqualified')
                        references.append(reference)
            if declared.get('x-source') in {'execution_handoff_refs', 'execution_result_refs', 'practical_receipt_refs',
                    'bvbrc_appservice_support_refs'}:
                for reference in form[name]:
                    namespace = declared['items'].get('x-reference-namespace')
                    # This exact native child form was authenticated above.
                    # Reuse only those admitted execution-result references;
                    # other providers and namespaces keep their own resolver.
                    already_admitted = namespace == 'execution_result' and reference in native_references
                    if not already_admitted and not self.resolve(context, reference, namespace):
                        raise ValueError('execution_received_reference_unqualified')
                    references.append(reference)
        return list(dict.fromkeys(references))

    def initial_references(self, context):
        if self._has_appservice() and (self.api_execution.appservice.owns_context(context)
                or context.role == 'launch' and any(value.get('service') == 'bvbrc_appservice'
                    for value in plain(context.assignment).get('requests', {}).values())):
            return self.api_execution.appservice.initial_references(context)
        if context.role != 'results':
            from .native_rna_structure_result_publication import validate_rna_structure_job_inputs
            assignment = plain(context.assignment)
            requests = (assignment.get('requests', {}).values() if context.role == 'launch' else
                [assignment] if context.role == 'launch_local' else [])
            return list(dict.fromkeys(ref for request in requests for ref in
                validate_rna_structure_job_inputs(self.store, context, request)))
        assignment = plain(context.assignment)
        selected = [assignment['handoff_ref']]
        target = self._target(context)
        if is_native_rna_structure_target(target):
            from .native_rna_structure_result_publication import validate_rna_structure_selected_inputs
            selected.extend(validate_rna_structure_selected_inputs(self.store, context, assignment['selector'],
                handoff_ref=assignment['handoff_ref'], returns=self.native_rna_structure_returns))
        if is_standard_blast_database_target(target):
            from .native_blast_standard_database_result_publication import validate_standard_blast_selected_inputs
            selected.extend(validate_standard_blast_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        if is_native_blast_database_target(target):
            from .native_blast_database_result_publication import validate_selected_inputs
            selected.extend(validate_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        from .bvbrc_data_host import is_bvbrc_request
        if target['resource_kind'] == 'api' and is_bvbrc_request(target['assignment'].get('request')):
            # These are only the explicitly named parent-supplied input pages
            # and metadata, not everything visible in the parent's storage.
            extra = self.api_execution.bvbrc_data._selected_input_refs(assignment)
            for reference in extra:
                self.api_execution.bvbrc_data.possession(context, reference)
            selected.extend(extra)
        return selected

    def resolve(self, context, reference, namespace):
        try:
            if self.native_rna_structure_results is not None:
                access = self.native_rna_structure_results.retained_reference_access(context, reference, namespace)
                if access is not None:
                    return access
                from .rna_structure_result_views import IDENTIFIER_NAMESPACES as RNA_NAMESPACES
                if namespace in RNA_NAMESPACES:
                    return (self.native_rna_structure_results.resolve(context, reference, namespace)
                        if context.role == 'results' else
                        self.native_rna_structure_returns.resolve_received(context, reference, namespace))
                if self.native_rna_structure_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_rna_structure_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_blast_standard_database_results is not None:
                from .native_blast_standard_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return (self.native_blast_standard_database_results.resolve(context, reference, namespace)
                        if context.role == 'results' else self.native_blast_standard_database_returns.resolve_received(context, reference, namespace))
                if self.native_blast_standard_database_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_blast_database_results is not None:
                from .native_blast_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return (self.native_blast_database_results.resolve(context, reference, namespace)
                        if context.role == 'results' else self.native_blast_database_returns.resolve_received(context, reference, namespace))
                if self.native_blast_database_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_hmmer_preparation_results is not None:
                from .hmmer_preparation_result_views import IDENTIFIER_NAMESPACES as HMMER_PREPARATION_NAMESPACES
                if namespace in HMMER_PREPARATION_NAMESPACES:
                    return (self.native_hmmer_preparation_results.resolve(context, reference, namespace)
                        if context.role == 'results' else
                        self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace))
                if self.native_hmmer_preparation_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_infernal_preparation_results is not None:
                from .infernal_preparation_result_views import IDENTIFIER_NAMESPACES as PREPARATION_NAMESPACES
                if namespace in PREPARATION_NAMESPACES:
                    return (self.native_infernal_preparation_results.resolve(context, reference, namespace)
                        if context.role == 'results' else
                        self.native_infernal_preparation_returns.resolve_received(context, reference, namespace))
                if self.native_infernal_preparation_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_infernal_preparation_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self._has_rfam():
                from .rfam_batch_returns import IDENTIFIER_NAMESPACES as RFAM_NAMESPACES
                if namespace in RFAM_NAMESPACES:
                    return (self.api_execution.rfam_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.rfam_returns.resolve_received(context, reference, namespace))
            if self.native_blast_results is not None:
                if namespace in {'native_blast_pairwise_row', 'native_blast_artifact_key',
                        'native_blast_search_pointer'}:
                    return (self.native_blast_results.resolve(context, reference, namespace)
                        if context.role == 'results' else
                        self.native_blast_returns.resolve_received(context, reference, namespace))
                if self.native_blast_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_infernal_results is not None:
                from .infernal_native_result_views import IDENTIFIER_NAMESPACES as INFERNAL_NAMESPACES
                if namespace in INFERNAL_NAMESPACES:
                    return (self.native_infernal_results.resolve(context, reference, namespace)
                        if context.role == 'results' else
                        self.native_infernal_returns.resolve_received(context, reference, namespace))
                if self.native_infernal_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_infernal_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self._has_appservice():
                from .bvbrc_homology_returns import IDENTIFIER_NAMESPACES
                if namespace in IDENTIFIER_NAMESPACES:
                    return (self.api_execution.homology_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.homology_returns.resolve_received(context, reference, namespace))
                from .bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
                if namespace in PHYLOGENY_NAMESPACES:
                    return (self.api_execution.phylogeny_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.phylogeny_returns.resolve_received(context, reference, namespace))
                from .bvbrc_alignment_returns import IDENTIFIER_NAMESPACES as ALIGNMENT_NAMESPACES
                if namespace in ALIGNMENT_NAMESPACES:
                    return (self.api_execution.alignment_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.alignment_returns.resolve_received(context, reference, namespace))
                from .bvbrc_genome_alignment_returns import IDENTIFIER_NAMESPACES as GENOME_ALIGNMENT_NAMESPACES
                if namespace in GENOME_ALIGNMENT_NAMESPACES:
                    return (self.api_execution.genome_alignment_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.genome_alignment_returns.resolve_received(context, reference, namespace))
                from .bvbrc_proteome_returns import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
                if namespace in PROTEOME_NAMESPACES:
                    return (self.api_execution.proteome_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.proteome_returns.resolve_received(context, reference, namespace))
                from .bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
                if namespace in COMPARATIVE_NAMESPACES:
                    return (self.api_execution.comparative_systems_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.comparative_systems_returns.resolve_received(context, reference, namespace))
                from .bvbrc_fastqutils_returns import IDENTIFIER_NAMESPACES as FASTQUTILS_NAMESPACES
                if namespace in FASTQUTILS_NAMESPACES:
                    return (self.api_execution.fastqutils_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.fastqutils_returns.resolve_received(context, reference, namespace))
                resolved = self.api_execution.appservice.resolve(context, reference, namespace)
                if resolved is not None:
                    return resolved
            if namespace == 'bvbrc_minhash_genome':
                if self.api_execution is None:
                    return False
                if context.role == 'results':
                    return self.api_execution.minhash.resolve_own(context, reference, namespace)
                return self.api_execution.minhash.resolve_received(context, reference, namespace)
            from .bvbrc_data_views import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                return self.api_execution is not None and self.api_execution.bvbrc_data.resolve(context, reference, namespace)
            if namespace in {'execution_handle', 'execution'}:
                from .episode_bindings import reference_in_context
                return bool(self.services is not None and reference_in_context(
                    self.services, context, reference, namespace))
            if (context.role in {'launch_local', 'launch_hpc'} and namespace == 'practical_receipt'
                    and not reference.startswith('source_')):
                return self._delegate(context).resolve(context, reference, namespace)
            if self.native_hmmer_results.resolve(context, reference, namespace):
                return True
            source = self.store.get(reference)
            if source.get('provider') == RESULT_PROVIDER:
                if source.get('version') in {'native_hmmer_bundle_v1', 'native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_standard_database_bundle_v1', 'native_infernal_bundle_v1',
                        'native_infernal_preparation_bundle_v1', 'native_hmmer_preparation_bundle_v1',
                        'native_rna_structure_bundle_v1'}:
                    return False
                if namespace not in {None, 'source', 'execution_result'}:
                    return False
                body = self._read_result(reference, context.scope)
                return bool(body['windows']) if namespace == 'execution_result' else True
            if namespace in {None, 'source', 'execution_handoff'}:
                try:
                    target = self.job_progress_provider.targets.read_target(reference, context.scope)
                    return namespace != 'execution_handoff' or self.job_progress_provider.targets.returnable_handoff(target)
                except ValueError:
                    if namespace == 'execution_handoff':
                        return False
            if PracticalReceiptInformation(self.store, self.run_id).resolve(context, reference, namespace):
                return True
            if self.api_execution is not None and self.api_execution.resolve(context, reference, namespace):
                return True
            if self.native_hmmer_preparation_results is not None:
                access = self.native_hmmer_preparation_results.retained_reference_access(context, reference, namespace)
                if access is not None:
                    return access
            if self.native_infernal_preparation_results is not None:
                access = self.native_infernal_preparation_results.retained_reference_access(context, reference, namespace)
                if access is not None:
                    return access
            if (source.get('provider') == 'episode.practical_receipt'
                    or self.api_execution is not None
                        and self.api_execution.is_handoff_source(reference)):
                return False
            if self.services is not None:
                from .episode_bindings import reference_in_context
                return bool(reference_in_context(self.services, context, reference, namespace))
            kind = source['record_type']
            return bool(self.store.reference_subset([reference], plain(context.scope)) and (
                namespace in {None, kind} or namespace == 'subject' and
                kind in {'input', 'feature', 'product', 'read_subject'}))
        except (ValueError, KeyError, OSError):
            return False

    def validate_report(self, context, form, original_schema):
        validate_form(form, original_schema, lambda ref, ns: self.resolve(context, ref, ns))
        facts = self.facts(context, {})
        for name, declared in plain(original_schema).get('properties', {}).items():
            source = declared.get('x-source')
            if source in facts and form[name] != facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')

    def project_credit(self, context, receiver_selection):
        if self.native_rna_structure_results is not None and self.native_rna_structure_results.applies(context):
            return self.native_rna_structure_results.credit_view(context, receiver_selection)
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            return self.native_blast_standard_database_results.credit_view(context, receiver_selection)
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            return self.native_blast_database_results.credit_view(context, receiver_selection)
        if self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context):
            return self.native_hmmer_preparation_results.credit_view(context, receiver_selection)
        if self.native_infernal_preparation_results is not None and self.native_infernal_preparation_results.applies(context):
            return self.native_infernal_preparation_results.credit_view(context, receiver_selection)
        if self.native_blast_results is not None and self.native_blast_results.applies(context):
            return self.native_blast_results.credit_view(context, receiver_selection)
        if self.native_infernal_results is not None and self.native_infernal_results.applies(context):
            return self.native_infernal_results.credit_view(context, receiver_selection)
        if self.native_hmmer_results.applies(context):
            return self.native_hmmer_results.credit_view(context, receiver_selection)
        if context.role in {'launch_local', 'launch_hpc'}:
            return self._delegate(context).credit_view(context, receiver_selection)
        if context.role == 'launch_api' or context.role == 'results' and self._target(context)['resource_kind'] == 'api':
            return self.api_execution.credit_view(context, receiver_selection)
        selected, handoffs, results = self._received(context, receiver_selection)
        handoffs = {ref: target for ref, target in handoffs.items()
            if self.job_progress_provider.targets.usable_handoff(target)}
        initial = set(selected['initial_known_record_refs'])
        baseline = {(target['resource_id'], target['execution_id']) for ref, target in handoffs.items() if ref in initial}
        identities = {(target['resource_id'], target['execution_id']) for target in handoffs.values()}
        handoff_count = len(identities-baseline) if context.role == 'launch' else 0
        seen, acquired_count = set(), 0
        for reference, body in sorted(results.items(), key=lambda item: (item[0] not in initial, item[0])):
            if not body['windows']:
                continue
            contribution = (body['target']['resource_id'], body['target']['execution_id'], tuple(sorted(
                (window['path'], window['offset'], window['returned_bytes'], digest(window['bytes_base64']))
                for window in body['windows'])))
            if context.role == 'results' and contribution not in seen and reference not in initial:
                acquired_count += 1
            seen.add(contribution)
        credit = self.handoff_unit*handoff_count + self.acquired_record_unit*acquired_count
        return {'credit': credit, 'operational_credit': credit, 'new_handoff_count': handoff_count,
            'new_acquired_record_count': acquired_count, 'operational_credit_binding': {
                'version': 'execution_received_records_credit_v1', 'handoff_unit': self.handoff_unit,
                'acquired_record_unit': self.acquired_record_unit,
                'qualification': 'original_request_resource_scope_selector_and_actual_received_unique_information'}}

    def credit_view(self, context, receiver_selection):
        return self.project_credit(context, receiver_selection)

    def _native_results_complete(self, context, bodies):
        if is_native_rna_structure_target(self._target(context)):
            return False  # RNA's original requested qualified delivery owns its endpoint.
        if is_standard_blast_database_target(self._target(context)):
            return False  # Only its original frozen publication proves this endpoint.
        if is_native_blast_database_target(self._target(context)):
            return False  # Only its original frozen publication proves this endpoint.
        if not bodies:
            return False
        closed = [body for body in bodies if body['observation']['state'] == 'completed'
                  and body['observation']['returncode'] == 0]
        if not closed:
            return False
        target = self._target(context)
        requested = self._windows(self._selector(plain(context.assignment), target))
        for path, (start, length) in requested.items():
            # A pre-terminal read remains useful partial custody. Completion
            # here establishes requested acquisition alongside a successful
            # exact attempt observation; current files have no verified
            # producing-attempt identity or common atomic version.
            windows = [window for body in closed for window in body['windows'] if window['path'] == path]
            if not windows:
                return False
            end = max(window['size_bytes'] for window in windows)
            if length is not None:
                end = min(end, start+length)
            cursor = start
            for window in sorted(windows, key=lambda item: item['offset']):
                if window['offset'] > cursor:
                    return False
                cursor = max(cursor, window['offset']+window['returned_bytes'])
            if cursor < end:
                return False
        return True

    def _proof_for_action(self, context, operation_key):
        if self.native_rna_structure_results is not None and self.native_rna_structure_results.applies(context):
            proof = self.native_rna_structure_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            proof = self.native_blast_standard_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            proof = self.native_blast_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        prefix = context.run_id+':'+context.episode_id+':'
        index = operation_key.removeprefix(prefix)
        if (not operation_key.startswith(prefix) or not index.isdecimal()
                or str(int(index)) != index):
            return None
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? '
            'AND decision_index=?', (context.run_id, context.episode_id, int(index))).fetchone()
        if row is None or row['result'] is None:
            return None
        result = json.loads(row['result'])
        if result.get('status') != 'completed':
            return None
        if context.role == 'launch':
            qualified = []
            for reference in result.get('record_refs', []):
                try:
                    target = self.job_progress_provider.targets.read_target(reference, context.scope)
                    self._context_target(context, target)
                    if self.job_progress_provider.targets.usable_handoff(target):
                        qualified.append(reference)
                except (ValueError, KeyError):
                    pass
            complete = bool(qualified)
            keys, endpoint = ['received_usable_handoff'], 'usable_handoff'
        else:
            # Only windows actually returned by this completed own action and
            # preceding received records may establish the acquisition endpoint.
            bodies = []
            rows = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
                'AND decision_index<=? AND result IS NOT NULL ORDER BY decision_index',
                (context.run_id, context.episode_id, int(index)))
            for earlier in rows:
                outcome = json.loads(earlier[0])
                if outcome.get('status') != 'completed':
                    continue
                for reference in outcome.get('record_refs', []):
                    body = self._read_result(reference, context.scope)
                    if body is not None and body['assignment'] == plain(context.assignment):
                        bodies.append(body)
            complete = self._native_results_complete(context, bodies)
            keys = ['requested_filesystem_acquisition', 'successful_exact_attempt_observed',
                    'attempt_output_version_unverified']
            endpoint = 'usable_handoff'
        if not complete:
            return None
        receipt = {'action': json.loads(row['action']), 'outcome': result,
            'endpoint': endpoint, 'validation_keys': keys}
        if context.role == 'results':
            receipt['supporting_receipt_sha256s'] = [digest(body) for body in bodies]
        return {'version': 'practical_completion_v1', 'run_id': context.run_id,
            'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment),
            'endpoint': endpoint, 'operation_key': operation_key, 'receipt_sha256': digest(receipt),
            'validation_keys': keys}

    def completion_for_action(self, context, operation_key):
        if self.native_rna_structure_results is not None and self.native_rna_structure_results.applies(context):
            proof = self.native_rna_structure_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            proof = self.native_blast_standard_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            proof = self.native_blast_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if context.role in ROLE_KINDS:
            return self._delegate(context).completion_for_action(context, operation_key)
        if context.role == 'results' and self._target(context)['resource_kind'] == 'api':
            return self.api_execution.completion_for_action(context, operation_key)
        if self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context):
            proof = self.native_hmmer_preparation_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_infernal_preparation_results is not None and self.native_infernal_preparation_results.applies(context):
            proof = self.native_infernal_preparation_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_results is not None and self.native_blast_results.applies(context):
            proof = self.native_blast_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_infernal_results is not None and self.native_infernal_results.applies(context):
            proof = self.native_infernal_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_hmmer_results.applies(context):
            proof = self.native_hmmer_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        return self._proof_for_action(context, operation_key)

    def verify_completion(self, context, proof):
        try:
            proof = validate_completion_proof(plain(proof))
        except (ValueError, TypeError):
            return False
        if self.native_rna_structure_results is not None and self.native_rna_structure_results.applies(context):
            return proof == self.native_rna_structure_results.completion(context)
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            return proof == self.native_blast_standard_database_results.completion(context)
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            return proof == self.native_blast_database_results.completion(context)
        if context.role in {'launch_local', 'launch_hpc'}:
            return self.state(context).verify_completion(proof)
        if context.role == 'launch_api' or context.role == 'results' and self._target(context)['resource_kind'] == 'api':
            return self.api_execution.verify_completion(context, proof)
        if self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context):
            return proof == self.native_hmmer_preparation_results.completion(context)
        if self.native_infernal_preparation_results is not None and self.native_infernal_preparation_results.applies(context):
            return proof == self.native_infernal_preparation_results.completion(context)
        if self.native_blast_results is not None and self.native_blast_results.applies(context):
            return proof == self.native_blast_results.completion(context)
        if self.native_infernal_results is not None and self.native_infernal_results.applies(context):
            return proof == self.native_infernal_results.completion(context)
        if self.native_hmmer_results.applies(context):
            return proof == self.native_hmmer_results.completion(context)
        return bool(proof and canonical(proof) == canonical(self._proof_for_action(context, proof.get('operation_key', ''))))

    def practical_estimator(self, context):
        if context.role in {'launch_local', 'launch_hpc'}:
            return self._delegate(context).practical_estimator(context)
        from .practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof))


__all__ = ['ExecutionEpisodes', 'VERSION', 'LAUNCH_VERSION', 'RESULTS_VERSION', 'RESULTS_SCHEMA',
           'launch_operation_catalog', 'native_result_operation_catalog']
