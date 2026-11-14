from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)
from gene_annotation_episode.episodic_workflow.root.published_evidence_assessment.family import member_for_role

class LiteratureContinuation:
    def continuation_task(self, context):
        from .commission_contract import continuation_task
        self._role(context.role)
        return continuation_task(context)

    def yield_controller(self, context, initial_credit, epoch):
        """Bind this commissioned literature episode's estimator and cutoff."""
        self._role(context.role)
        if not self.private_yield_binding:
            return None
        from .yield_estimation import _private_yield_controller
        from .commission_contract import continuation_task
        key = continuation_task(context)
        declaration = self._yield_bindings.get(key)
        if declaration is None:
            raise ContractError('literature_yield_binding_missing_for_task:' + key)
        return _private_yield_controller(context, initial_credit, epoch, declaration)

