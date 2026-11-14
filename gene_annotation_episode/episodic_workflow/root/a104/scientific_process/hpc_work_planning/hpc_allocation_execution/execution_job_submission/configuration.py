"""Private A104 Launch configuration."""
from __future__ import annotations
from .contracts import KINDS, LocalFileSourceResults, Path, TerminalExecutionBehavior, canonical, install_preparation_result_readers, install_primary_result_readers, json, math, plain, validate_preparation_resource_binding, validate_primary_resource_bindings

class LaunchConfiguration:

    def __init__(self, services, *, store, directory, run_id, resources, initial_information, tool_registry, handoff_unit, acquired_record_unit, log_window_bytes, log_roles, require_private_yield=False, results_yield_profiles=None, task_yield_profiles=None):
        self.services, self.store, self.directory = (services, store, Path(directory))
        self.run_id, self.tool_registry = (run_id, tool_registry)
        self.resources = json.loads(canonical(resources))
        self.initial_information = json.loads(canonical(initial_information))
        if not isinstance(self.resources, dict) or not self.resources or any((not isinstance(key, str) or not key or (not isinstance(value, dict)) or (value.get('kind') not in KINDS) for key, value in self.resources.items())):
            raise ValueError('explicit_execution_resources_required')
        if not isinstance(self.initial_information, dict) or not set(self.initial_information) <= set(self.resources):
            raise ValueError('initial_inventory_resource_not_bound')
        for unit in (handoff_unit, acquired_record_unit):
            if type(unit) not in (int, float) or not math.isfinite(unit) or unit <= 0:
                raise ValueError('explicit_positive_operational_credit_units_required')
        if type(log_window_bytes) is not int or log_window_bytes < 1 or (not isinstance(log_roles, (tuple, list))) or any((not isinstance(role, str) or not role for role in log_roles)):
            raise ValueError('explicit_execution_log_selection_required')
        self.handoff_unit, self.acquired_record_unit = (handoff_unit, acquired_record_unit)
        self.log_window_bytes, self.log_roles = (log_window_bytes, tuple(log_roles))
        if type(require_private_yield) is not bool:
            raise TypeError('execution_private_yield_binding_requires_boolean')
        self.private_yield_binding = require_private_yield
        profiles = {} if results_yield_profiles is None else plain(results_yield_profiles)
        if not isinstance(profiles, dict) or set(profiles) - {'native_unbounded_local', 'native_unbounded_hpc'}:
            raise ValueError('explicit_results_yield_profiles_invalid')
        from gene_annotation_episode.episodic_workflow.root.a104.numerical import YieldController, YieldParameters
        for key, binding in profiles.items():
            if not isinstance(binding, dict) or set(binding) != {'cutoff', 'parameters'} or (not isinstance(binding['parameters'], dict)) or (type(binding['cutoff']) not in (int, float)) or (not math.isfinite(binding['cutoff'])) or (binding['cutoff'] <= 0):
                raise ValueError('explicit_results_yield_profile_invalid:' + key)
            YieldController('configuration', 0.0, binding['cutoff'], YieldParameters(**binding['parameters']))
        self.results_yield_profiles = profiles
        task_profiles = {} if task_yield_profiles is None else plain(task_yield_profiles)
        if not isinstance(task_profiles, dict) or any((not isinstance(key, str) or not key or (not isinstance(binding, dict)) or (set(binding) != {'cutoff', 'parameters'}) or (not isinstance(binding['parameters'], dict)) or (type(binding['cutoff']) not in (int, float)) or (not math.isfinite(binding['cutoff'])) or (binding['cutoff'] <= 0) for key, binding in task_profiles.items())):
            raise ValueError('explicit_execution_task_yield_profiles_invalid')
        for binding in task_profiles.values():
            YieldController('configuration', 0.0, binding['cutoff'], YieldParameters(**binding['parameters']))
        self.task_yield_profiles = task_profiles
        self._practical = {}
        allowed_native = {'native_blast', 'native_blast_masking', 'native_blast_utility', 'native_blast_database', 'native_blast_standard_database', 'native_hmmer', 'native_hmmer_preparation'}
        for resource_id, configuration in self.resources.items():
            kind = KINDS[configuration['kind']]
            foreign = {name for name in configuration if name.startswith('native_') and name not in allowed_native}
            if foreign:
                raise ValueError('a104_execution_resource_binding_conflict')
            validate_primary_resource_bindings(configuration, kind)
            validate_preparation_resource_binding(configuration, kind)
            if kind != 'api':
                inventory = self.initial_information.get(resource_id)
                self._practical[resource_id] = TerminalExecutionBehavior(services, directory=self.directory, resources={kind: configuration}, store=store, initial_information={} if inventory is None else {kind: inventory})
        from gene_annotation_episode.episodic_workflow.root.a104.library.api_record_access import APIRecordAccess as APIServiceExecution
        api_resources = {key: value for key, value in self.resources.items() if KINDS[value['kind']] == 'api'}
        self.api_execution = None if not api_resources else APIServiceExecution(store, run_id=run_id, directory=self.directory, configuration=api_resources, tool_registry=tool_registry, handoff_unit=handoff_unit, acquired_record_unit=acquired_record_unit, received_input_reader=getattr(services, 'read_received_molecular_input', None))
        if self.api_execution is not None:
            from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_phylogeny_returns import BVBRCPhylogenyReturns
            self.api_execution.phylogeny_returns = BVBRCPhylogenyReturns(self.api_execution)
        from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.hpc_work_planning.hpc_allocation_execution.execution_progress_assessment.api_observer import APIObserver
        from gene_annotation_episode.episodic_workflow.root.a104.execution_progress import ExecutionProgressProvider
        self.job_progress_provider = ExecutionProgressProvider(store, run_id=run_id, directory=self.directory, resources=self.resources, api_execution=self.api_execution, log_window_bytes=log_window_bytes, log_roles=self.log_roles, api_observer=None if self.api_execution is None else APIObserver(self.api_execution), native_result_owner='scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition')
        self.local_file_sources = LocalFileSourceResults(self)
        install_primary_result_readers(self)
        install_preparation_result_readers(self)
        self._install_protected_reference_readers()
