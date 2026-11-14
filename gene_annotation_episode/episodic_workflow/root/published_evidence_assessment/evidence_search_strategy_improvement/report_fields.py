from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)
from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.family import member_for_role

class LiteratureReportFields:

    def fact_sources(self, role):
        self._role(role)
        # Common scientific facts already expose actual changed assessments,
        # observations, annotation accounts and report-basis references.
        from gene_annotation_episode.episodic_workflow.root.library.literature_task_answer_schemas import SCREENING, screening_schema, LEADS, lead_return_schema
        return {**(self._rate_fact_sources() if self.rate_population or self.a108_context_evidence else {}),
            SCREENING: screening_schema(), LEADS: lead_return_schema()}

