"""Private A104 Launch from parent."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.resource_records import INPUT_VERSION_SCHEMA
from .received_launch_records import LAUNCH_VERSION
from gene_annotation_episode.episodic_workflow.root.a104.launch_instructions import SELECTION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import checked
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_acquisition import is_native_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_acquisition import is_standard_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a104.a104_execution_bindings import launch_request_schema
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class LaunchFromParent:

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across a scientific return."""
        if parent is not None and parent.path[-1][0] == 'scientific_process' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ('execution_handoff_refs',)
        return ()

    def child_assignment_schema(self, parent, role):
        """Describe this selected child's admitted incoming assignment."""
        parent.role
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        schema = obj({'version': {'const': LAUNCH_VERSION}, 'requests': {'type': 'object', 'properties': {key: launch_request_schema(self._request_schema(key, selected=False, internal=internal, compact=False), key, self.resources[key].get('service')) for key in self.resources}, 'minProperties': 1, 'additionalProperties': False}, 'immutable_input_versions': {'type': 'array', 'items': deepcopy(INPUT_VERSION_SCHEMA)}, 'constraints': {'type': 'object'}})
        schema['properties']['launch_instructions'] = deepcopy(SELECTION_SCHEMA)
        return schema

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        if parent.role in ('hpc', 'hpc_execution'):
            from gene_annotation_episode.episodic_workflow.root.a104.library.hpc_launch_custody import authenticate_launch
            authenticate_launch(parent, selected, operation_key, self.directory)
        selected = self._launch(selected, scope=scope)
        for request in selected['requests'].values():
            self._masking_inputs(parent, request)
            self._utility_inputs(parent, request)
        self._versions(selected['immutable_input_versions'], scope, context=parent)
        from gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_result_publication import validate_native_job_inputs
        from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
        for request in selected['requests'].values():
            validate_native_job_inputs(self.store, parent, request)
            validate_standard_blast_job_inputs(self.store, parent, request)
        return selected

    def initial_references(self, context):
        if context.role != 'results':
            assignment = plain(context.assignment)
            requests = assignment.get('requests', {}).values() if context.role == 'launch' else [assignment] if context.role == 'launch_local' else []
            references = []
            for request in requests:
                references.extend(self._masking_inputs(context, request))
                references.extend(self._utility_inputs(context, request))
            return list(dict.fromkeys(references))
        assignment = plain(context.assignment)
        target = self._target(context)
        if self.native_blast_masking_results.applies(context):
            self._selector(assignment, target)
            return self.native_blast_masking_results.validate_selected_inputs(context, assignment)
        if self.native_blast_utility_results.applies(context):
            self._selector(assignment, target)
            return self.native_blast_utility_results.validate_selected_inputs(context, assignment)
        selected = [assignment['handoff_ref']]
        if is_standard_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_result_publication import validate_standard_blast_selected_inputs
            selected.extend(validate_standard_blast_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        if is_native_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_result_publication import validate_selected_inputs
            selected.extend(validate_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        return list(dict.fromkeys(selected))
