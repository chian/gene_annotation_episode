"""Private A104 from parent."""
from __future__ import annotations
from .contracts import ContractError, REF, _CHILDREN, _PAGE, _REFERENCES, _TABLE, _TEXT, _WINDOW, deepcopy, json, obj, plain, validate_schema

from .assignment_fields import LiteratureAssignmentFields

class LiteratureAssignment(LiteratureAssignmentFields):

    def child_assignment_schema(self, parent, role):
        return self.assignment_schema(role, context=parent)

    def assignment_schema(self, role, *, context=None):
        self._role(role)
        schema = obj({'version': {'const': 'literature_assignment_v1'}, 'question_context_refs': _REFERENCES, 'source_refs': _REFERENCES})
        return self._assignment_fields(schema, context=context)

    def _validate_assignment(self, role, assignment, scope, *, context=None):
        value = plain(assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self.assignment_schema(role, context=context))
        for field, references in value.items():
            if field.endswith('_refs'):
                for reference in references:
                    self._require(reference, scope, None if field == 'question_context_refs' else 'source')
        return value

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        self._role(role)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        selection = plain(selection)
        if self.private_yield_binding:
            from gene_annotation_episode.episodic_workflow.root.a104.literature_task_credit import _task_key
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
            yield_settings = {name: declaration[name] for name in ('kind', 'cutoff', 'uncertainty_alpha')}
            if 'credit_unit' in task and task['credit_unit'] != declaration['credit_unit'] or ('yield_settings' in task and task['yield_settings'] != yield_settings):
                raise ContractError('literature_task_supplied_yield_binding_mismatch:' + key)
            selection['literature_task'] = {**task, 'credit_unit': declaration['credit_unit'], 'yield_settings': yield_settings}
        value = self._validate_assignment(role, selection, scope, context=parent)
        if 'literature_task' in value:
            annotation_for = getattr(self.services, 'proposed_annotation_for', None)
            proposed = annotation_for(parent) if annotation_for is not None else parent.assignment.get('proposed_annotation_ref')
            if proposed is not None and value.get('proposed_annotation_ref') != proposed:
                raise ContractError('literature_child_proposed_annotation_differs_from_parent')
        parent.role == 'literature_page' and role in _CHILDREN['literature_page']
        return value
