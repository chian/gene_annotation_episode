"""Ports from a specialist binding to the existing application services.

This adapter owns no decisions, execution loop, credit formula or work policy.
It keeps bindings independent of Workflow/DecisionSource implementation types.
"""
from __future__ import annotations

import inspect
import json

from .communication import plain


class WorkflowServices:
    def __init__(self, workflow):
        self.workflow = workflow

    def tool_catalog(self, scope):
        catalog = self.workflow.tools.catalog(scope=plain(scope))
        return ([{'name': name, **item} for name, item in catalog.items()]
                if isinstance(catalog, dict) else list(catalog))

    async def execute_tool(self, name, arguments, *, scope, operation_key):
        tools = self.workflow.tools
        dispatch = getattr(tools, 'execute_async', tools.execute)
        result = dispatch(name, plain(arguments), scope=plain(scope), operation_key=operation_key)
        return await result if inspect.isawaitable(result) else result

    def read_record(self, reference):
        return self.workflow.store.get(reference)

    def reference_in_scope(self, reference, scope, namespace):
        store = self.workflow.store
        if not store.reference_subset([reference], plain(scope)):
            provider = getattr(self.workflow, 'progress_provider', None)
            return bool(provider is not None and provider.resolve(reference, plain(scope), namespace))
        kind = store.get(reference)['record_type']
        return (not namespace or namespace == kind or namespace == 'subject'
                and kind in {'input', 'feature', 'product', 'read_subject'})

    def reference_in_context(self, context, reference, namespace):
        if context.run_id != self.workflow.run_id:
            raise ValueError('context_reference_receiver_identity_mismatch')
        native = getattr(self.workflow, 'native_event_information', None)
        if native is not None and native.resolve(context, reference, namespace):
            return True
        if namespace == 'native_event_target':
            return False
        return self.reference_in_scope(reference, context.scope, namespace)

    def scientific_credit(self, context, receiver_selection):
        workflow = self.workflow
        local = workflow.project_child_credit is not None and len(context.path) > 1
        projector = workflow.project_child_credit if local else workflow.project_credit
        arguments = {}
        if local:
            request = context.request
            contract = request['report_contract']
            arguments.update(assignment={
                'goal': plain(request['goal']), 'scope': plain(context.scope),
                'purpose': contract['decision'],
                'schema': plain(contract['measurements']['schema']),
                'initial_report': plain(request['message']['initial_report'])},
                episode_id=context.episode_id, run_id=context.run_id)
        if getattr(projector, 'requires_episode_receipts', False):
            arguments['known_assessment_refs'] = workflow.receipts.known(
                context.episode_id, record_type='assessment')
        return workflow.projection_view(projector, plain(context.scope), **arguments)

    def scientific_support_routes(self, context, *, observation_kinds):
        """Describe the actual separate annotation binding without projecting it."""
        if context.run_id != self.workflow.run_id:
            raise ValueError('scientific_support_routes_receiver_identity_mismatch')
        from .scientific_support_metadata import annotation_policy_routes
        return annotation_policy_routes(self.workflow.project_annotation_score,
            self.workflow.annotation_score_binding, observation_kinds=observation_kinds)

    def bound_role_credit(self, context, receiver_selection):
        bindings = getattr(self.workflow, 'role_credit_projectors', {})
        if context.role not in bindings:
            raise ValueError('explicit_role_credit_binding_required:' + context.role)
        return bindings[context.role](context, receiver_selection)

    def capabilities(self):
        return tuple(getattr(self.workflow, 'resource_capabilities', ()))

    def public_search_ports(self, registry):
        from .resource_service_setup import bind_public_search_ports
        return bind_public_search_ports(self.workflow.store, self.workflow.tools,
            registry=plain(registry))

    async def observe_progress(self, target_handle, requested_fields, scope, *,
                         permitted_committed_record_types=(), operation_key=None):
        provider = getattr(self.workflow, 'progress_provider', None)
        if provider is None:
            raise ValueError('episode_progress_provider_not_bound')
        return await provider.observe_async(target_handle, requested_fields, plain(scope),
            permitted_committed_record_types=permitted_committed_record_types,
            operation_key=operation_key)

    def dependencies(self, target_handle, scope):
        provider = getattr(self.workflow, 'progress_provider', None)
        if provider is None:
            raise ValueError('episode_progress_provider_not_bound')
        return tuple(provider.direct_dependencies(target_handle, plain(scope)))

    def read_progress(self, reference, scope):
        provider = getattr(self.workflow, 'progress_provider', None)
        if provider is None:
            raise ValueError('episode_progress_provider_not_bound')
        return provider.read_progress(reference, plain(scope))

    def received_progress_refs(self, episode_id):
        provider = getattr(self.workflow, 'progress_provider', None)
        return [] if provider is None else provider.received_progress_refs(episode_id)

    def progress_selection(self, context):
        if context.run_id != self.workflow.run_id:
            raise ValueError('progress_selection_receiver_identity_mismatch')
        return self.workflow.progress_selection(context)

    def record_selection(self, context):
        if context.run_id != self.workflow.run_id:
            raise ValueError('record_selection_receiver_identity_mismatch')
        return self.workflow.record_selection(context.episode_id)

    def _scientific_provenance(self, context):
        if context.run_id != self.workflow.run_id:
            raise ValueError('scientific_provenance_receiver_identity_mismatch')
        provenance = self.workflow.scientific_provenance
        if provenance is None:
            raise ValueError('scientific_process_provenance_unavailable')
        return provenance

    def scientific_preparation(self, context, preparation_ref, *, owner='self'):
        return self._scientific_provenance(context).preparation(
            context, preparation_ref, owner=owner)

    def scientific_received_results(self, context):
        return self._scientific_provenance(context).received_results(context)

    def scientific_parent_invocation(self, context):
        return self._scientific_provenance(context).parent_invocation(context)

    def scientific_reference(self, context, reference, namespace):
        return self._scientific_provenance(context).resolve(context, reference, namespace,
            credit_metadata=self.workflow.source_controller_credit(context))

    def own_outcomes(self, episode_id, *, tools, offset, limit):
        if (type(offset) is not int or offset < 0 or type(limit) is not int or limit < 1
                or tools is not None and (not isinstance(tools, (tuple, list))
                    or any(not isinstance(name, str) for name in tools))):
            raise ValueError('explicit_outcome_page_required')
        clauses = ['run_id=?', 'episode_id=?', 'result IS NOT NULL']
        arguments = [self.workflow.run_id, episode_id]
        if tools is not None:
            clauses.append("json_extract(action,'$.tool') IN (SELECT value FROM json_each(?))")
            arguments.append(json.dumps(list(tools)))
        rows = self.workflow.store.db.execute("SELECT decision_index, "
            "json_extract(action,'$.tool') AS selected_tool, "
            "json_extract(result,'$.status') AS status, "
            "json_extract(result,'$.record_refs') AS record_refs, "
            "json_extract(result,'$.changed_record_refs') AS changed_record_refs "
            ", json_extract(result,'$.progress_refs') AS progress_refs "
            'FROM runtime_actions WHERE ' + ' AND '.join(clauses)
            + ' ORDER BY decision_index LIMIT ? OFFSET ?', (*arguments, limit + 1, offset))
        values = list(rows)
        records = [{'decision_index': row['decision_index'], 'selected_tool': row['selected_tool'],
            'status': row['status'], 'record_refs': json.loads(row['record_refs'] or '[]'),
            'changed_record_refs': json.loads(row['changed_record_refs'] or '[]'),
            'progress_refs': json.loads(row['progress_refs'] or '[]'),
            # Exact bodies remain addressable through the existing own-history
            # operation by decision_index. No nonexistent semantic ID is made.
            'result_ref': None} for row in values[:limit]]
        return {'records': records, 'offset': offset, 'limit': limit,
                'next_offset': offset + limit if len(values) > limit else None}
