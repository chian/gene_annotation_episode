"""Ports from a specialist binding to the existing application services.

This adapter owns no decisions, execution loop, credit formula or work policy.
It keeps bindings independent of Workflow/DecisionSource implementation types.
"""
from __future__ import annotations

import inspect
import json

from .communication import plain
from .episode_bindings import BindingContext, native_observation_options


class WorkflowServices:
    def __init__(self, workflow):
        self.workflow = workflow

    def tool_catalog(self, scope):
        catalog = self.workflow.tools.catalog(scope=plain(scope))
        return ([{'name': name, **item} for name, item in catalog.items()]
                if isinstance(catalog, dict) else list(catalog))

    def tool_information_catalog(self, scope) -> list[dict]:
        """Describe direct tools and resource operations the child can commission.

        The direct registry remains unchanged. Only explicitly bound owners
        declare resource contracts; source-library information is not a route.
        """
        from .resource_tool_information import (bound_resource_tool_contracts,
                                                tool_information_contracts)
        registry = self.workflow.episode_bindings
        scientific = self.workflow.scientific_process_binding
        child_roles = (() if scientific is None else
                       scientific.child_roles('scientific_process'))
        resources, seen = [], set()
        for role in registry.roles:
            binding = registry.for_role(role)
            if id(binding) in seen:
                continue
            seen.add(id(binding))
            for row in bound_resource_tool_contracts(binding):
                routes = [route for route in row['invocation_route']['routes']
                    if route['entry_role'] in child_roles
                    and registry.for_role(route['entry_role']) is binding
                    and registry.for_role(route['resource_role']) is binding]
                if routes:
                    resources.append({**row, 'invocation_route': {
                        'kind': 'commission', 'routes': routes}})
        return tool_information_contracts(self.tool_catalog(scope), resources)

    async def execute_tool(self, name, arguments, *, scope, operation_key,
                           permitted_record_refs=None):
        tools = self.workflow.tools
        dispatch = getattr(tools, 'execute_async', tools.execute)
        authorization = ({'permitted_record_refs': tuple(permitted_record_refs)}
                         if permitted_record_refs is not None else {})
        result = dispatch(name, plain(arguments), scope=plain(scope), operation_key=operation_key,
                          **authorization)
        return await result if inspect.isawaitable(result) else result

    def authenticate_structure_alignment_operands(self, context: BindingContext,
                                                 arguments: dict) -> dict:
        """Check original received structure sequences before alignment preparation."""
        from .protein_structure_authority import ProteinStructureOperandError
        from .protein_structure_contracts import issue
        from .protein_structure_operands import (
            authenticate_structure_sequence_reference,
            is_protein_structure_sequence_operand,
        )
        if context.run_id != self.workflow.run_id:
            raise ProteinStructureOperandError(issue(
                'original_commission_mismatch', stage='authority', field='receipt'))
        descriptors = {'query': None, 'reference': None}
        for role in descriptors:
            reference = arguments[role + '_ref']
            if not is_protein_structure_sequence_operand(self.workflow.store, reference):
                continue
            try:
                owner = self.workflow.episode_bindings.for_role('results')
            except LookupError:
                owner = None
            returns = getattr(owner, 'native_protein_structure_returns', None)
            if returns is None:
                raise ProteinStructureOperandError(issue(
                    'sequence_not_received', stage='authority', field='descriptor'))
            descriptor = authenticate_structure_sequence_reference(
                self.workflow.store, context, reference, returns=returns)
            if 'sequence_align' not in descriptor['allowed_uses']:
                raise ProteinStructureOperandError(issue(
                    'sequence_not_received', stage='authority', field='descriptor'))
            descriptors[role] = descriptor
        return descriptors

    def read_record(self, reference):
        return self.workflow.store.get(reference)

    def literature_rate_repository(self):
        """Expose the selected source-sheet adapter; own no decisions or credit."""
        from .literature_rate_storage import LiteratureRateRepository
        if not hasattr(self, '_literature_rate_repository'):
            self._literature_rate_repository = LiteratureRateRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_rate_repository

    def literature_quantity_repository(self):
        """Access committed source-native quantities without owning episode work."""
        from .literature_quantity_storage import LiteratureQuantityRepository
        if not hasattr(self, "_literature_quantity_repository"):
            self._literature_quantity_repository = LiteratureQuantityRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_quantity_repository

    def literature_assay_repository(self):
        """Access source-bound numerical assay calculations; own no decisions."""
        from .literature_assay_storage import LiteratureAssayRepository
        if not hasattr(self, '_literature_assay_repository'):
            self._literature_assay_repository = LiteratureAssayRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_assay_repository

    def literature_amount_repository(self):
        """Access selected source amount components without choosing work."""
        from .literature_amount_storage import LiteratureAmountRepository
        if not hasattr(self, '_literature_amount_repository'):
            self._literature_amount_repository = LiteratureAmountRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_amount_repository

    def literature_optical_repository(self):
        """Access selected optical q/Vq inputs without choosing scientific work."""
        from .literature_optical_storage import LiteratureOpticalRepository
        if not hasattr(self, '_literature_optical_repository'):
            self._literature_optical_repository = LiteratureOpticalRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_optical_repository

    def literature_kinetic_repository(self):
        """Access selected native kinetic parameter components, without choosing work."""
        from .literature_kinetic_storage import LiteratureKineticRepository
        if not hasattr(self, '_literature_kinetic_repository'):
            self._literature_kinetic_repository = LiteratureKineticRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_kinetic_repository

    def literature_ratio_repository(self):
        """Access retained relative-signal components without choosing work."""
        from .literature_ratio_storage import LiteratureRatioRepository
        if not hasattr(self, '_literature_ratio_repository'):
            self._literature_ratio_repository = LiteratureRatioRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_ratio_repository

    def literature_ratio_source_repository(self, *, evidence_origin="reported_source"):
        """Access selected native source-signal cells with the caller's bound origin."""
        from .literature_ratio_source_storage import LiteratureRatioSourceRepository
        if not hasattr(self, '_literature_ratio_source_repositories'):
            self._literature_ratio_source_repositories = {}
        if evidence_origin not in self._literature_ratio_source_repositories:
            repository = LiteratureRatioSourceRepository(self.workflow.store, self.workflow.run_id,
                evidence_origin=evidence_origin)
            self._literature_ratio_source_repositories[evidence_origin] = repository
        return self._literature_ratio_source_repositories[evidence_origin]

    def literature_binding_interaction_repository(self):
        """Access selected four-cell source binding interaction components."""
        from .literature_binding_interaction_storage import LiteratureBindingInteractionRepository
        if not hasattr(self, '_literature_binding_interaction_repository'):
            self._literature_binding_interaction_repository = LiteratureBindingInteractionRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_binding_interaction_repository

    def literature_controlled_response_repository(self, *, expected_descriptor=None, evidence_origin="reported_source"):
        """Access the caller-bound controlled-response repository; choose no work."""
        from .literature_controlled_response_storage import LiteratureControlledResponseRepository
        key = json.dumps([expected_descriptor, evidence_origin], sort_keys=True, allow_nan=False)
        if not hasattr(self, '_literature_controlled_response_repositories'):
            self._literature_controlled_response_repositories = {}
        if key not in self._literature_controlled_response_repositories:
            self._literature_controlled_response_repositories[key] = LiteratureControlledResponseRepository(
                self.workflow.store, self.workflow.run_id, expected_descriptor=expected_descriptor,
                evidence_origin=evidence_origin)
        return self._literature_controlled_response_repositories[key]
    def literature_gel_repository(self, *, expected_descriptor=None, evidence_origin="reported_source"):
        """Access the caller-bound gel repository; choose no work."""
        from .literature_gel_storage import LiteratureGelRepository
        key = json.dumps([expected_descriptor, evidence_origin], sort_keys=True, allow_nan=False)
        if not hasattr(self, '_literature_gel_repositories'):
            self._literature_gel_repositories = {}
        if key not in self._literature_gel_repositories:
            self._literature_gel_repositories[key] = LiteratureGelRepository(
                self.workflow.store, self.workflow.run_id, expected_descriptor=expected_descriptor,
                evidence_origin=evidence_origin)
        return self._literature_gel_repositories[key]

    def literature_binding_repository(self):
        """Access saved source binding parameters without choosing work."""
        from .literature_binding_storage import LiteratureBindingRepository
        if not hasattr(self, '_literature_binding_repository'):
            self._literature_binding_repository = LiteratureBindingRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_binding_repository

    def literature_binding_model_repository(self):
        """Read and populate explicitly selected conditional binding models."""
        from .literature_binding_model_storage import LiteratureBindingModelRepository
        if not hasattr(self, '_literature_binding_model_repository'):
            self._literature_binding_model_repository = LiteratureBindingModelRepository(self.workflow.store, self.workflow.run_id)
        return self._literature_binding_model_repository

    def literature_transport_repository(self):
        """Access explicitly selected source kinetic-response calculations."""
        from .literature_transport_storage import LiteratureTransportRepository
        if not hasattr(self, '_literature_transport_repository'):
            self._literature_transport_repository = LiteratureTransportRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_transport_repository

    def literature_perturbation_repository(self):
        """Access selected source perturbation/restoration components."""
        from .literature_perturbation_storage import LiteraturePerturbationRepository
        if not hasattr(self, '_literature_perturbation_repository'):
            self._literature_perturbation_repository = LiteraturePerturbationRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_perturbation_repository

    def literature_structure_repository(self):
        """Access selected source-model geometry and local-fit components."""
        from .literature_structure_storage import LiteratureStructureRepository
        if not hasattr(self, '_literature_structure_repository'):
            self._literature_structure_repository = LiteratureStructureRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_structure_repository

    def literature_reaction_repository(self):
        """Access selected reported-reaction constraints and resource budgets."""
        from .literature_reaction_storage import LiteratureReactionRepository
        if not hasattr(self, '_literature_reaction_repository'):
            self._literature_reaction_repository = LiteratureReactionRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_reaction_repository

    def literature_context_repository(self):
        """Access selected organism/sample compatibility components."""
        from .literature_context_storage import LiteratureContextRepository
        if not hasattr(self, '_literature_context_repository'):
            self._literature_context_repository = LiteratureContextRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_context_repository

    def literature_figure_repository(self):
        """Access selected native experimental figure measurements."""
        from .literature_figure_storage import LiteratureFigureRepository
        if not hasattr(self, '_literature_figure_repository'):
            self._literature_figure_repository = LiteratureFigureRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_figure_repository

    def literature_partner_repository(self):
        """Access selected condition-qualified experimental partner components."""
        from .literature_partner_storage import LiteraturePartnerRepository
        if not hasattr(self, '_literature_partner_repository'):
            self._literature_partner_repository = LiteraturePartnerRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_partner_repository

    def reference_in_scope(self, reference, scope, namespace):
        store = self.workflow.store
        # A qualified physical execution handle is itself a scoped source
        # record. Its operational namespace still needs the progress provider's
        # original-target checks, rather than the source record's type name.
        if namespace in {'execution_handle', 'execution'}:
            provider = getattr(self.workflow, 'progress_provider', None)
            return bool(provider is not None and provider.resolve(reference, plain(scope), namespace))
        if not store.reference_subset([reference], plain(scope)):
            provider = getattr(self.workflow, 'progress_provider', None)
            return bool(provider is not None and provider.resolve(reference, plain(scope), namespace))
        kind = store.get(reference)['record_type']
        return (not namespace or namespace == kind or namespace == 'subject'
                and kind in {'input', 'feature', 'product', 'read_subject'})

    def reference_in_context(self, context, reference, namespace):
        if context.run_id != self.workflow.run_id:
            raise ValueError('context_reference_receiver_identity_mismatch')
        received = self.workflow.episode_bindings.resolve_received_reference(context, reference, namespace)
        if received is not None:
            return received
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

    def observe_progress(self, target_handle, requested_fields, scope, *,
                         permitted_committed_record_types=(), operation_key=None,
                         native_operation=None, observation_context=None):
        provider = getattr(self.workflow, 'progress_provider', None)
        if provider is None:
            raise ValueError('episode_progress_provider_not_bound')
        return provider.observe(target_handle, requested_fields, plain(scope),
            permitted_committed_record_types=permitted_committed_record_types,
            operation_key=operation_key,
            **native_observation_options(native_operation, observation_context))

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
            raise ValueError('scientific_process_provenance_unavailable')
        return provenance

    def scientific_preparation(self, context, preparation_ref, *, owner='self'):
        return self._scientific_provenance(context).preparation(
            context, preparation_ref, owner=owner)

    def scientific_received_results(self, context):
        return self._scientific_provenance(context).received_results(context)

    def scientific_frozen_results(self, context):
        return self._scientific_provenance(context).frozen_results(context)

    def _alignment_site_records(self):
        from .alignment_site_action_records import AlignmentSiteActionRecords
        return AlignmentSiteActionRecords(self.workflow.store, self.workflow.run_id,
            sequence_reader=self.workflow.tools._sequence)

    def alignment_site_own_action_results(self, context, *, source, selection,
                                         after_decision_index, limit):
        return self._alignment_site_records().own_action_results(context,
            source=source, selection=selection,
            after_decision_index=after_decision_index, limit=limit)

    def alignment_site_frozen_facts(self, context, *, sources):
        return self._alignment_site_records().frozen_facts(context, sources=sources)

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
