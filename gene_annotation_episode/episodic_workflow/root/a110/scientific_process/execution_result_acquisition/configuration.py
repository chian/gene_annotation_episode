"""Private A110 Results configuration"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import resolve_received_execution_reference
from .binding_roles import KINDS
from gene_annotation_episode.episodic_workflow.root.a110.local_file_capture_results import LocalFileSourceResults
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.scientific_process.execution_result_acquisition.terminal_execution import TerminalExecutionBehavior
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical
import json
import math
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain

class ResultsConfiguration:

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
        from gene_annotation_episode.episodic_workflow.root.a110.numerical import YieldController, YieldParameters
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
        for resource_id, configuration in self.resources.items():
            kind = KINDS[configuration['kind']]
            if 'native_flux_balance' in configuration:
                from gene_annotation_episode.episodic_workflow.root.a110.native_flux_balance_bindings import validate_flux_balance_bindings
                if kind != 'local':
                    raise ValueError('native_flux_balance_resource_execution_binding_unfinished:' + kind)
                validate_flux_balance_bindings(configuration['native_flux_balance'])
            inventory = self.initial_information.get(resource_id)
            self._practical[resource_id] = TerminalExecutionBehavior(services, directory=self.directory, resources={kind: configuration}, store=store, initial_information={} if inventory is None else {kind: inventory})
        from gene_annotation_episode.episodic_workflow.root.a110.execution_progress import ExecutionProgressProvider
        self.job_progress_provider = ExecutionProgressProvider(store, run_id=run_id, directory=self.directory, resources=self.resources, log_window_bytes=log_window_bytes, log_roles=self.log_roles)
        self.local_file_sources = LocalFileSourceResults(self)
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_execution_inputs import FluxBalanceExecutionInputs
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import FluxBalanceRequestBindings
        self.flux_balance_inputs = FluxBalanceExecutionInputs(self, reference_access=resolve_received_execution_reference.__get__(self))
        self.flux_balance_requests = FluxBalanceRequestBindings(self)
        for practical in self._practical.values():
            practical.flux_balance_input_reader = self.flux_balance_inputs.for_start
        ordinary_fba = getattr(tool_registry, 'ordinary_flux_balance_backend', None)
        self.native_flux_balance_results = self.native_flux_balance_returns = None
        if ordinary_fba is not None or any((configuration.get('native_flux_balance') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a110.native_flux_balance_results import NativeFluxBalanceResults
            from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_returns import FluxBalanceReturns
            self.native_flux_balance_results = NativeFluxBalanceResults(self)
            self.native_flux_balance_returns = FluxBalanceReturns(self, ordinary_backend=ordinary_fba)
