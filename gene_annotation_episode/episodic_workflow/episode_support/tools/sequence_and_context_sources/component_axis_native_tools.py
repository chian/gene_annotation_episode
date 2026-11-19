"""A107 HPC component requests and receipt handling."""
from copy import deepcopy
import json

from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import ContractError, canonical, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_and_context_sources.component_axis_native_contracts import VERSION, OPERATIONS, tool_catalog
from gene_annotation_episode.episodic_workflow.episode_support.jobs.sequence_and_context_sources.component_axis_native_hpc import (MAX_INPUT_BYTES, RESULT_PROVIDER,
    STATUS_PROVIDER, require, freeze, commission, read, receive, publish, sha)


class ComponentNativeHPCMixin:
    def __init__(self, *args, **kwargs):
        self.component_native_resources = None
        super().__init__(*args, **kwargs)
    def configure_component_native_hpc(self, resources):
        resources = plain(resources)
        require(any(row.get('kind') == 'pbs_ssh' for row in resources.values()), 'configured_hpc_resource_required')
        require(self.component_native_resources is None or self.component_native_resources == resources,
            'hpc_resource_configuration_changed')
        for binding in self.a107_detection_bindings:
            require(binding['resource_id'] in resources and resources[binding['resource_id']].get('kind') == 'pbs_ssh',
                'a107_detector_resource_not_configured')
        self.component_native_resources = deepcopy(resources)

    def component_native_catalog(self):
        if self.component_native_resources is None:
            return {}
        entries = tool_catalog('A107')
        resource_ids = sorted(name for name, resource in self.component_native_resources.items()
            if resource.get('kind') == 'pbs_ssh')
        for contract in entries.values():
            resource = contract['input_schema']['properties']['resource_id']
            resource.update(enum=resource_ids, description=
                'Choose a configured remote PBS resource ID from this enum. '
                'A local host observation ID does not identify an HPC resource. '
                'The tool resource label local describes request preparation; '
                'the scientific calculation executes on the selected remote resource.')
        from gene_annotation_episode.episodic_workflow.episode_support.jobs.sequence_and_context_sources.genomic_detection_hpc import catalog
        entries.update(catalog(self.a107_detection_bindings))
        return entries

    def catalog(self, scope=None):
        entries = super().catalog(scope=scope)
        extra = ComponentNativeHPCMixin.component_native_catalog(self)
        require(not set(entries).intersection(extra), 'duplicate_operation_name')
        return {**entries, **extra}

    def as_record(self):
        return {**super().as_record(), 'component_native_tools': {'version': VERSION,
            'hpc_resources': deepcopy(self.component_native_resources),
            'execution': 'frozen_inputs_to_hpc'}}

    def operation_resource_limits(self):
        parent = getattr(super(), 'operation_resource_limits', lambda: {})()
        names = list(ComponentNativeHPCMixin.component_native_catalog(self))
        inherited = parent.get('component_native_metadata', {}).get('tool_names', [])
        return {**parent, 'component_native_metadata': {'tool_names': list(dict.fromkeys([*inherited, *names])), 'cpu_threads': 1, 'native_jobs': 0,
            'max_input_transfer_bytes': MAX_INPUT_BYTES,
            'oversize_behavior': 'explicit_missing_large_file_staging_capability; no_silent_truncation'}}

    def received_hpc_attributions(self, context, known, *, hpc_result_reader):
        parent = getattr(super(), 'received_hpc_attributions', None)
        generated, needs = parent(context, known, hpc_result_reader=hpc_result_reader) if callable(parent) else ([], [])
        more, pending = receive(self, context, set(known) | set(generated), reader=hpc_result_reader)
        return [*generated, *more], [*needs, *pending]

    async def execute_async(self, name, args, *, scope=None, operation_key=None, permitted_record_refs=None):
        if name not in (OPERATIONS['A107'], 'partner.request_detection_hpc'):
            return await super().execute_async(name, args, scope=scope, operation_key=operation_key,
                permitted_record_refs=permitted_record_refs)
        try:
            axis = 'A107'
            contracts = ComponentNativeHPCMixin.component_native_catalog(self)
            require(name in contracts, 'native_operation_not_configured')
            validate_schema(args, contracts[name]['input_schema'])
            invocation = self._current_invocation.get()
            require(invocation is not None and invocation[2:] == (name, args, operation_key),
                'original_action_binding_required')
            context = invocation[0]
            require(self.store.validate_scope(scope) == plain(context.scope), 'original_action_scope_required')
            known = set(context.received_record_refs if permitted_record_refs is None else permitted_record_refs)
            require(known <= set(context.received_record_refs), 'explicit_received_inputs_required')
            resources = self.component_native_resources
            require(resources is not None and args['resource_id'] in resources
                and resources[args['resource_id']].get('kind') == 'pbs_ssh', 'configured_hpc_resource_required')
            with self.store.transaction():
                request_ref, body = freeze(self, args, context=context, known=known, invocation=invocation)
                retained = [(ref, row) for ref in sorted(known)
                    if (row := read(self.store, ref, RESULT_PROVIDER)) is not None
                    and row['logical_work_sha256'] == body['logical_work_sha256']
                    and self.store.scope_contains(plain(context.scope), row['scope'])]
                if retained:
                    records = [request_ref, *[ref for ref, _ in retained]]
                    result = {'request_ref': request_ref, 'execution_status': 'qualified_components_already_received',
                        'new_execution_requested': False, 'scientific_credit': None}
                else:
                    from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.partner_presence_evidence.hpc_commission_sources import publish as publish_commission
                    work = commission(body, resources)
                    commission_ref = publish_commission(self.store, work, scope=plain(context.scope), resources=resources)
                    records = [request_ref, commission_ref]
                    result = {'request_ref': request_ref, 'commission_source_ref': commission_ref,
                        'hpc_assignment': {'commission_source_ref': commission_ref},
                        'new_execution_requested': True, 'scientific_credit': None}
                outcome = {'status': 'completed', 'record_refs': records, 'changed_record_refs': [],
                    'feedback': None, 'result': result}
            return outcome
        except (ValueError, KeyError, OSError, TypeError) as error:
            if isinstance(error, ContractError) and error.detail.get('input_admission'):
                with self.store.transaction():
                    reference = publish(self.store, STATUS_PROVIDER, {'version': VERSION,
                        'axis': axis, 'scope': plain(context.scope), 'run_id': context.run_id, 'operation': name,
                        'target_ref': next(iter({row['target_ref'] for row in self.store.coverage(args['target_ref'])})),
                        'request_ref': None, 'hpc_result_ref': None, 'status': 'input_admission_unavailable',
                        'arguments_sha256': sha(canonical(args).encode()),
                        'witness_ref': error.detail['witness_ref'], 'required_artifact_ref': error.detail['required_artifact_ref'],
                        'failure': error.detail['failure'], 'scientific_credit': None})
                return {'status': 'unavailable', 'record_refs': [reference], 'changed_record_refs': [],
                    'result': None, 'feedback': {'code': str(error), 'detail': error.detail}}
            feedback = {'code': str(error)}
            if (isinstance(error, ContractError)
                    and str(error) == 'component_native_input_contract_mismatch'):
                feedback['detail'] = error.detail
            if str(error) == 'component_native_configured_hpc_resource_required':
                feedback.update(configured_hpc_resource_ids=sorted(name for name, resource in
                    (self.component_native_resources or {}).items() if resource.get('kind') == 'pbs_ssh'),
                    recovery='Select a configured remote PBS resource ID. Host observation IDs '
                        'and the preparation tool resource label local are different identifiers. '
                        'This rejection created no scientific result or job.')
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': feedback}

