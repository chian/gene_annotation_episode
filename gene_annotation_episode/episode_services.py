"""Ports from a specialist binding to the existing application services.

This adapter owns no decisions, execution loop, credit formula or work policy.
It keeps bindings independent of Workflow/DecisionSource implementation types.
"""
from __future__ import annotations

import inspect
import json

from method_loop.identities import EpisodeRef

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

    def read_received_molecular_input(self, context, reference, namespace, *,
                                      tag_key=None, file_format=None, source_metadata_only=False,
                                      subject_metadata_only=False):
        """Read one selected admitted representation through the shared owner."""
        if (type(source_metadata_only) is not bool
                or type(subject_metadata_only) is not bool
                or sum((tag_key is not None, file_format is not None,
                        source_metadata_only, subject_metadata_only)) != 1
                or source_metadata_only and namespace != 'source'):
            raise ValueError('molecular_sequence_input_invalid_selection')
        binding = self._molecular_input_binding()
        if source_metadata_only:
            return binding.read_received_source(context, reference)
        if subject_metadata_only:
            return binding.read_received_subject(context, reference, namespace)
        if file_format is not None:
            return binding.read_received_file(context, reference, namespace, file_format=file_format)
        return binding.read_received(context, reference, namespace, tag_key=tag_key)

    def _molecular_input_binding(self):
        from types import SimpleNamespace
        from .molecular_sequence_input_bindings import MolecularSequenceInputBindings
        def resolve(current, selected, selected_namespace):
            verdict = self._molecular_reference_access(current, selected, selected_namespace)
            return (verdict if verdict is not None else
                self.workflow.episode_bindings.resolve_received_reference(current, selected, selected_namespace))
        owner = SimpleNamespace(store=self.workflow.store, run_id=self.workflow.run_id,
            resolve_received_reference=resolve,
            commission_assignment_matches=self.molecular_commission_assignment_matches)
        return MolecularSequenceInputBindings(owner)

    def read_received_molecular_file_metadata(self, context, reference, namespace, *, file_format):
        """Authenticate current File receipt metadata without opening bytes."""
        return self._molecular_input_binding().read_received_file_metadata(
            context, reference, namespace, file_format=file_format)

    def molecular_commission_assignment_matches(self, parent, child, selected_action, *, decision_index):
        """Authenticate original selectors against their frozen host ToolInfos.

        Input inspection does not reconstruct today's invocation binding. Only
        the exact recorded commission and its immutable library can explain a
        selector→canonical-body difference in the saved child assignment.
        """
        from copy import deepcopy
        from .episode_return_records import EpisodeReturnRecords
        from .scientific_process_records import (SELECTION_VERSION, scientific_digest,
            validate_filled_process, validate_selection)
        try:
            if (type(decision_index) is not int or decision_index < 0
                    or parent.run_id != self.workflow.run_id or child.run_id != parent.run_id
                    or child.role != 'scientific_process'
                    or child.path != (*parent.path, ('scientific_process', f'child_{decision_index}'))
                    or selected_action.get('kind') != 'episode_child'
                    or selected_action.get('role') != child.role):
                return False
            records = EpisodeReturnRecords(self.workflow.store, self.workflow.run_id,
                failure_prefix='molecular_commission_')
            records.authenticate(parent); records.authenticate(child)
            row = self.workflow.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? '
                'AND episode_id=? AND decision_index=?', (parent.run_id, parent.episode_id, decision_index)).fetchone()
            if row is None or not records._equal(json.loads(row['action']), selected_action):
                return False
            request = plain(child.request)
            if (not records._equal(selected_action.get('scope'), child.scope)
                    or selected_action.get('goal') != request['goal']['objective']):
                return False
            binding = self.workflow.scientific_process_binding
            if binding is None:
                return False
            filled = validate_filled_process(request['message']['scientific_process'])
            mechanics = filled['mechanics_binding']
            configuration = mechanics['configuration']
            if (mechanics.get('binding_id') != child.role
                    or not records._equal(configuration['library'], binding._library_record)
                    or not records._equal(configuration['tool_library'], binding._tools_record)):
                return False
            expected = deepcopy(selected_action['assignment'])
            if expected['selection'].get('version') != SELECTION_VERSION:
                return False
            expected['selection']['child_tool_info'] = binding.tool_library.resolve_tool_info(
                expected['selection']['child_tool_info'], available_catalog=None)
            expected['selection'] = validate_selection(expected['selection'])
            for name in ('evidence_axis', 'thought_pattern'):
                binding.library.resolve(expected['selection'][name])
            initial = json.loads(selected_action['initial_report_json'])
            contract = request['report_contract']
            invocation = dict(objective=selected_action['goal'], scope=plain(child.scope),
                purpose=selected_action['purpose'], report_schema=contract['measurements']['schema'], initial_report=initial)
            return (records._equal(expected, child.assignment)
                and records._equal(filled['selection'], expected['selection'])
                and records._equal(initial, request['message']['initial_report'])
                and selected_action['purpose'] == contract['decision']
                and filled['assignment_sha256'] == scientific_digest(expected)
                and filled['invocation_sha256'] == scientific_digest(invocation))
        except (ValueError, TypeError, KeyError, AttributeError, OSError):
            return False

    def _molecular_reference_access(self, context, reference, namespace):
        owner = getattr(getattr(self.workflow, 'tools', None), 'retained_molecular_reference_access', None)
        return owner(context, reference, namespace,
            initial_record_refs=getattr(self.workflow, 'initial_known_record_refs', None) or ()) if callable(owner) else None

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
        returns = self.protein_structure_input_authority()
        descriptors = {'query': None, 'reference': None}
        for role in descriptors:
            reference = arguments[role + '_ref']
            if not is_protein_structure_sequence_operand(self.workflow.store, reference):
                continue
            descriptor = authenticate_structure_sequence_reference(
                self.workflow.store, context, reference, returns=returns)
            if 'sequence_align' not in descriptor['allowed_uses']:
                raise ProteinStructureOperandError(issue(
                    'sequence_not_received', stage='authority', field='descriptor'))
            descriptors[role] = descriptor
        return descriptors

    def authenticate_source_byte_operands(self, context: BindingContext,
                                         tool_name: str, arguments: dict) -> None:
        """Preserve utility artifact grants at the selected source/material read."""
        from .domain import ContractError
        from .materials import source_window_selection
        from .native_blast_utility_contracts import BUNDLE_VERSION
        from .source_locations import received_source

        if context.run_id != self.workflow.run_id:
            raise ContractError('source_byte_context_run_mismatch')
        store = self.workflow.store
        if tool_name in {'material.parse', 'material.read'}:
            material = store._require(arguments['material_ref'], {'material'})
            source = store._require(material['source_ref'], {'source'})
        else:
            source = store._require(arguments['source_ref'], {'source'})
        if tool_name == 'source.read':
            artifact_ref, _, _ = source_window_selection(
                source, arguments.get('representation', 'text'))
        elif tool_name == 'source.locate':
            artifact_ref = received_source(store, source['id'], arguments['representation'],
                permitted_inputs=context.received_record_refs, scope=plain(context.scope))['id']
        else:
            artifact_ref = source['artifact_ref']
        if self._molecular_reference_access(context, artifact_ref, 'artifact') is False:
            raise ContractError('molecular_source_artifact_not_granted')
        try:
            owner = self.workflow.episode_bindings.for_role('results')
        except LookupError:
            owner = None
        results = getattr(owner, 'native_blast_utility_results', None)
        if results is not None:
            # The actual bytes can still belong to a utility result when an
            # ordinary source wrapper points at the same retained artifact.
            allowed = results.retained_reference_access(context, artifact_ref, 'artifact')
            if allowed is False:
                raise ContractError('native_blast_utility_source_artifact_not_granted')
        elif (source.get('provider') == 'episode.execution_result'
                and source.get('version') == BUNDLE_VERSION):
            raise ContractError('native_blast_utility_source_artifact_not_granted')

    def read_record(self, reference):
        return self.workflow.store.get(reference)

    def supplied_context_preview(self, context, *, limit=12000):
        """Present received caller input before a parent defines a child question.

        This is original task input, not acquired evidence or a generated
        interpretation. A partial preview retains a source handle for reading.
        """
        store = self.workflow.store
        reference = store.problem().get("caller_context_source_ref")
        if (reference is None or reference not in context.received_record_refs
                or not self.reference_in_scope(reference, context.scope, "source")):
            return []
        source = store.get(reference)
        body = store.get_artifact(source["artifact_ref"])
        preview = body[:limit].decode("utf-8", errors="ignore")
        return [{"source_ref": reference, "origin": "caller",
            "representation": "original", "content_preview": preview,
            "utf8_bytes": len(body), "complete": len(preview.encode("utf-8")) == len(body)}]

    def literature_rate_repository(self):
        """Expose the selected source-sheet adapter; own no decisions or credit."""
        from .literature_rate_storage import LiteratureRateRepository
        if not hasattr(self, '_literature_rate_repository'):
            self._literature_rate_repository = LiteratureRateRepository(
                self.workflow.store, self.workflow.run_id)
        else:
            # A rejected action can roll back DDL while this service cache
            # survives. Restore the original adapter, retaining its identity.
            self._literature_rate_repository._ensure_storage()
        return self._literature_rate_repository

    def literature_rate_observation_repository(self):
        """Access selected original XLSX entries and saved requested subsets."""
        from .literature_rate_observation_storage import LiteratureRateObservationRepository
        if not hasattr(self, '_literature_rate_observation_repository'):
            self._literature_rate_observation_repository = LiteratureRateObservationRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_rate_observation_repository

    def literature_calibration_recovery_repository(self):
        """Access selected recovery controls and exact saved numerical subsets."""
        from .literature_calibration_recovery_storage import LiteratureCalibrationRecoveryRepository
        if not hasattr(self, '_literature_calibration_recovery_repository'):
            self._literature_calibration_recovery_repository = LiteratureCalibrationRecoveryRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_calibration_recovery_repository

    def literature_rate_replicate_repository(self):
        """Access explicitly selected raw-rate tables and saved typed subsets."""
        from .literature_rate_replicate_storage import LiteratureRateReplicateRepository
        if not hasattr(self, '_literature_rate_replicate_repository'):
            self._literature_rate_replicate_repository = LiteratureRateReplicateRepository(
                self.workflow.store, self.workflow.run_id)
        return self._literature_rate_replicate_repository

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
        from .enrichr_reference_privacy import enrichr_reference_restriction
        restriction = enrichr_reference_restriction(store, None, reference, namespace, private_only=True)
        if restriction is not None:
            return restriction
        from .molecular_reference_privacy import molecular_reference_restriction
        restriction = molecular_reference_restriction(store, None, reference, namespace, private_only=True)
        if restriction is not None:
            return restriction
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
        molecular = self._molecular_reference_access(context, reference, namespace)
        if molecular is not None:
            return molecular
        protein = self.protein_structure_reference_access(context, reference, namespace)
        if protein is not None:
            return protein
        received = self.workflow.episode_bindings.resolve_received_reference(context, reference, namespace)
        if received is not None:
            return received
        native = getattr(self.workflow, 'native_event_information', None)
        if native is not None and native.resolve(context, reference, namespace):
            return True
        if namespace == 'native_event_target':
            return False
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
        workflow = self.workflow
        local = len(context.path) > 1
        projector = workflow.scientific_projector_for_context(context)
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
            annotation = self.proposed_annotation_for(context)
            if annotation is not None:
                arguments['assignment']['proposed_annotation_ref'] = annotation
            elif self.annotation_task_required():
                raise ValueError('scientific_task_requires_original_proposed_annotation')
        arguments.update(workflow.projector_receipt_arguments(projector, context.episode_id))
        result = workflow.projection_view(projector, plain(context.scope), **arguments)
        if local and arguments['assignment'].get('proposed_annotation_ref') is not None:
            result['proposed_annotation_ref'] = arguments['assignment']['proposed_annotation_ref']
        return result

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

    def itc_parameter_own_facts(self, context):
        if context.run_id != self.workflow.run_id:
            raise ValueError('itc_parameter_receiver_identity_mismatch')
        return self.molecular_own_facts(context, fact_source='itc_binding_parameters')

    def itc_parameter_frozen_facts(self, context):
        return self.molecular_frozen_facts(context, fact_source='itc_binding_parameters')

    def itc_parameter_received_facts(self, context):
        return self.molecular_received_facts(context, fact_source='itc_binding_parameters')

    def molecular_own_facts(self, context, *, fact_source):
        from .molecular_result_facts import own_molecular_facts
        if context.run_id != self.workflow.run_id:
            raise ValueError('molecular_facts_receiver_identity_mismatch')
        return own_molecular_facts(self.workflow.tools, context,
            read_received=self.read_received_molecular_input, fact_source=fact_source)

    def molecular_frozen_facts(self, context, *, fact_source):
        from .molecular_result_facts import frozen_molecular_facts
        return frozen_molecular_facts(self.workflow.store, self.workflow.run_id, context,
            fact_source=fact_source)

    def molecular_received_facts(self, context, *, fact_source):
        from .molecular_result_facts import received_molecular_facts
        return received_molecular_facts(self.workflow.store, self.workflow.run_id, context,
            fact_source=fact_source)

    def protein_structure_input_authority(self):
        from .protein_structure_action_records import ProteinStructureActionRecords
        registry = getattr(self.workflow, 'episode_bindings', None)
        for_role = getattr(registry, 'for_role', None)
        try:
            owner = for_role('results') if callable(for_role) else None
        except LookupError:
            owner = None
        return ProteinStructureActionRecords(self.workflow.store, self.workflow.run_id,
            legacy_returns=getattr(owner, 'native_protein_structure_returns', None))

    def read_received_hpc_result(self, context, reference):
        from .hpc_result_receipts import read_received_result
        try:
            binding = self.workflow.episode_bindings.for_role('hpc')
        except LookupError as error:
            raise ValueError('configured_hpc_result_authority_required') from error
        return read_received_result(binding, context, reference)

    def protein_structure_reference_access(self, context, reference, namespace):
        return self.protein_structure_input_authority().retained_reference_access(
            context, reference, namespace)

    def protein_structure_action_own_facts(self, context, *, fact_source):
        return self.protein_structure_input_authority().own_facts(context, fact_source=fact_source)

    def protein_structure_action_frozen_facts(self, context, *, fact_source):
        from .protein_structure_action_records import frozen_protein_structure_action_facts
        return frozen_protein_structure_action_facts(self.workflow.store, self.workflow.run_id,
            context, fact_source=fact_source)

    def protein_structure_action_received_facts(self, context, *, fact_source):
        return self.protein_structure_input_authority().received_facts(context, fact_source=fact_source)

    def scientific_saved_request(self, context: BindingContext, *, active_only=True) -> dict | None:
        """Read an existing request; yielded requests can finish their first form."""
        if type(active_only) is not bool:
            raise ValueError('scientific_saved_request_active_flag_invalid')
        workflow = self.workflow
        journal = workflow.journal
        if (context.run_id != workflow.run_id or journal.run_id != workflow.run_id
                or context.role != 'scientific_process'
                or EpisodeRef(context.run_id, context.path).episode_id != context.episode_id):
            raise ValueError('scientific_saved_request_identity_mismatch')
        row = journal.row('runtime_episodes', context.episode_id)
        if row is None:
            return None
        if (row['run_id'] != context.run_id or row['episode_id'] != context.episode_id
                or json.loads(row['path']) != plain(context.path)):
            raise ValueError('scientific_saved_request_identity_mismatch')
        if row['state'] == 'active':
            if row['completion'] is not None or row['archive'] is not None:
                return None
        elif not active_only and row['state'] == 'yielded':
            if row['completion'] is None or row['archive'] is None:
                return None
            completion, archive = (json.loads(value) for value in (row['completion'], row['archive']))
            if (not isinstance(completion, dict) or not completion
                    or not isinstance(archive, dict) or not archive):
                raise ValueError('scientific_saved_request_invalid')
        else:
            return None
        request = json.loads(row['request'])
        if not isinstance(request, dict):
            raise ValueError('scientific_saved_request_invalid')
        return request

    def scientific_closed_request(self, context: BindingContext) -> dict | None:
        """Read one completed invocation, without creating work or loading its tree."""
        workflow = self.workflow
        journal = workflow.journal
        if (context.run_id != workflow.run_id or journal.run_id != workflow.run_id
                or context.role != 'scientific_process'
                or EpisodeRef(context.run_id, context.path).episode_id != context.episode_id):
            raise ValueError('scientific_closed_request_identity_mismatch')
        row = journal.row('runtime_episodes', context.episode_id)
        if row is None:
            return None
        if (row['run_id'] != context.run_id or row['episode_id'] != context.episode_id
                or json.loads(row['path']) != plain(context.path)):
            raise ValueError('scientific_closed_request_identity_mismatch')
        if row['state'] != 'yielded' or row['completion'] is None or row['archive'] is None:
            return None
        closing = journal.row('runtime_forms', context.episode_id)
        if closing is None or closing['form'] is None:
            return None
        if closing['run_id'] != context.run_id or closing['episode_id'] != context.episode_id:
            raise ValueError('scientific_closed_request_identity_mismatch')
        completion, archive, form, request = (json.loads(value) for value in
            (row['completion'], row['archive'], closing['form'], row['request']))
        if (not isinstance(completion, dict) or not completion
                or not isinstance(archive, dict) or not archive
                or not isinstance(form, dict) or not isinstance(request, dict)):
            raise ValueError('scientific_closed_request_invalid')
        return request

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

    def _restriction_mapping_records(self):
        from .restriction_mapping_action_records import RestrictionMappingActionRecords
        return RestrictionMappingActionRecords(self.workflow.store, self.workflow.run_id)

    def restriction_mapping_own_action_results(self, context, *, selection,
                                               after_decision_index, limit):
        return self._restriction_mapping_records().own_action_results(context,
            selection=selection, after_decision_index=after_decision_index, limit=limit)

    def restriction_mapping_frozen_facts(self, context, *, sources):
        return self._restriction_mapping_records().frozen_facts(context, sources=sources)

    def restriction_mapping_reference(self, context, reference, namespace):
        from .restriction_mapping_references import RestrictionMappingReferences
        return RestrictionMappingReferences(self.workflow.store, self.workflow.run_id).resolve(
            context, reference, namespace)

    def scientific_parent_invocation(self, context):
        return self._scientific_provenance(context).parent_invocation(context)

    def scientific_parent_task(self, context):
        """Optionally read original scientific guidance without changing work."""
        if context.run_id != self.workflow.run_id:
            raise ValueError('scientific_provenance_receiver_identity_mismatch')
        provenance = getattr(self.workflow, 'scientific_provenance', None)
        return None if provenance is None else provenance.parent_task(context)

    def macs2_peak_monitor_task(self, context, *, assignment=None):
        """Read selected MACS2 guidance only after current target admission.

        Commission preparation passes the selecting parent's actual context;
        a monitor decision uses its own saved context. Neither case constructs
        a Results context, observes the job or receives any new reference.
        """
        from .native_macs2_peak_execution import OPERATION, MODE, validate_macs2_peak_native_job
        workflow = self.workflow
        if context.run_id != workflow.run_id:
            raise ValueError('macs2_peak_monitor_receiver_identity_mismatch')
        if context.role == 'scientific_process' and assignment is not None:
            workflow.scientific_process_binding.validate_context(context)
            selection = plain(context.assignment).get('selection', {})
            parent = dict(scientific_question=context.request['goal']['objective'],
                selected_tool_info=selection.get('child_tool_info', []))
        else:
            parent = self.scientific_parent_task(context)
        if parent is None or not any(row.get('name') == OPERATION and row.get('resources') == 'local'
                for row in parent.get('selected_tool_info', ())):
            return None
        from .episode_monitoring import _ASSIGNMENT
        from .domain import validate_schema
        selected = plain(context.assignment if assignment is None else assignment)
        validate_schema(selected, _ASSIGNMENT)
        reference = selected['target_handle']
        receipts = workflow.receipts
        if receipts is None or reference not in receipts.known(context.episode_id):
            raise ValueError('macs2_peak_monitor_target_not_received')
        if not self.reference_in_scope(reference, context.scope, 'execution_handle'):
            raise ValueError('macs2_peak_monitor_target_outside_scope')
        try:
            owner = workflow.episode_bindings.for_role('results')
        except LookupError:
            return None
        if owner.store is not workflow.store or owner.run_id != workflow.run_id or owner.services is not self:
            raise ValueError('macs2_peak_monitor_owner_identity_mismatch')
        target = owner.job_progress_provider.targets.read_target(reference, plain(context.scope))
        requested = target.get('assignment', {})
        job = requested.get('requested_job', {}).get('native_macs2_peak')
        if target.get('resource_kind') != 'local' or job is None:
            return None
        job = validate_macs2_peak_native_job(job)
        if job['request']['operation'] != OPERATION or job['request']['mode'] != MODE:
            return None
        from .macs2_peak_presentation import macs2_peak_scientific_job_view
        resource_id = target['resource_id']
        return dict(version='selected_execution_task_v1',
            scientific_question=parent['scientific_question'], selected_tool_info=plain(parent['selected_tool_info']),
            requests=[dict(resource_id=resource_id, resource_kind='local', endpoint=requested.get('endpoint'),
                constraints=plain(requested.get('constraints', {})),
                resource=owner._resource_information(resource_id), job=macs2_peak_scientific_job_view(job))],
            constraints=plain(requested.get('constraints', {})), selector=selected, result_description=None)

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
