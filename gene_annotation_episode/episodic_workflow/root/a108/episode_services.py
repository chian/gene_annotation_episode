"""Ports from a specialist binding to the existing application services.

This adapter owns no decisions, execution loop, credit formula or work policy.
It keeps bindings independent of Workflow/DecisionSource implementation types.
"""
from __future__ import annotations
import inspect
import json
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.a108.communication import plain
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.a108.episode_bindings import native_observation_options

class WorkflowServices:

    def __init__(self, workflow):
        self.workflow = workflow

    def tool_invocation(self, context, *, tool_name, arguments, operation_key):
        return self.workflow.tools.current_invocation(context, tool_name=tool_name, arguments=arguments, operation_key=operation_key)

    def create_tool_knowledge(self, directory):
        from gene_annotation_episode.episodic_workflow.root.a108.tool_knowledge import ToolKnowledge
        return ToolKnowledge.freeze(directory, source=getattr(self.workflow.tools, 'knowledge_library_directory', None))

    def create_launch_instructions(self, directory):
        from gene_annotation_episode.episodic_workflow.root.a108.launch_instructions import LaunchInstructions
        return LaunchInstructions.freeze(directory, source=getattr(self.workflow.tools, 'launch_instruction_library_directory', None))

    def scientific_library_catalog(self):
        binding = getattr(self.workflow, 'sample_context_evidence_binding', None)
        callback = getattr(binding, 'scientific_library_catalog', None)
        if callable(callback):
            return callback()
        from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence_library import catalog
        return catalog()

    def scientific_retriever_catalog(self, binding):
        callback = getattr(binding, 'scientific_retriever_catalog', None)
        if callable(callback):
            return callback()
        from gene_annotation_episode.episodic_workflow.root.a108.scientific_tool_library import catalog
        configuration = binding.tool_retrieval
        return catalog(retrieval_mode=None if configuration is None else configuration['mode'], tool_info=binding.tool_library.supports_tool_info)

    def create_tool_retriever(self, binding, *, provider):
        callback = getattr(binding, 'create_tool_retriever', None)
        if callable(callback):
            return callback(store=self.workflow.store, run_id=self.workflow.run_id, provider=provider)
        from gene_annotation_episode.episodic_workflow.root.a108.scientific_tool_retrieval import ScientificToolRetriever
        return ScientificToolRetriever(self.workflow.store, run_id=self.workflow.run_id, provider=provider, library=binding.tool_library, configuration=binding.tool_retrieval)

    def execute_scientific_library(self, context, name, arguments):
        binding = self.workflow.sample_context_evidence_binding
        callback = getattr(binding, 'execute_scientific_library', None)
        if callable(callback):
            return callback(context, name, arguments)
        return self.workflow.sample_context_evidence_binding.library.execute(name, arguments)

    def create_receipts(self, run_id):
        from gene_annotation_episode.episodic_workflow.root.a108.episode_receipts import EpisodeReceipts
        return EpisodeReceipts(self.workflow.store, run_id)

    def instructions(self, source, context):
        composer = getattr(type(source), 'instruction_composer', None)
        if callable(composer):
            return composer(source, context)
        from gene_annotation_episode.episodic_workflow.root.a108.runtime_prompt import instructions
        return instructions(source, context)

    def reasoning_commit_requirement(self):
        from gene_annotation_episode.episodic_workflow.root.a108.runtime_prompt import REASONING_COMMIT_REQUIREMENT
        return REASONING_COMMIT_REQUIREMENT

    def decision_exchange_instructions(self):
        from gene_annotation_episode.episodic_workflow.root.a108.decision_protocol_prompt import INSTRUCTIONS
        return INSTRUCTIONS

    def literature_numerical_contracts(self):
        from gene_annotation_episode.episodic_workflow.root.a108.library import literature_numerical_contracts
        return literature_numerical_contracts

    def tool_catalog(self, scope):
        catalog = self.workflow.tools.catalog(scope=plain(scope))
        return [{'name': name, **item} for name, item in catalog.items()] if isinstance(catalog, dict) else list(catalog)

    def tool_information_catalog(self, scope) -> list[dict]:
        """Describe direct tools and resource operations the child can commission.

        The direct registry remains unchanged. Only explicitly bound episodes
        declare resource contracts; source-library information is not a route.
        """
        from gene_annotation_episode.episodic_workflow.root.a108.resource_tool_information import bound_resource_tool_contracts, tool_information_contracts
        registry = self.workflow.episode_bindings
        scientific = self.workflow.sample_context_evidence_binding
        child_roles = () if scientific is None else scientific.child_roles('sample_context_evidence')
        resources, seen = ([], set())
        for role in registry.roles:
            binding = registry.for_role(role)
            if id(binding) in seen:
                continue
            seen.add(id(binding))
            for row in bound_resource_tool_contracts(binding):
                routes = [route for route in row['invocation_route']['routes'] if route['entry_role'] in child_roles and registry.for_role(route['entry_role']) is binding and (registry.for_role(route['resource_role']) is binding)]
                if routes:
                    resources.append({**row, 'invocation_route': {'kind': 'commission', 'routes': routes}})
        return tool_information_contracts(self.tool_catalog(scope), resources)

    async def execute_tool(self, name, arguments, *, scope, operation_key, permitted_record_refs=None):
        tools = self.workflow.tools
        dispatch = getattr(tools, 'execute_async', tools.execute)
        authorization = {'permitted_record_refs': tuple(permitted_record_refs)} if permitted_record_refs is not None else {}
        result = dispatch(name, plain(arguments), scope=plain(scope), operation_key=operation_key, **authorization)
        return await result if inspect.isawaitable(result) else result

    def authenticate_source_byte_operands(self, context: BindingContext, tool_name: str, arguments: dict) -> None:
        """Authenticate received source/material records and selected representations."""
        from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError
        from gene_annotation_episode.episodic_workflow.root.a108.source_bytes import source_window_selection
        from gene_annotation_episode.episodic_workflow.root.a108.source_locations import received_source
        if context.run_id != self.workflow.run_id:
            raise ContractError('source_byte_context_run_mismatch')
        store = self.workflow.store
        if tool_name in {'material.parse', 'material.read'}:
            material = store._require(arguments['material_ref'], {'material'})
            source = store._require(material['source_ref'], {'source'})
        else:
            source = store._require(arguments['source_ref'], {'source'})
        if tool_name == 'source.read':
            artifact_ref, _, _ = source_window_selection(source, arguments.get('representation', 'text'))
        elif tool_name == 'source.locate':
            artifact_ref = received_source(store, source['id'], arguments['representation'], permitted_inputs=context.received_record_refs, scope=plain(context.scope))['id']
        else:
            artifact_ref = source['artifact_ref']

    def read_record(self, reference):
        return self.workflow.store.get(reference)

    def supplied_context_preview(self, context, *, limit=12000):
        """Present received caller input before a parent defines a child question.

        This is original task input, not acquired evidence or a generated
        interpretation. A partial preview retains a source handle for reading.
        """
        store = self.workflow.store
        reference = store.problem().get('caller_context_source_ref')
        if reference is None or reference not in context.received_record_refs or (not self.reference_in_scope(reference, context.scope, 'source')):
            return []
        source = store.get(reference)
        body = store.get_artifact(source['artifact_ref'])
        preview = body[:limit].decode('utf-8', errors='ignore')
        return [{'source_ref': reference, 'origin': 'caller', 'representation': 'original', 'content_preview': preview, 'utf8_bytes': len(body), 'complete': len(preview.encode('utf-8')) == len(body)}]

    def reference_in_scope(self, reference, scope, namespace):
        store = self.workflow.store
        if namespace in {'execution_handle', 'execution'}:
            provider = getattr(self.workflow, 'progress_provider', None)
            return bool(provider is not None and provider.resolve(reference, plain(scope), namespace))
        if not store.reference_subset([reference], plain(scope)):
            provider = getattr(self.workflow, 'progress_provider', None)
            return bool(provider is not None and provider.resolve(reference, plain(scope), namespace))
        kind = store.get(reference)['record_type']
        return not namespace or namespace == kind or (namespace == 'subject' and kind in {'input', 'feature', 'product', 'read_subject'})

    def reference_in_context(self, context, reference, namespace):
        if context.run_id != self.workflow.run_id:
            raise ValueError('context_reference_receiver_identity_mismatch')
        received = self.workflow.episode_bindings.resolve_received_reference(context, reference, namespace)
        if received is not None:
            return received
        return self.reference_in_scope(reference, context.scope, namespace)

    def annotation_task_required(self):
        return bool(getattr(self.workflow.project_credit, 'task_credit', False))

    def proposed_annotation_for(self, context):
        """Use the task's original assignment, including an ancestor commission."""
        reference = context.assignment.get('proposed_annotation_ref')
        if reference is not None:
            return reference
        for length in range(len(context.path) - 1, 0, -1):
            identity = EpisodeRef(context.run_id, context.path[:length]).episode_id
            row = self.workflow.journal.row('runtime_episodes', identity)
            if row is None:
                continue
            assignment = json.loads(row['request'])['message'].get('episode_assignment', {})
            reference = assignment.get('proposed_annotation_ref')
            if reference is not None:
                return reference
        return None

    def scientific_credit(self, context, receiver_selection):
        from .library.standalone_scientific_credit import scientific_credit
        return scientific_credit(self, context, receiver_selection)

    def scientific_credit_for(self, invocation, context, receiver_selection):
        current = self.scientific_credit
        if getattr(current, '__func__', None) is not _DEFAULT_SCIENTIFIC_CREDIT:
            return current(context, receiver_selection)
        return invocation(self, context, receiver_selection)

    def scientific_support_routes(self, context, *, observation_kinds):
        """Describe the actual separate annotation binding without projecting it."""
        if context.run_id != self.workflow.run_id:
            raise ValueError('scientific_support_routes_receiver_identity_mismatch')
        binding = getattr(self.workflow, 'sample_context_evidence_binding', None)
        callback = getattr(binding, 'scientific_support_routes', None)
        if callable(callback):
            return callback(self.workflow.project_annotation_score, self.workflow.annotation_score_binding, observation_kinds=observation_kinds)
        from gene_annotation_episode.episodic_workflow.root.a108.library.scientific_support_metadata import annotation_policy_routes
        return annotation_policy_routes(self.workflow.project_annotation_score, self.workflow.annotation_score_binding, observation_kinds=observation_kinds)

    def bound_role_credit(self, context, receiver_selection):
        bindings = getattr(self.workflow, 'role_credit_projectors', {})
        if context.role not in bindings:
            raise ValueError('explicit_role_credit_binding_required:' + context.role)
        return bindings[context.role](context, receiver_selection)

    def capabilities(self):
        return tuple(getattr(self.workflow, 'resource_capabilities', ()))

    def observe_progress(self, target_handle, requested_fields, scope, *, permitted_committed_record_types=(), operation_key=None, native_operation=None, observation_context=None):
        provider = getattr(self.workflow, 'progress_provider', None)
        if provider is None:
            raise ValueError('episode_progress_provider_not_bound')
        return provider.observe(target_handle, requested_fields, plain(scope), permitted_committed_record_types=permitted_committed_record_types, operation_key=operation_key, **native_observation_options(native_operation, observation_context))

    def describe_progress_target(self, target_handle, scope):
        provider = getattr(self.workflow, 'progress_provider', None)
        return None if provider is None else provider.describe_target(target_handle, plain(scope))

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
            raise ValueError('sample_context_evidence_provenance_unavailable')
        return provenance

    def create_scientific_provenance(self, binding):
        callback = getattr(binding, 'create_scientific_provenance', None)
        if callable(callback):
            return callback(store=self.workflow.store, journal=self.workflow.journal)
        from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence_provenance import SampleContextEvidenceProvenance
        return SampleContextEvidenceProvenance(self.workflow.store, self.workflow.journal, library=binding.library, tool_library=binding.tool_library)

    def scientific_preparation(self, context, preparation_ref):
        provenance = self._scientific_provenance(context)
        binding = getattr(self.workflow, 'sample_context_evidence_binding', None)
        callback = getattr(binding, 'read_scientific_preparation', None)
        if callable(callback):
            return callback(provenance, context, preparation_ref, owner='self')
        return provenance.preparation(context, preparation_ref)

    def scientific_parent_preparation(self, context, preparation_ref):
        provenance = self._scientific_provenance(context)
        binding = getattr(self.workflow, 'sample_context_evidence_binding', None)
        callback = getattr(binding, 'read_scientific_preparation', None)
        if callable(callback):
            return callback(provenance, context, preparation_ref, owner='parent')
        return provenance.parent_preparation(context, preparation_ref)

    def scientific_received_results(self, context):
        return self._scientific_provenance(context).received_results(context)

    def scientific_frozen_results(self, context):
        return self._scientific_provenance(context).frozen_results(context)

    def scientific_received_results_for(self, invocation, context):
        current = self.scientific_received_results
        if getattr(current, '__func__', None) is not _DEFAULT_SCIENTIFIC_RECEIVED_RESULTS:
            return current(context)
        provenance = self._scientific_provenance(context)
        current_read = provenance.received_results
        from .sample_context_evidence_provenance import _DEFAULT_RECEIVED_RESULTS
        if getattr(current_read, '__func__', None) is not _DEFAULT_RECEIVED_RESULTS:
            return current_read(context)
        return invocation(provenance, context)

    def scientific_frozen_results_for(self, invocation, context):
        current = self.scientific_frozen_results
        if getattr(current, '__func__', None) is not _DEFAULT_SCIENTIFIC_FROZEN_RESULTS:
            return current(context)
        provenance = self._scientific_provenance(context)
        current_read = provenance.frozen_results
        from .sample_context_evidence_provenance import _DEFAULT_FROZEN_RESULTS
        if getattr(current_read, '__func__', None) is not _DEFAULT_FROZEN_RESULTS:
            return current_read(context)
        return invocation(provenance, context)

    def scientific_saved_request_for(self, invocation, context, *, active_only=True):
        current = self.scientific_saved_request
        if getattr(current, '__func__', None) is not _DEFAULT_SCIENTIFIC_SAVED_REQUEST:
            return current(context, active_only=active_only)
        return invocation(self, context, active_only=active_only)

    def scientific_saved_request(self, context: BindingContext, *, active_only=True) -> dict | None:
        from .library.standalone_scientific_saved_request import scientific_saved_request
        return scientific_saved_request(self, context, active_only=active_only)

    def scientific_closed_request(self, context: BindingContext) -> dict | None:
        """Read one completed invocation, without creating work or loading its tree."""
        workflow = self.workflow
        journal = workflow.journal
        if context.run_id != workflow.run_id or journal.run_id != workflow.run_id or context.role != 'sample_context_evidence' or (EpisodeRef(context.run_id, context.path).episode_id != context.episode_id):
            raise ValueError('scientific_closed_request_identity_mismatch')
        row = journal.row('runtime_episodes', context.episode_id)
        if row is None:
            return None
        if row['run_id'] != context.run_id or row['episode_id'] != context.episode_id or json.loads(row['path']) != plain(context.path):
            raise ValueError('scientific_closed_request_identity_mismatch')
        if row['state'] != 'yielded' or row['completion'] is None or row['archive'] is None:
            return None
        closing = journal.row('runtime_forms', context.episode_id)
        if closing is None or closing['form'] is None:
            return None
        if closing['run_id'] != context.run_id or closing['episode_id'] != context.episode_id:
            raise ValueError('scientific_closed_request_identity_mismatch')
        completion, archive, form, request = (json.loads(value) for value in (row['completion'], row['archive'], closing['form'], row['request']))
        if not isinstance(completion, dict) or not completion or (not isinstance(archive, dict)) or (not archive) or (not isinstance(form, dict)) or (not isinstance(request, dict)):
            raise ValueError('scientific_closed_request_invalid')
        return request

    def scientific_parent_invocation(self, context):
        return self._scientific_provenance(context).parent_invocation(context)

    def scientific_parent_task(self, context):
        """Optionally read original scientific guidance without changing work."""
        if context.run_id != self.workflow.run_id:
            raise ValueError('scientific_provenance_receiver_identity_mismatch')
        provenance = getattr(self.workflow, 'scientific_provenance', None)
        return None if provenance is None else provenance.parent_task(context)

    def scientific_reference(self, context, reference, namespace):
        return self._scientific_provenance(context).resolve(context, reference, namespace, credit_metadata=self.workflow.source_controller_credit(context))

    def own_outcomes(self, episode_id, *, tools, offset, limit):
        if type(offset) is not int or offset < 0 or type(limit) is not int or (limit < 1) or (tools is not None and (not isinstance(tools, (tuple, list)) or any((not isinstance(name, str) for name in tools)))):
            raise ValueError('explicit_outcome_page_required')
        clauses = ['run_id=?', 'episode_id=?', 'result IS NOT NULL']
        arguments = [self.workflow.run_id, episode_id]
        if tools is not None:
            clauses.append("json_extract(action,'$.tool') IN (SELECT value FROM json_each(?))")
            arguments.append(json.dumps(list(tools)))
        rows = self.workflow.store.db.execute("SELECT decision_index, json_extract(action,'$.tool') AS selected_tool, json_extract(result,'$.status') AS status, json_extract(result,'$.record_refs') AS record_refs, json_extract(result,'$.changed_record_refs') AS changed_record_refs , json_extract(result,'$.progress_refs') AS progress_refs FROM runtime_actions WHERE " + ' AND '.join(clauses) + ' ORDER BY decision_index LIMIT ? OFFSET ?', (*arguments, limit + 1, offset))
        values = list(rows)
        records = [{'decision_index': row['decision_index'], 'selected_tool': row['selected_tool'], 'status': row['status'], 'record_refs': json.loads(row['record_refs'] or '[]'), 'changed_record_refs': json.loads(row['changed_record_refs'] or '[]'), 'progress_refs': json.loads(row['progress_refs'] or '[]'), 'result_ref': None} for row in values[:limit]]
        return {'records': records, 'offset': offset, 'limit': limit, 'next_offset': offset + limit if len(values) > limit else None}

    def protein_structure_input_authority(self):
        from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.protein_structure_action_records import ProteinStructureActionRecords
        return ProteinStructureActionRecords(self.workflow.store, self.workflow.run_id)

    def protein_structure_reference_access(self, context, reference, namespace):
        return self.protein_structure_input_authority().retained_reference_access(
            context, reference, namespace)


_DEFAULT_SCIENTIFIC_CREDIT = WorkflowServices.scientific_credit
_DEFAULT_SCIENTIFIC_RECEIVED_RESULTS = WorkflowServices.scientific_received_results
_DEFAULT_SCIENTIFIC_FROZEN_RESULTS = WorkflowServices.scientific_frozen_results
_DEFAULT_SCIENTIFIC_SAVED_REQUEST = WorkflowServices.scientific_saved_request
