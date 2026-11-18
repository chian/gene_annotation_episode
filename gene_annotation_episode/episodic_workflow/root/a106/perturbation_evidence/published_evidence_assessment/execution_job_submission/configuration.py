"""Private A106 launch configuration."""
from __future__ import annotations
from .execution_contracts import KINDS, Path, canonical, json, math, plain

class OperationalConfiguration:

    def __init__(self, services, *, store, directory, run_id, resources, initial_information, tool_registry, handoff_unit, acquired_record_unit, log_window_bytes, log_roles, require_private_yield=False, task_yield_profiles=None):
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
        from gene_annotation_episode.episodic_workflow.root.a106.numerical import YieldController, YieldParameters
        task_profiles = {} if task_yield_profiles is None else plain(task_yield_profiles)
        if not isinstance(task_profiles, dict) or any((not isinstance(key, str) or not key or (not isinstance(binding, dict)) or (set(binding) != {'cutoff', 'parameters'}) or (not isinstance(binding['parameters'], dict)) or (type(binding['cutoff']) not in (int, float)) or (not math.isfinite(binding['cutoff'])) or (binding['cutoff'] <= 0) for key, binding in task_profiles.items())):
            raise ValueError('explicit_execution_task_yield_profiles_invalid')
        for binding in task_profiles.values():
            YieldController('configuration', 0.0, binding['cutoff'], YieldParameters(**binding['parameters']))
        self.task_yield_profiles = task_profiles
        from gene_annotation_episode.episodic_workflow.root.a106.api_service_execution import APIServiceExecution
        api_resources = {key: value for key, value in self.resources.items() if KINDS[value['kind']] == 'api'}
        self.api_execution = None if not api_resources else APIServiceExecution(store, run_id=run_id, directory=self.directory, configuration=api_resources, tool_registry=tool_registry, handoff_unit=handoff_unit, acquired_record_unit=acquired_record_unit, received_input_reader=getattr(services, 'read_received_molecular_input', None), application_return_owner=self, support_receipts=self._appservice_received_support_refs, support_report_validator=self._appservice_validate_received_report)
        from gene_annotation_episode.episodic_workflow.root.a106.execution_progress import ExecutionProgressProvider
        self.job_progress_provider = ExecutionProgressProvider(store, run_id=run_id, directory=self.directory, resources=self.resources, api_execution=self.api_execution, log_window_bytes=log_window_bytes, log_roles=self.log_roles)
        from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.flux_balance_execution_inputs import FluxBalanceExecutionInputs

        self.flux_balance_inputs = FluxBalanceExecutionInputs(self)

        from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_protein_structure_results import NativeProteinStructureResults

        from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_protein_structure_returns import NativeProteinStructureReturns

        self.native_protein_structure_results = NativeProteinStructureResults(self)

        self.native_protein_structure_returns = NativeProteinStructureReturns(self)

        from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_fluorescence_results import NativeFluorescenceResults

        from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.fluorescence_returns import FluorescenceReturns

        self.native_fluorescence_results = NativeFluorescenceResults(self)

        self.native_fluorescence_returns = FluorescenceReturns(self)

        self.native_flux_balance_results = self.native_flux_balance_returns = None

        ordinary_fba = getattr(tool_registry, 'ordinary_flux_balance_backend', None)

        if (ordinary_fba is not None
                or any(configuration.get('native_flux_balance') for configuration in self.resources.values())):
            from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_flux_balance_results import NativeFluxBalanceResults
            from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.flux_balance_returns import FluxBalanceReturns
            self.native_flux_balance_results = NativeFluxBalanceResults(self)
            self.native_flux_balance_returns = FluxBalanceReturns(self, ordinary_backend=ordinary_fba)

        self.native_expression_nmf_results = self.native_expression_nmf_returns = None

        if any(configuration.get('native_expression_nmf') for configuration in self.resources.values()):
            from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_expression_nmf_results import NativeExpressionNMFResults
            from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.expression_nmf_returns import ExpressionNMFReturns
            self.native_expression_nmf_results = NativeExpressionNMFResults(self)
            self.native_expression_nmf_returns = ExpressionNMFReturns(self)

        self.atac_results = self.atac_returns = None

        if any(configuration.get('native_atac_differential') for configuration in self.resources.values()):
            from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_atac_differential_results import NativeAtacDifferentialResults
            from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.atac_differential_returns import AtacDifferentialReturns
            self.atac_results = NativeAtacDifferentialResults(self)
            self.atac_returns = AtacDifferentialReturns(self)

        self.native_chromatin_interaction_results = self.native_chromatin_interaction_returns = None

        if any(configuration.get('native_chromatin_interactions') for configuration in self.resources.values()):
            from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_chromatin_interaction_results import NativeChromatinInteractionResults
            from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.chromatin_interaction_returns import ChromatinInteractionReturns
            self.native_chromatin_interaction_results = NativeChromatinInteractionResults(self)
            self.native_chromatin_interaction_returns = ChromatinInteractionReturns(self)

