"""Original configured API assignments, constraints and operation catalogues."""
from __future__ import annotations

from copy import deepcopy

from .api_hmmer_protocol import PROVIDER as LEGACY_PROVIDER
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import API_ASSIGNMENT_SCHEMA, checked, validate_api_assignment


class APIServiceAssignments:
    def assignment_schema(self, resource_id):
        if resource_id not in self.configuration:
            raise ValueError('api_resource_not_bound')
        if resource_id not in self.services:
            schema = deepcopy(API_ASSIGNMENT_SCHEMA)
        else:
            from gene_annotation_episode.execution_contracts import API_SERVICE_ASSIGNMENT_SCHEMA
            schema = deepcopy(API_SERVICE_ASSIGNMENT_SCHEMA)
            schema['properties']['service'] = {'const': self.services[resource_id].service}
            schema['properties']['request'] = deepcopy(self.services[resource_id].request_schema)
        schema['properties']['resource_id'] = {'type': 'string', 'const': resource_id}
        return schema

    def validate_assignment(self, assignment, *, scope=None):
        assignment = validate_api_assignment(plain(assignment))
        resource_id = assignment['resource_id']
        schema = self.assignment_schema(resource_id)
        checked(assignment, schema, 'api_service_assignment_conflict')
        if resource_id not in self.services:
            self._legacy_binding()._constraints(assignment)
            if scope is not None:
                self.tools._check_sequence_operand(assignment['subject_ref'], plain(scope))
        else:
            service = self.services[resource_id]
            service.validate_request(assignment['request'], plain(scope) if scope is not None else None)
            if service.service == 'bvbrc_appservice' and assignment['request'].get('required_application_id') == 'ComparativeSystems':
                from .library.bvbrc_comparative_systems_tool_info import validate_comparative_request
                validate_comparative_request(assignment['request'])
            for key, value in assignment['constraints'].items():
                if key == 'allowed_resource_ids':
                    valid = isinstance(value, list) and resource_id in value
                elif key == 'allowed_kinds':
                    valid = isinstance(value, list) and 'api' in value
                elif key == 'kind':
                    valid = value == 'api'
                elif key in {'resource_id', 'service', 'request', 'endpoint'}:
                    valid = value == assignment[key]
                else:
                    valid = False
                if not valid:
                    raise ValueError('api_service_constraint_conflict:'+key)
        return assignment

    def capabilities(self, resource_id):
        if resource_id in self.services:
            return self.services[resource_id].capabilities()
        # Legacy schemas are fixed and do not require an invented query.
        return [{'name': name} for name in ('api.hmmer.databases', 'api.hmmer.prepare',
            'api.hmmer.submit', 'api.hmmer.status', 'api.hmmer.check_handoff')]

    def operation_contracts(self, resource_id, role):
        """Actual configured service contracts; no query or target is fabricated."""
        if resource_id not in self.configuration:
            raise ValueError('api_resource_not_bound')
        if role not in {'launch_api', 'results'}:
            raise ValueError('api_execution_role_required')
        if resource_id not in self.services:
            from .api_hmmer_protocol import hmmer_operation_catalog
            return hmmer_operation_catalog(role)
        service = self.services[resource_id]
        if service.service == 'bvbrc_appservice':
            from gene_annotation_episode.bvbrc_appservice_tool_info import bvbrc_appservice_tool_contracts
            return [{key: deepcopy(row[key]) for key in ('name', 'description', 'input_schema', 'instructions')}
                for row in bvbrc_appservice_tool_contracts(resource_id=resource_id)
                if any(route['resource_role'] == role for route in row['invocation_route']['routes'])]
        entries = (service.capabilities() if role == 'launch_api'
                   else service.result_capabilities())
        return [{key: deepcopy(row[key]) for key in ('name', 'description', 'input_schema', 'instructions') if key in row}
                for row in entries]

    def _legacy_context(self, context):
        if context.role == 'results':
            return self.store.get(context.assignment['handoff_ref']).get('provider') == LEGACY_PROVIDER
        return plain(context.assignment).get('version') == 'api_execution_assignment_v1'

    def _context(self, context, *, verify_artifacts=True, _enrichr_history=None):
        if context.run_id != self.run_id:
            raise ValueError('api_execution_run_conflict')
        if context.role == 'launch_api':
            if _enrichr_history is not None:
                raise ValueError('enrichr_original_context_conflict')
            assignment = self.validate_assignment(context.assignment, scope=context.scope)
            return assignment, self.services[assignment['resource_id']], None
        if context.role != 'results':
            raise ValueError('api_execution_role_required')
        raw = plain(context.assignment)
        if set(raw) != {'version', 'handoff_ref', 'selector'} or raw['version'] != 'execution_results_assignment_v1':
            raise ValueError('invalid_api_results_assignment')
        target = self.read_target(raw['handoff_ref'], context.scope,
            verify_artifacts=verify_artifacts, _enrichr_history=_enrichr_history)
        self.validate_result_selector(target, raw['selector'])
        return target['assignment'], self.services[target['resource_id']], target

    def validate_result_selector(self, target, selector):
        if target['assignment'].get('version') == 'api_execution_assignment_v1':
            schema = {'type': 'object', 'properties': {'page': {'type': 'integer', 'minimum': 1},
                'page_size': {'type': 'integer', 'minimum': 1}},
                'required': ['page'], 'additionalProperties': False}
        else:
            self.validate_assignment(target['assignment'], scope=target['scope'])
            schema = self.services[target['resource_id']].selector_schema
        value = checked(selector, schema, 'invalid_api_service_result_selector')
        if target['assignment'].get('version') != 'api_execution_assignment_v1':
            self.services[target['resource_id']].result_catalog(target['assignment']['request'], value)
        return value

    def initialize(self, context):
        if self._legacy_context(context):
            return self._legacy_binding().initialize(context)
        selected = None
        if any(bound.service == 'uniprot' for bound in self.services.values()):
            original = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
            selected = self.uniprot_returns._selection(context, original)
        closed_target = self.closed_enrichr_target(context)
        if closed_target is None:
            _, service, _ = self._context(context)
        else:
            service = self.services[closed_target['resource_id']]
            self.validate_result_selector(closed_target, plain(context.assignment)['selector'])
        if selected is not None and selected['pages']:
            self.uniprot_returns._require(service.service == 'uniprot', 'original_context_conflict')
        if any(bound.service == 'enrichr' for bound in self.services.values()):
            schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
            if self.enrichr_returns.validate_fields(context, schema):
                self.enrichr_returns._require(service.service == 'enrichr', 'original_context_conflict')
        if self.appservice.owns_context(context):
            self.appservice.validate_assignment(context)
        self._manifest(context, create=closed_target is None)
        return {'assignment': plain(context.assignment), 'scope': plain(context.scope)}

    def catalog(self, context):
        if self._legacy_context(context):
            return self._legacy_binding().catalog(context)
        assignment, service, target = self._context(context)
        if service.service == 'rfam_batch' and target is None:
            return service.available_launch_catalog(assignment['request'], self._events(context.episode_id))
        return (service.launch_catalog(assignment['request']) if target is None else
                service.result_catalog(assignment['request'], plain(context.assignment)['selector']))

