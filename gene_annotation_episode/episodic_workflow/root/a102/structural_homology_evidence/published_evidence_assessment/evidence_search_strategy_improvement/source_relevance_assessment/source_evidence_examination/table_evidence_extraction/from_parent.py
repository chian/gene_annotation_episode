"""Private A102 literature_table from parent."""
from __future__ import annotations
from .source_contracts import ContractError, REF, _PAGE, _REFERENCES, _TABLE, _WINDOW, deepcopy, json, obj, plain, validate_schema

class SourceFromParent:

    def child_assignment_schema(self, parent, role):
        return self.assignment_schema(role, context=parent)

    def assignment_schema(self, role, *, context=None):
        self._role(role)
        selection = {'anyOf': [_TABLE, _WINDOW]}
        schema = obj({'version': {'const': 'reading_assignment_v1'}, 'page': _PAGE, 'selection': selection})
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

    def _validate_page(self, page, scope):
        source = self._require(page['source_ref'], scope, 'source')
        if self._artifact(source, page['representation']) != page['artifact_ref']:
            raise ContractError('literature_source_artifact_mismatch', detail={'reference': page['source_ref'], 'artifact_ref': page['artifact_ref'], 'representation': page['representation']})
        self._require(page['artifact_ref'], scope, 'artifact')
        for reference in (*page['question_context_refs'], *page['prior_delivery_refs']):
            self._require(reference, scope)

    def _validate_assignment(self, role, assignment, scope, *, context=None):
        value = plain(assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self.assignment_schema(role, context=context))
        page = value['page']
        self._validate_page(page, scope)
        selected = value['selection']
        windows = [selected]
        for window in windows:
            if window['source_ref'] != page['source_ref']:
                raise ContractError('literature_reading_source_mismatch')
            if 'representation' in window and window['representation'] != page['representation']:
                raise ContractError('literature_reading_representation_mismatch')
            if 'representation' in window:
                artifact = self.services.read_record(page['artifact_ref'])
                if window['offset'] > artifact['size']:
                    raise ContractError('source_offset_out_of_bounds')
        return value

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        self._role(role)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('operation_key_required')
        selection = plain(selection)
        if self.private_yield_binding:
            from gene_annotation_episode.episodic_workflow.root.a102.literature_task_credit import _task_key
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
        if parent.role == 'literature_page':
            original = self._validate_commissioning_page_assignment(parent.assignment, parent.scope, context=parent)
            if not self._within_source(value['page']['source_ref'], original['source_ref'], scope):
                raise ContractError('literature_reading_outside_assigned_source')
        return value
