"""Authenticate the original page parent with this reading child's own configuration."""
from __future__ import annotations
from .source_contracts import REF, _PAGE, deepcopy, json, plain, validate_schema

class SourceCommissioningPageAssignment:

    def _commissioning_page_schema(self, *, context=None):
        schema = _PAGE
        schema = deepcopy(schema)
        from gene_annotation_episode.episodic_workflow.root.a102.literature_task_credit import task_schema
        task = task_schema()
        if self.private_yield_binding:
            for case in task['anyOf']:
                case['required'].remove('credit_unit')
            schema['required'].extend(('literature_task', 'proposed_annotation_ref'))
        schema['properties']['literature_task'] = task
        schema['properties']['proposed_annotation_ref'] = REF
        from gene_annotation_episode.episodic_workflow.root.a102.a102_literature_bindings import REQUESTED, assignment_component_schema
        schema['properties'][REQUESTED] = assignment_component_schema()
        return schema

    def _validate_commissioning_page_assignment(self, assignment, scope, *, context=None):
        value = plain(assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self._commissioning_page_schema(context=context))
        page = value
        self._validate_page(page, scope)
        return value
