"""Root-owned workflow_setup.py"""
from __future__ import annotations
from .episode_commissions import CommissionCoordinator
from .episode_completion import CompletionLedger
from .decision_context import PROTOCOL as DECISION_EXCHANGE_PROTOCOL
from .decision_exchanges import DecisionExchanges
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import DurableExecutionStore
from .workflow_values import EPISODE_BRANCH_LIFECYCLE
from .episode_application_services import EpisodeApplicationServices
from .episode_bindings import EpisodeBindingRegistry
from .episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.method_loop import EpisodeTree
from gene_annotation_episode.episodic_workflow.root.method_loop import Grain
from .episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.method_loop.archive import JsonArchive
from gene_annotation_episode.launch_instructions import LaunchInstructions
from .local_return_history import LocalReturnHistory
from pathlib import Path
from .composition_information import ROOT_BOUNDARY_VERSION
from .workflow_values import ReleasingContext
from gene_annotation_episode.tool_knowledge import ToolKnowledge
from .wait_estimation_inputs import WaitInputs
from .wait_events import WaitStore
from .episode_journal import WorkflowError
from .episode_services import WorkflowServices
from .workflow_values import _annotation_child_roles
from .workflow_values import _binding_name
from .workflow_values import _decision_protocol
from .workflow_values import _effective_restoration_configuration
from .task_values import _plain
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import canonical
from .episode_application_services import job_progress_binding
import json
from .episode_bindings import native_job_event_configuration
from .episode_application_services import service_binding

class WorkflowSetup:

    @classmethod
    def validate_expectations(cls, binding, job_episodes=None, *, episode_roles=()):
        scientific = ('annotation',) if 'scientific_process' in episode_roles else cls.grain_names
        names = (*scientific, *(() if job_episodes is None else job_episodes.roles), *episode_roles)
        if binding is not None and set(binding.episode_types) - set(names):
            raise ValueError('execution_expectations_name_unavailable_episode_type')

    def __init__(self, store, tools, provider, directory, run_id, controller_factory, project_credit, credit_binding=None, restoration_settings=None, execution_expectations=None, job_episodes=None, controller_binding=None, project_child_credit=None, child_credit_binding=None, resource_estimator=None, project_annotation_score=None, annotation_score_binding=None, initial_known_record_refs=None, native_timing_information=None, episode_binding_factories=None, episode_binding_descriptors=None, role_credit_bindings=None, job_progress_provider=None, execution_binding=None, episode_service_factory=None, episode_service_binding=None, progress_receipt_order='received_progress_order_v1', episode_record_receipts=False, wait_inputs_version='wait_inputs_binding_v2', completed_action_inputs_version='completed_action_inputs_binding_v1', native_job_events=None, episode_service_inputs=None, annotation_child_roles=None, root_role='annotation', decision_protocol=None, root_action_boundary=ROOT_BOUNDARY_VERSION, episode_branch_lifecycle=EPISODE_BRANCH_LIFECYCLE, inprocess_completion_order=None, episode_binding_owners=None):
        from .inprocess_replay import VERSION as INPROCESS_COMPLETION_ORDER
        if inprocess_completion_order not in (None, INPROCESS_COMPLETION_ORDER):
            raise ValueError('unsupported_inprocess_completion_order')
        if inprocess_completion_order is not None and execution_binding is not None:
            raise ValueError('durable_execution_already_owns_completion_order')
        self.inprocess_completion_order = inprocess_completion_order
        self.root_role = root_role
        if episode_branch_lifecycle != EPISODE_BRANCH_LIFECYCLE:
            raise ValueError('original_episode_lifecycle_requires_its_pinned_implementation')
        self.episode_branch_lifecycle = episode_branch_lifecycle
        if root_action_boundary not in (None, ROOT_BOUNDARY_VERSION):
            raise ValueError('unsupported_root_action_boundary')
        self.root_action_boundary = root_action_boundary
        self.decision_protocol = _decision_protocol(decision_protocol)
        self.annotation_child_roles = _annotation_child_roles(annotation_child_roles)
        native_job_events = native_job_event_configuration(native_job_events)
        if native_job_events is not None:
            if job_episodes is None:
                raise ValueError('native_job_events_requires_job_binding')
            statistics = getattr(job_episodes, 'statistics', None)
            if statistics is not None and statistics.resource_id != native_job_events['resource_id']:
                raise ValueError('native_event_resource_binding_mismatch')
        self.native_job_events = native_job_events
        if type(episode_record_receipts) is not bool:
            raise TypeError('episode_record_receipts_must_be_bool')
        if episode_record_receipts and (not isinstance(initial_known_record_refs, (list, tuple)) or any((not isinstance(ref, str) or not ref for ref in initial_known_record_refs))):
            raise ValueError('receipt_binding_requires_explicit_initial_known_record_refs')
        self.episode_record_receipts = episode_record_receipts
        if wait_inputs_version not in {'wait_inputs_binding_v1', 'wait_inputs_binding_v2'}:
            raise ValueError('unsupported_wait_inputs_binding')
        self.wait_inputs_version = wait_inputs_version
        if completed_action_inputs_version not in {None, 'completed_action_inputs_binding_v1'}:
            raise ValueError('unsupported_completed_action_inputs_binding')
        self.completed_action_inputs_version = completed_action_inputs_version
        self.episode_application_services_binding = service_binding(episode_service_factory, episode_service_binding, inputs=episode_service_inputs)
        if self.episode_application_services_binding is not None and any((value is not None for value in (episode_binding_factories, episode_binding_descriptors, role_credit_bindings, job_progress_provider))):
            raise ValueError('episode_service_factory_and_direct_services_are_exclusive')
        if progress_receipt_order not in {'received_progress_order_v1', 'legacy_grouped_v1'}:
            raise ValueError('unsupported_progress_receipt_order')
        self.progress_receipt_order = progress_receipt_order
        self.store, self.tools, self.provider = (store, tools, provider)
        self.directory, self.run_id = (Path(directory), run_id)
        self.knowledge = ToolKnowledge.freeze(self.directory / 'tool-knowledge', source=getattr(tools, 'knowledge_library_directory', None))
        self.launch_instructions = LaunchInstructions.freeze(self.directory / 'launch-instructions', source=getattr(tools, 'launch_instruction_library_directory', None))
        self.controller_factory, self.project_credit = (controller_factory, project_credit)
        self.project_child_credit = project_child_credit
        self.project_annotation_score = project_annotation_score
        self.annotation_score_binding = _plain(annotation_score_binding)
        self.child_credit_binding = _plain(child_credit_binding) if child_credit_binding is not None else {'kind': 'custom', 'projector': _binding_name(project_child_credit, 'caller_injected'), 'meaning': 'Available finding calculation; each scientific owner selects its task credit.'} if project_child_credit is not None else None
        self.controller_binding = _plain(controller_binding) if controller_binding is not None else {'kind': 'custom', 'factory': _binding_name(controller_factory, 'caller_injected')}
        self.job_episodes = job_episodes
        if job_episodes is not None:
            job_episodes.recover_statistics()
        self.execution_expectations = execution_expectations
        self.resource_estimator = resource_estimator
        self.native_timing_information = native_timing_information
        self.restoration_settings = _effective_restoration_configuration(base=restoration_settings)
        self.credit_binding = _plain(credit_binding) if credit_binding is not None else {'kind': 'custom', 'projector': _binding_name(project_credit, 'caller_injected'), 'meaning': 'Caller-injected projector; no default scientific policy or denominator is inferred.'}
        self.journal = Journal(store, run_id)
        self.decision_exchanges = DecisionExchanges(self.journal) if self.decision_protocol == DECISION_EXCHANGE_PROTOCOL else None
        self.execution_backend = DurableExecutionStore(self.directory / 'episode-execution')
        self.native_event_information = None
        self.native_event_recovery = None
        if native_job_events is not None:
            from .native_events import NativeEventProvider
            from .library.native_event_information import NativeEventInformation
            native_provider = NativeEventProvider(self.execution_backend.root_directory, run_id=run_id, resource_id=native_job_events['resource_id'])
            job_episodes = job_episodes.with_native_events(native_provider)
            self.job_episodes = job_episodes
            self.native_event_information = NativeEventInformation(store, self.journal, self.execution_backend, jobs=job_episodes.jobs, resource_id=native_job_events['resource_id'])
            self.native_event_recovery = job_episodes.recover_native_events()
        self.execution_binding = _plain(execution_binding)
        self.execution_handle = None
        self.commissions = CommissionCoordinator(store, self.journal, self.execution_backend)
        self.completions = CompletionLedger(store, self.journal)
        self.wait_store = WaitStore(store, run_id)
        self.local_return_history = LocalReturnHistory(store, self.journal, self.execution_backend)
        self.progress_provider = None
        self.role_credit_projectors = {}
        self.role_credit_definitions = {}
        self.resource_capabilities = ()
        self.receipts = EpisodeReceipts(store, run_id) if episode_record_receipts or native_timing_information is not None or any((getattr(projector, 'requires_episode_receipts', False) for projector in (project_credit, project_child_credit))) else None
        self.initial_known_record_refs = tuple(initial_known_record_refs) if isinstance(initial_known_record_refs, (list, tuple)) else initial_known_record_refs
        self.archive = JsonArchive(self.directory / 'archive')
        if self.inprocess_completion_order is not None:
            from .inprocess_replay import InProcessReplay
            if self.receipts is None:
                raise ValueError('inprocess_completion_replay_requires_original_receipts')
            self.inprocess_replay = InProcessReplay(self)
        else:
            self.inprocess_replay = None
        self.services = WorkflowServices(self)
        self.episode_job_progress_provider_binding = None
        terminal_configuration = None
        if episode_service_factory is not None:
            setup_inputs = {} if episode_service_inputs is None else {'tool_catalog': json.loads(canonical(self.tools.catalog()))}
            if episode_service_inputs == 'actual_tool_registry_v1':
                setup_inputs['tool_registry'] = self.tools
            if self.episode_application_services_binding['factory'] == 'gene_annotation_episode.practical_service_setup.PracticalServiceFactory':
                from .terminal_binding_catalogue import (application_from_original_factory,
                    factory_configuration, owner_records, descriptor_parents,
                    validate_saved_fixed_catalogue)
                terminal_configuration = factory_configuration(episode_service_factory, self.episode_application_services_binding)
                recorded_descriptors = None
                saved_run = self.journal.row('runtime_runs')
                if saved_run is not None:
                    saved_settings = json.loads(saved_run['settings'])
                    if 'episode_bindings' in saved_settings:
                        validate_saved_fixed_catalogue(saved_settings)
                        if canonical(saved_settings.get('episode_application_services')) != canonical(self.episode_application_services_binding):
                            raise ValueError('root_terminal_saved_factory_conflict')
                        recorded_descriptors = saved_settings['episode_bindings']
                application = application_from_original_factory(episode_service_factory,
                    directory=self.directory, descriptors=recorded_descriptors)
                parents = descriptor_parents(terminal_configuration, application.episode_binding_descriptors)
                expected_owners = tuple(row['owner'] for row in owner_records(terminal_configuration, parents=parents))
                if episode_binding_owners is not None and tuple(episode_binding_owners) != expected_owners:
                    raise ValueError('root_terminal_supplied_owner_conflict')
                episode_binding_owners = expected_owners
            else:
                from .execution_service_setup import ExecutionServiceFactory
                if type(episode_service_factory) is ExecutionServiceFactory:
                    actual_service = service_binding(episode_service_factory,
                        episode_service_factory.as_record(), inputs=episode_service_inputs)
                    if canonical(actual_service) != canonical(self.episode_application_services_binding):
                        raise ValueError('root_execution_actual_factory_definition_conflict')
                    recorded_descriptors = None
                    saved_run = self.journal.row('runtime_runs')
                    if saved_run is not None:
                        saved_settings = json.loads(saved_run['settings'])
                        if canonical(saved_settings.get('episode_application_services')) != canonical(actual_service):
                            raise ValueError('root_execution_saved_factory_definition_conflict')
                        recorded_descriptors = saved_settings['episode_bindings']
                    application = episode_service_factory(store, run_id=run_id, directory=self.directory,
                        job_episodes=job_episodes, resource_estimator=resource_estimator,
                        **setup_inputs, episode_binding_descriptors=recorded_descriptors)
                else:
                    application = episode_service_factory(store, run_id=run_id, directory=self.directory, job_episodes=job_episodes, resource_estimator=resource_estimator, **setup_inputs)
            if type(application) is not EpisodeApplicationServices:
                raise TypeError('episode_service_factory_must_return_EpisodeApplicationServices')
            episode_binding_descriptors = application.episode_binding_descriptors
            role_credit_bindings = application.role_credit_bindings
            job_progress_provider = application.job_progress_provider
            self.episode_job_progress_provider_binding = job_progress_binding(job_progress_provider)
        self._constructing_binding_requests = {}
        if episode_binding_owners is not None and episode_binding_descriptors is not None and terminal_configuration is None:
            raise ValueError('root_owned_descriptor_constructor_not_implemented')
        if episode_binding_descriptors is not None:
            if episode_binding_factories is not None:
                raise ValueError('episode_descriptors_and_factories_are_exclusive')
            from .episode_composition import compose_episode_bindings
            composition = compose_episode_bindings(self.services, store=store, journal=self.journal, execution_backend=self.execution_backend, descriptors=episode_binding_descriptors, job_episodes=job_episodes, resource_estimator=resource_estimator, role_credit_bindings=role_credit_bindings or {}, job_progress_provider=job_progress_provider, directory=self.directory, tool_registry=self.tools, terminal_configuration=terminal_configuration)
            self.progress_provider = composition.progress_provider
            self.resource_capabilities = composition.resource_capabilities
            self.role_credit_projectors = composition.role_credit_projectors
            self.role_credit_definitions = composition.role_credit_definitions
            self.episode_bindings = EpisodeBindingRegistry(composition.bindings, owners=episode_binding_owners, owner_for_path=self._binding_owner_for_path, terminal_configuration=terminal_configuration)
        else:
            if role_credit_bindings is not None or job_progress_provider is not None:
                raise ValueError('explicit_specialist_services_require_episode_descriptors')
            if episode_binding_factories is None:
                from .literature_families import factories
                episode_binding_factories = factories()
            self.episode_bindings = EpisodeBindingRegistry((factory(self.services) for factory in episode_binding_factories), owners=episode_binding_owners, owner_for_path=self._binding_owner_for_path)
        for profile in self.episode_bindings.contract_information_configurations():
            self.validate_contract_information_configuration(profile)
        self.validate_expectations(execution_expectations, job_episodes, episode_roles=self.episode_bindings.roles)
        self._legacy_scientific_process_binding = self.episode_bindings.for_role('scientific_process') if 'scientific_process' in self.episode_bindings.roles and len(self.episode_bindings.private_owners) <= 1 else None
        self.scientific_provenance = None
        self.scientific_tool_retriever = None
        if self.has_scientific_binding and len(self.episode_bindings.private_owners) <= 1:
            create_provenance = getattr(self.scientific_process_binding, 'create_scientific_provenance', None)
            if create_provenance is None:
                from .scientific_process_provenance import ScientificProcessProvenance
                self.scientific_provenance = ScientificProcessProvenance(store, self.journal, library=self.scientific_process_binding.library, tool_library=self.scientific_process_binding.tool_library)
            else:
                self.scientific_provenance = create_provenance(store=store, journal=self.journal)
            retrieval = self.scientific_process_binding.tool_retrieval
            if retrieval is not None and retrieval['mode'] == 'semantic_fast_v1':
                create_retriever = getattr(self.scientific_process_binding, 'create_tool_retriever', None)
                if create_retriever is None:
                    from .scientific_tool_retrieval import ScientificToolRetriever
                    self.scientific_tool_retriever = ScientificToolRetriever(store, run_id=run_id, provider=provider, library=self.scientific_process_binding.tool_library, configuration=retrieval)
                else:
                    self.scientific_tool_retriever = create_retriever(store=store, run_id=run_id, provider=provider)
        if self.receipts is None and any((getattr(projector, 'requires_episode_receipts', False) for projector in self.role_credit_projectors.values())):
            raise ValueError('role_credit_requires_episode_record_receipts')
        self.wait_inputs = WaitInputs(store, self.journal, self.progress_provider)
        names = self.grain_names + (() if job_episodes is None else job_episodes.roles) + self.episode_bindings.roles
        self.grains = {name: Grain(name, 'One completed selected improvement action', 'Committed semantic work and a parent-defined form', self.controller) for name in names}
        if root_role not in self.grains:
            raise ValueError('root_episode_role_not_bound')
        available_entries = self._default_scientific_child_roles()
        if self.annotation_child_roles is not None and (not set(self.annotation_child_roles) <= set(available_entries)):
            raise ValueError('annotation_child_role_not_an_entry_role')
        children = {self.grains['annotation']: tuple((self.grains[name] for name in self.declared_child_roles('annotation')))}
        for role in () if job_episodes is None else job_episodes.roles:
            children[self.grains[role]] = ()
        if not self.has_scientific_binding:
            children[self.grains['improvement']] = tuple((self.grains[name] for name in self.declared_child_roles('improvement')))
        for role in self.episode_bindings.roles:
            children[self.grains[role]] = tuple((self.grains[name] for name in self.declared_child_roles(role)))
        if self.annotation_child_roles is not None or root_role != 'annotation':
            reachable, frontier = (set(), [self.grains[root_role]])
            while frontier:
                grain = frontier.pop()
                if grain not in reachable:
                    reachable.add(grain)
                    frontier.extend(children.get(grain, ()))
            children = {grain: values for grain, values in children.items() if grain in reachable}
        adjacency = {parent.name: {child.name for child in values} for parent, values in children.items()}

        def reaches(start, target):
            frontier, seen = ([start], set())
            while frontier:
                value = frontier.pop()
                if value == target:
                    return True
                if value not in seen:
                    seen.add(value)
                    frontier.extend(adjacency.get(value, ()))
            return False
        recursive = tuple(((parent, child) for parent, values in adjacency.items() for child in values if reaches(child, parent)))
        self.tree = EpisodeTree(self.grains[root_role], children, self_nesting=tuple((name for name, values in adjacency.items() if name in values)), recursive_edges=recursive)
        self.context = ReleasingContext(tree=self.tree, run_id=run_id)
        self.configure_execution(execution_binding)

    def configure_execution(self, binding, *, execution_handle=None):
        if self.execution_binding is not None and _plain(binding) != self.execution_binding:
            raise WorkflowError('execution_binding_is_immutable')
        self.execution_binding = _plain(binding)
        self.execution_handle = execution_handle
        if binding is not None and self.progress_provider is None:
            from .progress_observations import ProgressProvider
            self.progress_provider = ProgressProvider(self.store, self.execution_backend, run_id=self.run_id)
            self.wait_inputs = WaitInputs(self.store, self.journal, self.progress_provider)
