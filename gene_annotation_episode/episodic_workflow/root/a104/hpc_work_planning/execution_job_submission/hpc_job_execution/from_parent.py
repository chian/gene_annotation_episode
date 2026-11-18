"""Private A104 HPCExecution from parent."""
from __future__ import annotations
from .binding_roles import KINDS
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import checked
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_acquisition import is_native_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_acquisition import is_standard_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class HPCExecutionFromParent:

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across a scientific return."""
        if parent is not None and parent.path[-1][0] == 'evolutionary_history_evidence' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ()
        return ()

    def child_assignment_schema(self, parent, role):
        """A frozen HPC launch exposes only its already authorized request."""
        if parent.role == 'launch' and role == 'launch_hpc' and any((ancestor == 'hpc' for ancestor, _ in parent.path)):
            assignment = plain(parent.assignment)
            requests = [request for resource_id, request in assignment['requests'].items() if self._permitted(assignment, resource_id) and request.get('resource_kind') == 'hpc']
            if not requests:
                raise ValueError('frozen_hpc_launch_request_missing')
            return {'type': 'object', 'enum': requests}
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        alternatives = [self._request_schema(key, selected=True, internal=internal) for key, config in self.resources.items() if KINDS[config['kind']] == ROLE_KINDS[role]]
        return {'anyOf': alternatives} if alternatives else {'not': {}}

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        selected = self._validate_request(selected)
        if ROLE_KINDS[role] != KINDS[self.resources[selected['resource_id']]['kind']]:
            raise ValueError('execution_resource_kind_conflict')
        if parent.role != 'launch':
            raise ValueError('resource_child_role_owned_by_launch')
        original = self._launch(plain(parent.assignment))
        self._masking_inputs(parent, selected)
        self._utility_inputs(parent, selected)
        self._versions(original['immutable_input_versions'], scope, context=parent)
        from gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_result_publication import validate_native_job_inputs
        from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_result_publication import validate_standard_blast_job_inputs
        validate_native_job_inputs(self.store, parent, selected)
        validate_standard_blast_job_inputs(self.store, parent, selected)
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
