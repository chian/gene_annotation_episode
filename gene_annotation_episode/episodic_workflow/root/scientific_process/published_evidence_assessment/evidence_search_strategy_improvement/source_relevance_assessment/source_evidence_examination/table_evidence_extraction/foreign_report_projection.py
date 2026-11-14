from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)



class LiteratureForeignReportProjection:
    def _received_external_report_facts(self, context):
        result = {}
        for namespace, _, _, _, repository in self._population_routes():
            cells = repository().received_cells(context)
            if cells or namespace == "literature_rate_cells":
                result[namespace] = cells
        if not self.rate_population:
            return self._complete_requested_received_arrays(context, result)
        if self.controlled_response_population:
            cells = self._controlled_response_repository().received_cells(context)
            if cells:
                result["literature_controlled_response_component_cells"] = cells
        if self.gel_population:
            cells = self._gel_repository().received_cells(context)
            if cells:
                result["literature_gel_component_cells"] = cells
        from gene_annotation_episode.episodic_workflow.root.library.literature_reaction_native_return_contracts import NAMESPACE
        native = self.services.literature_reaction_repository().native_observations_projection().received_rows(context)
        if native:
            result[NAMESPACE] = native
        return self._complete_requested_received_arrays(context, result)

