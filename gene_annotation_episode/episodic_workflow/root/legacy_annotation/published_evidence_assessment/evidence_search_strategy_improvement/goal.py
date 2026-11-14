from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)

class LiteratureGoal:
    def instructions(self, context):
        self._role(context.role)
        if self._enabled('a108_context_evidence', context):
            from gene_annotation_episode.episodic_workflow.root.library.literature_a108_prompt import A108_CONTEXT_TASK, A108_READING_TASK
            return '\n\n'.join(("Investigate which search approach is productive. Keep the information objective and evidence context separate from a literal provider query. Revise terms or source choices in light of actual search/read outcomes; a search child can investigate which returned sources deserve examination.", A108_CONTEXT_TASK, A108_READING_TASK))
        if self._enabled('a106_intervention', context):
            from gene_annotation_episode.episodic_workflow.root.library.literature_perturbation_prompt import PERTURBATION_TASK
            from gene_annotation_episode.episodic_workflow.root.library.literature_a106_task_declaration import TASK
            return '\n\n'.join(("Investigate which search approach is productive. Keep the information objective and evidence context separate from a literal provider query. Revise terms or source choices in light of actual search/read outcomes; a search child can investigate which returned sources deserve examination.", PERTURBATION_TASK, TASK))
        return ("Investigate which search approach is productive. Keep the information objective and evidence context separate from a literal provider query. Revise terms or source choices in light of actual search/read outcomes; a search child can investigate which returned sources deserve examination." + "\n"
            "This is an iterative scientific investigation in the shared Episode loop. "
            "Earlier outcomes and admitted child forms inform later choices; no child order, "
            "reading quota or complete-document requirement is prescribed. A one-off search/read "
            "is an ordinary tool. A supplied reading selector is context, not an automatically "
            "executed action. Preserve the source's actual subject, experimental conditions, "
            "representation, version and UTF-8 byte anchors. Distinguish source claims from "
            "their applicability to the fixed target. Negative findings and qualifications can "
            "advance the investigation. Commit interpretations with the common reasoning action "
            "and update only the parent's declared typed form in that same work call. "
            "Navigation, byte coverage and repeated reading earn no scientific credit by themselves. "
            "The commissioned task's own yield settings guide continuation.")

