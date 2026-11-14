from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)

from .assignment_fields import LiteratureAssignmentFields

class LiteratureAssignment(LiteratureAssignmentFields):
    def child_assignment_schema(self, parent, role):
        return self.assignment_schema(role, context=parent)

    def assignment_schema(self, role, *, context=None):
        self._role(role)
        version, field = ("strategy_assignment_v1", "prior_search_refs")
        schema = obj({"version": {"const": version}, "question_context_refs": _REFERENCES,
                      field: _REFERENCES})
        return self._assignment_fields(schema, context=context)

    def _require(self, reference, scope, namespace=None):
        if not self.services.reference_in_scope(reference, scope, namespace):
            raise ContractError("literature_reference_unavailable", detail={
                "reference": reference, "namespace": namespace})
        return self.services.read_record(reference)

    @staticmethod
    def _artifact(source, representation):
        if representation == "original":
            return source["artifact_ref"]
        if representation == "text":
            # Match the existing source.read fallback exactly.
            return source.get("text_ref") or source["artifact_ref"]
        return source.get(representation + "_ref")

    def _validate_page(self, page, scope):
        source = self._require(page["source_ref"], scope, "source")
        if self._artifact(source, page["representation"]) != page["artifact_ref"]:
            raise ContractError("literature_source_artifact_mismatch", detail={
                "reference": page["source_ref"], "artifact_ref": page["artifact_ref"],
                "representation": page["representation"]})
        self._require(page["artifact_ref"], scope, "artifact")
        for reference in (*page["question_context_refs"], *page["prior_delivery_refs"]):
            self._require(reference, scope)
        # prior_delivery_refs are provenance only. They do not assert reading
        # coverage, successful extraction or understanding.

    def _validate_assignment(self, role, assignment, scope, *, context=None):
        value = plain(assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self.assignment_schema(role, context=context))
        return self._validate_owned_assignment(value, scope)

    def _validate_owned_assignment(self, value, scope):
        for field, references in value.items():
            if field.endswith("_refs"):
                for reference in references:
                    self._require(reference, scope, None if field == "question_context_refs" else "source")
        return value

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        # Common composition validates scope containment, ownership, the
        # original form and the operation identity. Never replace them here.
        self._role(role)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        selection = plain(selection)
        if self.private_yield_binding:
            from .commission_contract import _task_key
            task = selection.get('literature_task')
            if not isinstance(task, dict):
                raise ContractError('literature_original_task_required')
            try:
                key = _task_key(task)
            except (KeyError, TypeError) as error:
                raise ContractError('literature_original_task_invalid') from error
            declaration = self._yield_bindings.get(key)
            if declaration is None:
                raise ContractError('literature_yield_binding_missing_for_task:' + key)
            yield_settings = {name: declaration[name]
                for name in ('kind', 'cutoff', 'uncertainty_alpha')}
            if ('credit_unit' in task and task['credit_unit'] != declaration['credit_unit']
                    or 'yield_settings' in task and task['yield_settings'] != yield_settings):
                raise ContractError('literature_task_supplied_yield_binding_mismatch:' + key)
            selection['literature_task'] = {**task, 'credit_unit': declaration['credit_unit'],
                'yield_settings': yield_settings}
        value = self._validate_assignment(role, selection, scope, context=parent)
        if 'literature_task' in value:
            annotation_for = getattr(self.services, 'proposed_annotation_for', None)
            proposed = annotation_for(parent) if annotation_for is not None else parent.assignment.get('proposed_annotation_ref')
            if proposed is not None and value.get('proposed_annotation_ref') != proposed:
                raise ContractError('literature_child_proposed_annotation_differs_from_parent')
        parent.role
        return value

