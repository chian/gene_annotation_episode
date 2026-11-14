from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.family import member_for_role

class LiteratureReceivedRecordCustody:

    def received_form_references(self, context, form, schema, operation_key):
        if not (self.rate_population or self.a108_context_evidence):
            return []
        for namespace, _, _, _, repository in self._population_routes():
            cells = []
            for name, node in schema.get("properties", {}).items():
                if node.get("x-source") == namespace:
                    cells.extend(form[name])
            if cells:
                repository().receive_cells(context, cells, operation_key)
        from gene_annotation_episode.episodic_workflow.root.literature_sheet_updates import current_sheet_refs
        references = current_sheet_refs(self.services.workflow.store, context)
        for namespace, _, _, _, repository in self._a108_population_routes():
            cells = [row for name, node in schema.get('properties', {}).items()
                if node.get('x-source') == namespace for row in form[name]]
            references.extend(repository().cell_record_refs(cells))
        if not self.rate_population:
            return list(dict.fromkeys(references))
        window_cells = [row for name, node in schema.get('properties', {}).items()
            if node.get('x-source') == 'literature_concentration_window_cells' for row in form[name]]
        references.extend(self._concentration_window_repository().cell_record_refs(window_cells))
        comparison_cells = [row for name, node in schema.get('properties', {}).items()
            if node.get('x-source') == 'literature_measurement_comparison_cells' for row in form[name]]
        references.extend(self._measurement_comparison_repository().cell_record_refs(comparison_cells))
        summary_cells = [row for name, node in schema.get('properties', {}).items()
            if node.get('x-source') == 'literature_kinetic_summary_precision_cells' for row in form[name]]
        references.extend(self._summary_precision_repository().cell_record_refs(summary_cells))
        endpoint_cells = [row for name, node in schema.get('properties', {}).items()
            if node.get('x-source') == 'literature_endpoint_signal_cells' for row in form[name]]
        references.extend(self._endpoint_signal_repository().cell_record_refs(endpoint_cells))
        from gene_annotation_episode.episodic_workflow.root.literature_product_coupling_storage import NAMESPACE as COUPLING_NAMESPACE
        coupling_cells = [row for name, node in schema.get("properties", {}).items()
            if node.get("x-source") == COUPLING_NAMESPACE for row in form[name]]
        references.extend(self._product_coupling_repository().cell_record_refs(coupling_cells))
        from gene_annotation_episode.episodic_workflow.root.literature_measurement_validation_storage import NAMESPACE as VALIDATION_NAMESPACE
        validation_cells = [row for name, node in schema.get("properties", {}).items()
            if node.get("x-source") == VALIDATION_NAMESPACE for row in form[name]]
        references.extend(self._measurement_validation_repository().cell_record_refs(validation_cells))
        from gene_annotation_episode.episodic_workflow.root.literature_calibration_recovery_storage import NAMESPACE as RECOVERY_NAMESPACE
        recovery_cells = [row for name, node in schema.get("properties", {}).items()
            if node.get("x-source") == RECOVERY_NAMESPACE for row in form[name]]
        references.extend(self.services.literature_calibration_recovery_repository().cell_record_refs(recovery_cells))
        from gene_annotation_episode.episodic_workflow.root.library.literature_rate_observation_return_contracts import NAMESPACE as OBSERVATION_NAMESPACE
        observation_cells = [row for name, node in schema.get("properties", {}).items()
            if node.get("x-source") == OBSERVATION_NAMESPACE for row in form[name]]
        references.extend(self.services.literature_rate_observation_repository().cell_record_refs(observation_cells))
        grid_cells = [row for name, node in schema.get("properties", {}).items()
            if node.get("x-source") == "literature_rate_grid_cells" for row in form[name]]
        references.extend(self._rate_grid_repository().cell_record_refs(grid_cells))
        from gene_annotation_episode.episodic_workflow.root.literature_rate_replicate_storage import NAMESPACE as REPLICATE_NAMESPACE
        replicate_cells = [row for name, node in schema.get("properties", {}).items()
            if node.get("x-source") == REPLICATE_NAMESPACE for row in form[name]]
        references.extend(self.services.literature_rate_replicate_repository().cell_record_refs(replicate_cells))
        if self.ion_discrimination_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_ion_discrimination_return_contracts import NAMESPACE
            cells = [row for name, node in schema.get("properties", {}).items()
                if node.get("x-source") == NAMESPACE for row in form[name]]
            references.extend(self._ion_discrimination_repository().cell_record_refs(cells))
        if self.channel_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_channel_return_contracts import NAMESPACE
            cells = [row for name, node in schema.get("properties", {}).items()
                if node.get("x-source") == NAMESPACE for row in form[name]]
            references.extend(self._channel_repository().cell_record_refs(cells))
        if self.compiled_assay_population:
            from gene_annotation_episode.episodic_workflow.root.literature_compiled_assay_storage import NAMESPACE, NAMESPACE_V2, NAMESPACE_V3
            cells = [row for name, node in schema.get("properties", {}).items()
                if node.get("x-source") in {NAMESPACE, NAMESPACE_V2, NAMESPACE_V3} for row in form[name]]
            references.extend(self._compiled_assay_repository().cell_record_refs(cells))
        if self.a106_intervention:
            from gene_annotation_episode.episodic_workflow.root.library.literature_perturbation_operand_contracts import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items()
                if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._perturbation_operand_repository().cell_record_refs(cells))
            from gene_annotation_episode.episodic_workflow.root.literature_intervention_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items()
                if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._intervention_grading_repository().cell_record_refs(cells))
            from gene_annotation_episode.episodic_workflow.root.library.literature_a106_subscore import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items()
                if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._a106_subscore_repository().cell_record_refs(cells))
        if self.assay_grading_population:
            from gene_annotation_episode.episodic_workflow.root.literature_assay_grading_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items()
                if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._assay_grading_repository().cell_record_refs(cells))
            from gene_annotation_episode.episodic_workflow.root.literature_a105_aggregation_storage import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items()
                if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._a105_aggregation_repository().cell_record_refs(cells))
        if self.product_partition_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_product_partition_return_schema import NAMESPACE
            cells = [row for name, node in schema.get("properties", {}).items()
                if node.get("x-source") == NAMESPACE for row in form[name]]
            references.extend(self._product_partition_repository().cell_record_refs(cells))
        if self.completion_time_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_completion_time_return_schema import NAMESPACE
            cells = [row for name, node in schema.get("properties", {}).items()
                if node.get("x-source") == NAMESPACE for row in form[name]]
            references.extend(self._completion_time_repository().cell_record_refs(cells))
        if self.active_site_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_active_site_return_schema import NAMESPACE
            cells = [row for name, node in schema.get("properties", {}).items()
                if node.get("x-source") == NAMESPACE for row in form[name]]
            references.extend(self._active_site_repository().cell_record_refs(cells))
        if self.parent_depletion_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_parent_depletion_return_schema import NAMESPACE
            cells=[row for name,node in schema.get('properties',{}).items()
                if node.get('x-source')==NAMESPACE for row in form[name]]
            references.extend(self._parent_depletion_repository().cell_record_refs(cells))
        if self.stoichiometric_balance_population:
            from gene_annotation_episode.episodic_workflow.root.library.literature_stoichiometric_balance_return_schema import NAMESPACE
            cells = [row for name, node in schema.get('properties', {}).items()
                if node.get('x-source') == NAMESPACE for row in form[name]]
            references.extend(self._stoichiometric_balance_repository().cell_record_refs(cells))
        if self.controlled_response_population:
            adapter = self._controlled_response_repository()
            cells = [row for name, node in schema.get("properties", {}).items()
                if node.get("x-source") == "literature_controlled_response_component_cells"
                for row in form[name]]
            if cells:
                adapter.receive_cells(context, cells, operation_key)
                references.extend(adapter.cell_record_refs(cells))
        if self.gel_population:
            adapter = self._gel_repository()
            cells = [row for name, node in schema.get("properties", {}).items()
                if node.get("x-source") == "literature_gel_component_cells"
                for row in form[name]]
            if cells:
                adapter.receive_cells(context, cells, operation_key)
                references.extend(adapter.cell_record_refs(cells))
        from gene_annotation_episode.episodic_workflow.root.library.literature_reaction_native_return_contracts import NAMESPACE
        from gene_annotation_episode.episodic_workflow.root.literature_reaction_native_storage import native_row_references
        native = [row for name, node in schema.get("properties", {}).items()
            if node.get("x-source") == NAMESPACE for row in form[name]]
        if native:
            self.services.literature_reaction_repository().native_observations_projection().receive_rows(context, native, operation_key)
            references.extend(native_row_references(native))
        return list(dict.fromkeys(references))

    def received_evidence_tokens(self, context):
        """Identify validated received component subsets, including zero-value cells.

        A sheet reference alone does not deliver its other components. These
        readers authenticate the original typed delivery before exposing each
        immutable cell; renamed form fields and repeated subsets add no token.
        """
        if not (self.rate_population or self.a108_context_evidence):
            return []
        from method_loop.durable import content_digest
        tokens = []
        def include(namespace, cells):
            tokens.extend('received_cell:' + namespace + ':' + content_digest(cell)
                          for cell in cells)
        for namespace, _, _, _, repository in self._population_routes():
            include(namespace, repository().received_cells(context))
        if self.rate_population:
            if self.controlled_response_population:
                include('literature_controlled_response_component_cells',
                        self._controlled_response_repository().received_cells(context))
            if self.gel_population:
                include('literature_gel_component_cells',
                        self._gel_repository().received_cells(context))
            from gene_annotation_episode.episodic_workflow.root.library.literature_reaction_native_return_contracts import NAMESPACE
            include(NAMESPACE, self.services.literature_reaction_repository()
                    .native_observations_projection().received_rows(context))
        return list(dict.fromkeys(tokens))

