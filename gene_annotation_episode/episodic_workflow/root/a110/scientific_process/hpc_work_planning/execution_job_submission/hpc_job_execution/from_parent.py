from __future__ import annotations
from .execution_contracts import ASSIGNMENT_SCHEMA
from .execution_contracts import GENERIC_REQUESTED_JOB_SCHEMA
from .execution_contracts import KINDS
from .execution_contracts import ROLE_KINDS
from .execution_contracts import checked
from .execution_contracts import deepcopy
from .execution_contracts import json
from .execution_contracts import plain
from .execution_contracts import _constraints
from .execution_contracts import _validate_request
from .execution_contracts import obj
from .execution_contracts import SELECTION_SCHEMA
from .execution_contracts import INPUT_VERSION_SCHEMA
from .execution_contracts import LAUNCH_VERSION

class NativeParentRequests:

    def _permitted(self, assignment, resource_id):
        constraints = assignment['constraints']
        kind = KINDS[self.resources[resource_id]['kind']]
        return resource_id in assignment['requests'] and ('allowed_resource_ids' not in constraints or resource_id in constraints['allowed_resource_ids']) and ('allowed_kinds' not in constraints or kind in constraints['allowed_kinds']) and ('resource_id' not in constraints or resource_id == constraints['resource_id']) and ('kind' not in constraints or kind == constraints['kind'])

    def _request_schema(self, resource_id, *, selected, internal=False, compact=True):
        kind = KINDS[self.resources[resource_id]['kind']]
        schema = deepcopy(ASSIGNMENT_SCHEMA)
        if schema.get('type') != 'object' or not isinstance(schema.get('properties'), dict):
            raise ValueError('concrete_execution_assignment_schema_required')
        schema['properties']['resource_id'] = {'type': 'string', 'const': resource_id}
        schema['properties']['resource_kind'] = {'type': 'string', 'const': kind}
        alternatives = []
        if internal and self.resources[resource_id].get('native_flux_balance'):
            from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_contracts import flux_balance_schema
            for binding in self.resources[resource_id]['native_flux_balance']:
                alternatives.append({'allOf': [flux_balance_schema('FBARequestedJob'), {'properties': {'native_flux_balance': {'properties': {'operation': {'const': binding['operation']}, 'mode': {'const': binding['mode']}, 'software': {'const': deepcopy(binding['software'])}, 'model_input': {'properties': {'format': {'enum': deepcopy(binding['model_formats'])}}}}}}}]})
        schema['properties']['requested_job'] = {'anyOf': [deepcopy(GENERIC_REQUESTED_JOB_SCHEMA), *alternatives]} if alternatives else deepcopy(GENERIC_REQUESTED_JOB_SCHEMA)
        if selected and 'resource_id' not in schema['required']:
            schema['required'].append('resource_id')
        if compact and kind == 'local' and self.resources[resource_id].get('native_flux_balance'):
            from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import resource_assignment_schema
            return {'anyOf': [schema, resource_assignment_schema(resource_id, selected=selected)]}
        return schema
    _validate_request = _validate_request

    def _launch(self, value, *, scope=None):
        from gene_annotation_episode.episodic_workflow.root.a110.library.execution_request_compatibility import launch_assignment_schema
        value = checked(value, launch_assignment_schema(self, True, _read_request_INPUT_VERSION_SCHEMA=lambda: INPUT_VERSION_SCHEMA, _read_request_LAUNCH_VERSION=lambda: LAUNCH_VERSION, _read_request_SELECTION_SCHEMA=lambda: SELECTION_SCHEMA, _read_request_deepcopy=lambda: deepcopy, _read_request_obj=lambda: obj), 'invalid_execution_launch_assignment')
        for resource_id, request in value['requests'].items():
            self._validate_request(request, resource_id=resource_id)
        self._constraints(value['constraints'])
        return value
    _constraints = staticmethod(_constraints)

    def child_assignment_schema(self, parent, role):
        if parent.role == 'launch' and any((ancestor == 'hpc' for ancestor, _ in parent.path)):
            assignment = plain(parent.assignment)
            requests = [request for resource_id, request in assignment['requests'].items() if self._permitted(assignment, resource_id) and request.get('resource_kind') == 'hpc']
            if not requests:
                raise ValueError('frozen_hpc_launch_request_missing')
            return {'type': 'object', 'enum': requests}
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        alternatives = [self._request_schema(key, selected=True, internal=internal) for key, config in self.resources.items() if KINDS[config['kind']] == ROLE_KINDS[role]]
        return {'anyOf': alternatives} if alternatives else {'not': {}}

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        if parent.role in ('hpc', 'hpc_execution') and False:
            pass
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        if False and is_compact_launch(selected):
            pass
        if False and is_compact_assignment(selected):
            pass
        selected = self._validate_request(selected)
        if ROLE_KINDS[role] != KINDS[self.resources[selected['resource_id']]['kind']]:
            raise ValueError('execution_resource_kind_conflict')
        if parent.role != 'launch':
            raise ValueError('resource_child_role_owned_by_launch')
        original = self._launch(plain(parent.assignment))
        self._flux_balance_inputs(parent, selected, input_versions=original['immutable_input_versions'])
        self._versions(original['immutable_input_versions'], scope, context=parent, flux_balance_assignments=[selected])
        return selected
