from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.family import member_for_role

class LiteratureCredit:
    def credit_view(self, context, receiver_selection):
        self._role(context.role)
        return self.services.scientific_credit(context, receiver_selection)

    def credit_projector(self, context):
        from .task_credit import LiteratureTaskCredit
        from .commission_contract import commissioned_task
        self._role(context.role)
        task, _ = commissioned_task(context)
        for option, axis in (('a106_intervention', 'A106'), ('a108_context_evidence', 'A108'),
                ('assay_grading_population', 'A105')):
            if self._enabled(option, context):
                if task['evidence_axis'] != axis:
                    raise ContractError('literature_task_original_axis_mismatch')
                break
        return LiteratureTaskCredit(self, context)

    def automatic_score_judgments(self, context):
        if not self._enabled('a106_intervention', context):
            return []
        return self._a106_subscore_repository().prepare_judgments(context)

    def complete_score_judgment(self, context, judgment_ref, response=None, *, provenance, failure=None):
        if not self._enabled('a106_intervention', context):
            raise ContractError('a106_automatic_judgment_outside_axis')
        return self._a106_subscore_repository().complete_judgment(
            context, judgment_ref, response, provenance=provenance, failure=failure)

