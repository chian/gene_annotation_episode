"""Private A104 source operations."""
from __future__ import annotations
from .contracts import ContractError, Mapping, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _population_catalog, deepcopy, identity, inspect, plain, source_location_inputs, validate_schema

from .source_catalog import LiteratureSourceCatalog

from .source_admission import LiteratureSourceAdmission

from .source_text_inputs import LiteratureSourceTextInputs

class LiteratureSourceOperations(LiteratureSourceTextInputs, LiteratureSourceAdmission, LiteratureSourceCatalog):

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            arguments = self._tool_arguments(context, tool_name, arguments)
        except ContractError as error:
            return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), **({'detail': error.detail} if error.detail else {})}}
        if tool_name in {'literature.concentration_window.populate', 'literature.measurement_comparison.populate', 'literature.product_coupling.populate', 'literature.measurement_validation.populate', 'literature.ion_discrimination.populate', 'literature.channel.populate', 'literature.assay.components.populate', 'literature.calibration.recovery.populate', 'literature.rate.observations.populate', 'literature.rate.replicates.populate', 'literature.rate.populate', 'literature.rate.source.populate', 'literature.quantity.populate', 'literature.assay.populate', 'literature.ratio.populate', 'literature.ratio.source.populate', 'literature.binding.populate', 'literature.binding.model.populate', 'literature.transport.response.populate', 'literature.figure.populate', 'literature.amount.populate', 'literature.completion_time.populate', 'literature.active_site.populate', 'literature.product_partition.populate', 'literature.optical.populate', 'literature.kinetic.populate', 'literature.kinetic.model.populate', 'literature.binding.interaction.populate', 'literature.binding.interaction.model.populate', 'literature.controlled_response.source_v3.populate', 'literature.gel.populate', 'literature.parent_depletion.populate', 'literature.stoichiometric_balance.populate', 'literature.assay_grading.populate', 'literature.a105.aggregate'}:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_contract_error import ExperimentalContractError
            try:
                if tool_name == 'literature.figure.populate' and arguments.get('version') == 'literature_figure_endpoint_signal_population_v1':
                    repo = self._endpoint_signal_repository()
                    return repo.populate(context, self._materialize_text_arguments(context, arguments, repo), operation_key)
                if tool_name == 'literature.kinetic.populate' and arguments.get('version') == 'literature_kinetic_summary_precision_population_v1':
                    repo = self._summary_precision_repository()
                    return repo.populate(context, self._materialize_text_arguments(context, arguments, repo), operation_key)
                repo = {'literature.concentration_window.populate': self._concentration_window_repository, 'literature.measurement_comparison.populate': self._measurement_comparison_repository, 'literature.product_coupling.populate': self._product_coupling_repository, 'literature.measurement_validation.populate': self._measurement_validation_repository, 'literature.ion_discrimination.populate': self._ion_discrimination_repository, 'literature.channel.populate': self._channel_repository, 'literature.assay.components.populate': self._compiled_assay_repository, 'literature.rate.populate': self.literature_rate_repository, 'literature.calibration.recovery.populate': self.literature_calibration_recovery_repository, 'literature.rate.observations.populate': self.literature_rate_observation_repository, 'literature.rate.replicates.populate': self.literature_rate_replicate_repository, 'literature.rate.source.populate': self.literature_rate_repository, 'literature.quantity.populate': self.literature_quantity_repository, 'literature.assay.populate': self.literature_assay_repository, 'literature.amount.populate': self.literature_amount_repository, 'literature.completion_time.populate': self._completion_time_repository, 'literature.active_site.populate': self._active_site_repository, 'literature.parent_depletion.populate': self._parent_depletion_repository, 'literature.stoichiometric_balance.populate': self._stoichiometric_balance_repository, 'literature.assay_grading.populate': self._assay_grading_repository, 'literature.a105.aggregate': self._a105_aggregation_repository, 'literature.product_partition.populate': self._product_partition_repository, 'literature.optical.populate': self.literature_optical_repository, 'literature.kinetic.populate': self.literature_kinetic_repository, 'literature.kinetic.model.populate': self._kinetic_model_repository, 'literature.binding.interaction.populate': self.literature_binding_interaction_repository, 'literature.binding.interaction.model.populate': self._binding_interaction_model_repository, 'literature.ratio.populate': self.literature_ratio_repository, 'literature.ratio.source.populate': self._ratio_source_repository, 'literature.controlled_response.source_v3.populate': self._controlled_response_repository, 'literature.gel.populate': self._gel_repository, 'literature.binding.populate': self.literature_binding_repository, 'literature.binding.model.populate': self.literature_binding_model_repository, 'literature.transport.response.populate': self.literature_transport_repository, 'literature.figure.populate': self.literature_figure_repository}[tool_name]()
                arguments = self._materialize_text_arguments(context, arguments, repo)
                if tool_name == 'literature.controlled_response.source_v3.populate':
                    return repo.populate_v3(context, arguments, operation_key)
                return repo.populate_native(context, arguments, operation_key) if tool_name == 'literature.rate.source.populate' else repo.populate(context, arguments, operation_key)
            except (ContractError, ExperimentalContractError) as error:
                return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), 'field': getattr(error, 'field', None), **({'detail': deepcopy(error.detail)} if getattr(error, 'detail', None) is not None and (isinstance(error, ExperimentalContractError) and error.code == 'source_quote_mismatch' or (isinstance(error, ContractError) and str(error) in {'representation_error'})) else {})}}
        authorization = {'permitted_record_refs': tuple(context.received_record_refs)} if tool_name in {'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records'} else {}
        outcome = self.services.execute_tool(tool_name, arguments, scope=context.scope, operation_key=operation_key, **authorization)
        outcome = await outcome if inspect.isawaitable(outcome) else outcome
        if self.rate_population and tool_name == 'state.query' and (outcome.get('status') in {'completed', 'partial'}):
            try:
                for record in outcome.get('result', {}).get('records', ()):
                    self._endpoint_signal_repository().authorize_record_access(context, record)
                    self._summary_precision_repository().authorize_record_access(context, record)
                    self._measurement_comparison_repository().authorize_record_access(context, record)
                    self._concentration_window_repository().authorize_record_access(context, record)
            except ContractError as error:
                return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
        return outcome

