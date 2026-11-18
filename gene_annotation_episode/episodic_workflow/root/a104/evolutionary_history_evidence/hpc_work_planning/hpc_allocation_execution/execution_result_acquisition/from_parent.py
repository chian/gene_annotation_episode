"""Private A104 Results from parent."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.local_file_capture_results import SELECTOR_SCHEMA as LOCAL_FILE_SOURCE_SELECTOR_SCHEMA
from .result_records import RESULTS_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import checked
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.local_file_capture_results import is_file_source_selector
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_acquisition import is_native_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_acquisition import is_standard_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.a104_execution_bindings import result_selector_conditions

class ResultsFromParent:

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across a scientific return."""
        if parent is not None and parent.path[-1][0] == 'evolutionary_history_evidence' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ('execution_result_refs',)
        return ()

    def child_assignment_schema(self, parent, role):
        """Describe this Results child's original admitted request."""
        parent.role
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        schema = deepcopy(RESULTS_SCHEMA)
        schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'local_file_source_selector_v1'}}}, 'then': deepcopy(LOCAL_FILE_SOURCE_SELECTOR_SCHEMA)})
        schema['properties']['selector']['allOf'].extend(result_selector_conditions())
        return schema

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        recorded = self._recorded_results_assignment(parent, selected, scope, operation_key)
        if recorded is not None:
            return recorded
        masking_target = self._retained_masking_target(parent, selected, scope)
        utility_target = self._retained_utility_target(parent, selected, scope)
        target = utility_target if utility_target is not None else masking_target if masking_target is not None else self.job_progress_provider.targets.read_target(selected['handoff_ref'], scope)
        self._selector(selected, target)
        if is_file_source_selector(selected.get('selector')):
            self.local_file_sources.admit(parent, selected, target)
        if self._masking_selector(selected):
            self.native_blast_masking_results.validate_selected_inputs(parent, selected)
        if self._utility_selector(selected):
            self.native_blast_utility_results.validate_selected_inputs(parent, selected)
        if is_standard_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_result_publication import validate_standard_blast_selected_inputs
            validate_standard_blast_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'])
        if is_native_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_result_publication import validate_selected_inputs
            validate_selected_inputs(self.store, parent, selected['selector'], handoff_ref=selected['handoff_ref'])
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_data_host import is_bvbrc_request
        if target['resource_kind'] == 'api' and is_bvbrc_request(target['assignment'].get('request')):
            self.api_execution.bvbrc_data.validate_inputs(parent, selected['selector'], request=target['assignment']['request'])
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
