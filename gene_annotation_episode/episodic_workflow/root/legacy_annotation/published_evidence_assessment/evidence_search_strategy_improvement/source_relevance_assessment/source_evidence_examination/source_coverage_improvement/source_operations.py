from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.family import member_for_role

from .source_argument_admission import LiteratureSourceArgumentAdmission

from .source_text_materialization import LiteratureSourceTextMaterialization

class LiteratureSourceOperations(LiteratureSourceTextMaterialization, LiteratureSourceArgumentAdmission):
    def _within_source(self, reference, root, scope):
        pending, seen = [reference], set()
        while pending:
            current = pending.pop()
            if current == root:
                return True
            if current in seen:
                continue
            seen.add(current)
            source = self._require(current, scope, "source")
            pending.extend(source.get("parent_source_refs", ()))
        return False

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            arguments = self._tool_arguments(context, tool_name, arguments)
        except ContractError as error:
            # The common source records this actual failed own attempt. It
            # supplies feedback for another selected action, never a completed
            # scientific observation or an automatic retry.
            return {"status": "invalid", "operation_ref": identity("operation", {
                "key": operation_key, "name": tool_name, "arguments": plain(arguments)}),
                "record_refs": [], "changed_record_refs": [], "result": None,
                "feedback": {"category": "arguments_or_reference", "code": str(error),
                    **({"detail": error.detail} if error.detail else {})}}
        if tool_name == "literature.intervention_analysis.contract":
            from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.analysis_contract import prepare_analysis_contract
            try:
                value = prepare_analysis_contract(self.services, arguments)
            except ContractError as error:
                return {"status":"invalid", "record_refs":[], "changed_record_refs":[], "result":None,
                    "feedback":{"category":"arguments_or_reference", "code":str(error)}}
            return {"status":"completed", "record_refs":[], "changed_record_refs":[], "result":value, "feedback":None}
        if tool_name in {"literature.concentration_window.populate", "literature.measurement_comparison.populate", "literature.product_coupling.populate", "literature.measurement_validation.populate", "literature.ion_discrimination.populate", "literature.channel.populate", "literature.assay.components.populate", "literature.calibration.recovery.populate", "literature.rate.observations.populate", "literature.rate.replicates.populate", "literature.rate.populate", "literature.rate.source.populate", "literature.quantity.populate", "literature.assay.populate", "literature.ratio.populate", "literature.ratio.source.populate", "literature.binding.populate", "literature.binding.model.populate", "literature.transport.response.populate", "literature.perturbation.populate", "literature.structure.populate", "literature.reaction.populate", "literature.reaction.source.populate", "literature.figure.populate", "literature.partner.populate", "literature.partner.source.populate", "literature.amount.populate", "literature.completion_time.populate", "literature.active_site.populate", "literature.product_partition.populate", "literature.optical.populate", "literature.kinetic.populate", "literature.kinetic.model.populate", "literature.binding.interaction.populate", "literature.binding.interaction.model.populate", "literature.controlled_response.source_v3.populate", "literature.gel.populate", "literature.parent_depletion.populate", "literature.stoichiometric_balance.populate", "literature.assay_grading.populate", "literature.intervention_grading.populate", "literature.a106.finalize", "literature.a105.aggregate", "literature.a108_grading.populate", "literature.a108.aggregate"}:
            from gene_annotation_episode.episodic_workflow.root.library.literature_experimental_contracts import ExperimentalContractError
            try:
                if tool_name == 'literature.reaction.source.populate':
                    from gene_annotation_episode.episodic_workflow.root.literature_reaction_source import populate_source
                    repo = self.services.literature_reaction_repository()
                    return populate_source(repo, context,
                        self._materialize_text_arguments(context, arguments, repo), operation_key)
                if tool_name == 'literature.figure.populate' and arguments.get('version') == 'literature_figure_endpoint_signal_population_v1':
                    repo = self._endpoint_signal_repository()
                    return repo.populate(context, self._materialize_text_arguments(context, arguments, repo), operation_key)
                if tool_name == 'literature.kinetic.populate' and arguments.get('version') == 'literature_kinetic_summary_precision_population_v1':
                    repo = self._summary_precision_repository()
                    return repo.populate(context, self._materialize_text_arguments(context, arguments, repo), operation_key)
                repo = {"literature.concentration_window.populate": self._concentration_window_repository,
                        "literature.measurement_comparison.populate": self._measurement_comparison_repository,
                        "literature.product_coupling.populate": self._product_coupling_repository,
                        "literature.measurement_validation.populate": self._measurement_validation_repository,
                        "literature.ion_discrimination.populate": self._ion_discrimination_repository,
                        "literature.channel.populate": self._channel_repository,
                        "literature.assay.components.populate": self._compiled_assay_repository,
                        "literature.rate.populate": self.services.literature_rate_repository,
                        "literature.calibration.recovery.populate": self.services.literature_calibration_recovery_repository,
                        "literature.rate.observations.populate": self.services.literature_rate_observation_repository,
                        "literature.rate.replicates.populate": self.services.literature_rate_replicate_repository,
                        "literature.rate.source.populate": self.services.literature_rate_repository,
                        "literature.quantity.populate": self.services.literature_quantity_repository,
                        "literature.assay.populate": self.services.literature_assay_repository,
                        "literature.amount.populate": self.services.literature_amount_repository,
                        "literature.completion_time.populate": self._completion_time_repository,
                        "literature.active_site.populate": self._active_site_repository,
                        "literature.parent_depletion.populate": self._parent_depletion_repository,
                        "literature.stoichiometric_balance.populate": self._stoichiometric_balance_repository,
                        "literature.assay_grading.populate": self._assay_grading_repository,
                        "literature.intervention_grading.populate": self._intervention_grading_repository,
                        "literature.a106.finalize": self._a106_subscore_repository,
                        "literature.a105.aggregate": self._a105_aggregation_repository,
                        "literature.a108_grading.populate": self._a108_grading_repository,
                        "literature.a108.aggregate": self._a108_aggregation_repository,
                        "literature.product_partition.populate": self._product_partition_repository,
                        "literature.optical.populate": self.services.literature_optical_repository,
                        "literature.kinetic.populate": self.services.literature_kinetic_repository,
                        "literature.kinetic.model.populate": self._kinetic_model_repository,
                        "literature.binding.interaction.populate": self.services.literature_binding_interaction_repository,
                        "literature.binding.interaction.model.populate": self._binding_interaction_model_repository,
                        "literature.ratio.populate": self.services.literature_ratio_repository,
                        "literature.ratio.source.populate": self._ratio_source_repository,
                        "literature.controlled_response.source_v3.populate": self._controlled_response_repository,
                        "literature.gel.populate": self._gel_repository,
                        "literature.binding.populate": self.services.literature_binding_repository,
                        "literature.binding.model.populate": self.services.literature_binding_model_repository,
                        "literature.transport.response.populate": self.services.literature_transport_repository,
                        "literature.perturbation.populate": self.services.literature_perturbation_repository,
                        "literature.structure.populate": self.services.literature_structure_repository,
                        "literature.reaction.populate": self.services.literature_reaction_repository,
                        "literature.figure.populate": self.services.literature_figure_repository,
                        "literature.partner.populate": self.services.literature_partner_repository,
                        "literature.partner.source.populate": self.services.literature_partner_repository}[tool_name]()
                arguments = self._materialize_text_arguments(context, arguments, repo)
                if tool_name == "literature.controlled_response.source_v3.populate":
                    return repo.populate_v3(context, arguments, operation_key)
                return (repo.populate_native(context, arguments, operation_key)
                        if tool_name == "literature.rate.source.populate" else repo.populate(context, arguments, operation_key))
            except (ContractError, ExperimentalContractError) as error:
                return {"status": "invalid", "operation_ref": identity("operation", {
                    "key": operation_key, "name": tool_name, "arguments": plain(arguments)}),
                    "record_refs": [], "changed_record_refs": [], "result": None,
                    "feedback": {"category": "arguments_or_reference", "code": str(error),
                                 "field": getattr(error, "field", None),
                                 **({"detail": deepcopy(error.detail)}
                                    if getattr(error, "detail", None) is not None and (
                                        isinstance(error, ExperimentalContractError) and error.code == "source_quote_mismatch"
                                        or isinstance(error, ContractError) and str(error) in {
                                            "representation_error",
                                            "a106_revision_question_mismatch",
                                            "a106_existing_assessment_requires_null_missing_reason"}
                                        or isinstance(error, ContractError)
                                            and tool_name == "literature.intervention_grading.populate"
                                            and (str(error) == "assay_grading_anchored_support_required"
                                                or str(error) == "intervention_latest_revision_required"
                                                and bool(error.detail)))
                                    else {})}}
        authorization = ({"permitted_record_refs": tuple(context.received_record_refs)}
                         if tool_name in {"source.locate", "source.sequence.scan", "source.sequence.references", "source.experimental.records"} else {})
        outcome = self.services.execute_tool(tool_name, arguments, scope=context.scope,
                                              operation_key=operation_key, **authorization)
        outcome = await outcome if inspect.isawaitable(outcome) else outcome
        if self.rate_population and tool_name == 'state.query' and outcome.get('status') in {'completed', 'partial'}:
            try:
                for record in outcome.get('result', {}).get('records', ()):
                    self._endpoint_signal_repository().authorize_record_access(context, record)
                    self._summary_precision_repository().authorize_record_access(context, record)
                    self._measurement_comparison_repository().authorize_record_access(context, record)
                    self._concentration_window_repository().authorize_record_access(context, record)
            except ContractError as error:
                return {"status": "invalid", "operation_ref": identity("operation", {
                    "key": operation_key, "name": tool_name, "arguments": plain(arguments)}),
                    "record_refs": [], "changed_record_refs": [], "result": None,
                    "feedback": {"category": "arguments_or_reference", "code": str(error)}}
        if self._enabled('a108_context_evidence', context) and tool_name == 'state.query' and outcome.get('status') in {'completed', 'partial'}:
            try:
                for record in outcome.get('result', {}).get('records', ()):
                    self._a108_grading_repository().authorize_record_access(context, record)
                    self._a108_aggregation_repository().authorize_record_access(context, record)
            except ContractError as error:
                return {'status': 'invalid', 'operation_ref': identity('operation', {
                    'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}),
                    'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
        return outcome

